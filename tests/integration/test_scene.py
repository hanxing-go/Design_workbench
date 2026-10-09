import json
import sqlite3
import subprocess
import sys
from typing import Any

import pytest
from pydantic import ValidationError

from design_workbench.adapters.storage.sqlite import SqliteStore
from design_workbench.application.contracts import EditRequest, HistoryRequest
from design_workbench.application.scenes import SceneService
from design_workbench.domain.errors import WorkbenchError


def edit(
    service: SceneService, operations: list[dict[str, Any]], request_id: str = "edit"
) -> dict[str, Any]:
    return service.edit(
        EditRequest.model_validate(
            {
                "expected_revision": service.summary()["revision"],
                "request_id": request_id,
                "operations": operations,
            }
        )
    )


def test_atomic_preview_revision_and_idempotence(service: SceneService) -> None:
    request = EditRequest.model_validate(
        {
            "expected_revision": 0,
            "request_id": "first",
            "operations": [
                {
                    "op": "fill",
                    "bounds": {"low": [-1, 0, -1], "high": [1, 1, 1]},
                    "state": {"name": "stone"},
                }
            ],
        }
    )
    assert service.edit(request, preview=True)["changed"] == 18
    assert service.summary()["revision"] == 0
    first = service.edit(request)
    assert service.edit(request) == first
    assert service.summary()["blocks"] == 18
    with pytest.raises(WorkbenchError) as error:
        edit(
            service,
            [
                {
                    "op": "fill",
                    "bounds": {"low": [3, 0, 0], "high": [4, 0, 0]},
                    "state": {"name": "oak_planks"},
                },
                {
                    "op": "fill",
                    "bounds": {"low": [5, 0, 0], "high": [5, 0, 0]},
                    "state": {"name": "invented"},
                },
            ],
            "bad",
        )
    assert error.value.code == "UNKNOWN_BLOCK"
    assert service.summary()["blocks"] == 18
    assert service.summary()["revision"] == 1
    with pytest.raises(WorkbenchError) as conflict:
        service.edit(request.model_copy(update={"request_id": "stale"}))
    assert conflict.value.code == "REVISION_CONFLICT"
    with pytest.raises(ValidationError):
        EditRequest.model_validate({**request.model_dump(by_alias=True), "extra": "bad"})
    with pytest.raises(ValidationError):
        EditRequest.model_validate(
            {
                "expected_revision": 1,
                "request_id": "badfield",
                "operations": [
                    {
                        "op": "fill",
                        "bounds": {"low": [0, 0, 0], "high": [0, 0, 0]},
                        "state": {"name": "stone"},
                        "invented": True,
                    }
                ],
            }
        )


def test_history_persists_branches_and_monotonic_revisions(service: SceneService) -> None:
    edit(
        service,
        [{"op": "set", "blocks": [{"position": [0, 0, 0], "state": {"name": "stone"}}]}],
        "one",
    )
    edit(service, [{"op": "replace", "selector": {}, "state": {"name": "oak_planks"}}], "two")
    service.history("undo", HistoryRequest(expected_revision=2, request_id="undo"))
    reopened = SqliteStore(service.repository.path)  # type: ignore[attr-defined]
    assert reopened.load().revision == 3
    assert reopened.load().cells[(0, 0, 0)].state.name == "minecraft:stone"
    assert reopened.history_info()["redo_available"] == 1
    service.history("redo", HistoryRequest(expected_revision=3, request_id="redo"))
    assert service.summary()["revision"] == 4
    service.history("undo", HistoryRequest(expected_revision=4, request_id="undo-again"))
    edit(service, [{"op": "replace", "selector": {}, "state": {"name": "bricks"}}], "branch")
    assert service.summary()["redo_available"] == 0
    assert service.summary()["revision"] == 6


def test_rotation_mirror_and_collision(service: SceneService) -> None:
    edit(
        service,
        [
            {
                "op": "set",
                "blocks": [
                    {
                        "position": [1, 0, 0],
                        "state": {
                            "name": "oak_stairs",
                            "properties": {"facing": "east", "shape": "inner_left"},
                        },
                        "group": "roof",
                    }
                ],
            }
        ],
        "stair",
    )
    edit(service, [{"op": "transform", "selector": {"group": "roof"}, "rotation": 90}], "rotate")
    scene = service.repository.load()
    assert dict(scene.cells[(0, 0, 1)].state.properties)["facing"] == "south"
    edit(service, [{"op": "transform", "selector": {"group": "roof"}, "mirror": "z"}], "mirror")
    properties = dict(service.repository.load().cells[(0, 0, -1)].state.properties)
    assert properties["facing"] == "north"
    assert properties["shape"] == "inner_right"
    with pytest.raises(WorkbenchError) as collision:
        edit(service, [{"op": "transform", "selector": {}, "copy": True}], "collide")
    assert collision.value.code == "EDIT_COLLISION"


def test_writer_competition_is_optimistic(service: SceneService) -> None:
    old = service.repository.load()
    edit(
        service,
        [{"op": "set", "blocks": [{"position": [0, 0, 0], "state": {"name": "stone"}}]}],
        "winner",
    )
    with pytest.raises(WorkbenchError) as error:
        service.repository.commit(old, [], 0, "loser", "fingerprint")
    assert error.value.code == "REVISION_CONFLICT"
    assert service.summary()["blocks"] == 1


def test_process_exit_mid_transaction_rolls_back(service: SceneService) -> None:
    edit(
        service,
        [{"op": "set", "blocks": [{"position": [0, 0, 0], "state": {"name": "stone"}}]}],
        "start",
    )
    path = str(service.repository.path)  # type: ignore[attr-defined]
    code = """
import os,sqlite3,sys
c=sqlite3.connect(sys.argv[1],isolation_level=None)
c.execute('BEGIN IMMEDIATE')
c.execute('DELETE FROM chunks')
c.execute("UPDATE meta SET value='broken'")
os._exit(23)
"""
    result = subprocess.run([sys.executable, "-c", code, path], check=False)
    assert result.returncode == 23
    assert service.summary()["revision"] == 1
    assert service.summary()["blocks"] == 1


def test_schema_migration_backups_and_failure_preserves_original(service: SceneService) -> None:
    path = service.repository.path  # type: ignore[attr-defined]
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE requests")
        connection.execute("PRAGMA user_version=1")
    upgraded = SqliteStore(path)
    assert upgraded.load().revision == 0
    backups = list(path.parent.glob(path.name + ".v1-backup-*"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version=1")
    with pytest.raises(WorkbenchError):
        SqliteStore(path)
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert (
            json.loads(connection.execute("SELECT value FROM meta").fetchone()[0])["revision"] == 0
        )
