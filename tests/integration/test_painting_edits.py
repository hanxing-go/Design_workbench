import json
import sqlite3
import uuid
from pathlib import Path

import pytest
from litemapy import Schematic

from design_workbench.adapters.formats.litematic import Litematic, region_bounds
from design_workbench.adapters.rendering.paintings import imported_paintings
from design_workbench.adapters.storage.sqlite import SqliteStore
from design_workbench.application.contracts import EditRequest, HistoryRequest
from design_workbench.application.scenes import SceneService
from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.placement import FACES


def edit(service: SceneService, *operations: dict) -> dict:
    return service.edit(
        EditRequest.model_validate(
            {
                "expected_revision": service.summary()["revision"],
                "request_id": str(service.summary()["revision"]),
                "operations": operations,
            }
        )
    )


def wall(service: SceneService) -> None:
    edit(
        service,
        {"op": "fill", "bounds": {"low": [0, 0, 0], "high": [3, 3, 0]}, "state": {"name": "stone"}},
    )


def test_snap_is_revision_checked_collision_safe_and_preserves_manual_set(
    service: SceneService,
) -> None:
    wall(service)
    request = EditRequest.model_validate(
        {
            "expected_revision": 1,
            "request_id": "snap",
            "operations": [
                {"op": "place", "support": [0, 0, 0], "face": "south", "state": {"name": "torch"}}
            ],
        }
    )
    assert service.edit(request)["changed"] == 1
    assert service.edit(request)["revision"] == 2
    scene = service.repository.load()
    assert scene.cells[(0, 0, 1)].state.name == "minecraft:wall_torch"
    assert dict(scene.cells[(0, 0, 1)].state.properties)["facing"] == "south"
    with pytest.raises(WorkbenchError):
        edit(
            service,
            {"op": "place", "support": [0, 0, 0], "face": "south", "state": {"name": "ladder"}},
        )
    assert service.summary()["revision"] == 2
    edit(
        service,
        {
            "op": "set",
            "blocks": [
                {
                    "position": [0, 0, 1],
                    "state": {"name": "ladder", "properties": {"facing": "west"}},
                }
            ],
        },
    )
    assert dict(service.repository.load().cells[(0, 0, 1)].state.properties)["facing"] == "west"
    with pytest.raises(WorkbenchError):
        edit(
            service,
            {"op": "place", "support": [8, 0, 0], "face": "south", "state": {"name": "torch"}},
        )


def test_painting_undo_redo_reopen_and_independent_litematic_export(
    service: SceneService, tmp_path: Path
) -> None:
    wall(service)
    result = edit(
        service, {"op": "painting", "support": [1, 1, 0], "face": "south", "variant": "auto"}
    )
    assert result["paintings_changed"] == 1
    scene = service.repository.load()
    painting = scene.paintings[0]
    assert painting.variant == "pointer"  # Stable tie-break among equally sized artwork.
    assert len(painting.positions()) == 16
    reopened = SqliteStore(service.repository.path).load()  # type: ignore[attr-defined]
    assert reopened.paintings == scene.paintings
    payload, report = service.export_asset(2)
    assert report["paintings"] == 1
    target = tmp_path / "painting.litematic"
    target.write_bytes(payload)
    independent = Schematic.load(str(target))
    entity = next(iter(independent.regions.values())).entities[0]
    assert str(entity.data["id"]) == "minecraft:painting"
    assert str(entity.data["variant"]) == "minecraft:pointer"
    document = Litematic.parse(payload)
    entry = next(iter(document["Regions"].values()))["Entities"][0]
    assert int(entry["facing"]) == 0
    assert [float(v) for v in entry["Pos"]] == pytest.approx(painting.center())
    assert [int(entry["Tile" + axis]) for axis in "XYZ"] == list(painting.anchor)
    assert imported_paintings(payload)[0].anchor == painting.anchor
    service.history("undo", HistoryRequest(expected_revision=2, request_id="undo-paint"))
    assert service.summary()["paintings"] == 0
    service.history("redo", HistoryRequest(expected_revision=3, request_id="redo-paint"))
    assert service.repository.load().paintings[0] == painting
    edit(service, {"op": "delete_painting", "id": painting.id})
    assert service.summary()["paintings"] == 0


def test_painting_fit_support_and_import_protection_are_atomic(service: SceneService) -> None:
    wall(service)
    edit(service, {"op": "painting", "support": [1, 1, 0], "face": "south", "variant": "match"})
    with pytest.raises(WorkbenchError, match="先删除"):
        edit(
            service, {"op": "delete", "selector": {"bounds": {"low": [1, 1, 0], "high": [1, 1, 0]}}}
        )
    with pytest.raises(WorkbenchError):
        edit(service, {"op": "painting", "support": [1, 1, 0], "face": "south", "variant": "match"})
    assert service.summary()["revision"] == 2
    payload, _ = service.export_asset(2)
    service.import_asset(payload, HistoryRequest(expected_revision=2, request_id="reimport"))
    assert service.summary()["paintings"] == 0  # Now preserved as a read-only source entity.
    assert (1, 1, 0) in service.repository.load().protected
    reexported, _ = service.export_asset(3)
    assert (
        next(iter(Litematic.parse(reexported)["Regions"].values()))["Entities"]
        == next(iter(Litematic.parse(payload)["Regions"].values()))["Entities"]
    )


def test_schema_two_migration_backups_leave_other_metadata_unchanged(service: SceneService) -> None:
    path = service.repository.path  # type: ignore[attr-defined]
    with sqlite3.connect(path) as conn:
        data = json.loads(conn.execute("SELECT value FROM meta WHERE key='scene'").fetchone()[0])
        data.pop("paintings")
        conn.execute("UPDATE meta SET value=? WHERE key='scene'", (json.dumps(data),))
        conn.execute("PRAGMA user_version=2")
    upgraded = SqliteStore(path)
    assert upgraded.load().paintings == []
    assert len(list(path.parent.glob(path.name + ".v2-backup-*"))) == 1
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 3
        assert (
            json.loads(conn.execute("SELECT value FROM meta WHERE key='scene'").fetchone()[0])
            == data
        )


@pytest.mark.parametrize("face", ["south", "west", "north", "east"])
def test_negative_origin_painting_coordinates_uuid_and_reimport(
    service: SceneService, face: str
) -> None:
    edit(
        service,
        {
            "op": "fill",
            "bounds": {"low": [-12, -7, -12], "high": [-8, -3, -8]},
            "state": {"name": "stone"},
        },
    )
    normal = FACES[face]
    support = [-10 + 2 * normal[0], -5, -10 + 2 * normal[2]]
    edit(service, {"op": "painting", "support": support, "face": face, "variant": "match"})
    painting = service.repository.load().paintings[0]
    payload, _ = service.export_asset(2)
    region = next(iter(Litematic.parse(payload)["Regions"].values()))
    origin = region_bounds(region).low
    entry = region["Entities"][0]
    assert all(v < 0 for v in origin)
    assert [int(entry["Tile" + axis]) + origin[i] for i, axis in enumerate("XYZ")] == list(
        painting.anchor
    )
    assert [float(v) + origin[i] for i, v in enumerate(entry["Pos"])] == pytest.approx(
        painting.center()
    )
    words = [int(v) & 0xFFFFFFFF for v in entry["UUID"]]
    assert (
        uuid.UUID(
            int=sum(word << shift for word, shift in zip(words, (96, 64, 32, 0), strict=True))
        ).hex
        == uuid.UUID(painting.id).hex
    )
    imported = imported_paintings(payload)[0]
    assert imported.anchor == painting.anchor and imported.facing == face
    scene, _ = service.formats.read(payload)
    assert set(painting.positions()) <= scene.protected
    assert {
        tuple(p[i] - normal[i] for i in range(3)) for p in painting.positions()
    } <= scene.protected
