import gzip
import io
import json
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import nbtlib
import pytest
from fastapi.testclient import TestClient

from design_workbench.adapters.rendering.cache import RenderCache
from design_workbench.adapters.rendering.packets import render_chunk, render_packet
from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.adapters.resources.pack import ResourcePack
from design_workbench.adapters.storage.sqlite import SqliteStore, decode_chunk, encode
from design_workbench.application.contracts import EditRequest, HistoryRequest, RenameRequest
from design_workbench.application.scenes import SceneService
from design_workbench.config import Settings
from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.models import BlockState, Bounds, Cell, Point, Scene
from design_workbench.interfaces.http import create_app


class MinimalPack:
    """Deterministic resource fixture; fluid/sign projection still uses real code."""

    def __init__(self, resource_hash: str = "first") -> None:
        self.manifest = {"bundle_hash": resource_hash}
        self.atlas = {"width": 16, "height": 16, "uv": {}}

    def support(self, state: BlockState) -> dict[str, Any]:
        return {"status": "special" if state.name.endswith("chest") else "static", "reason": "test"}

    def geometry(self, state: BlockState) -> dict[str, Any]:
        return {**self.support(state), "faces": [], "opaque_cube": True, "render_layer": "cutout"}


@pytest.fixture
def pack() -> ResourcePack:
    return cast(ResourcePack, MinimalPack())


@pytest.fixture
def cache() -> Any:
    instance = RenderCache()
    try:
        yield instance
    finally:
        instance.close()


def store(service: SceneService) -> SqliteStore:
    return cast(SqliteStore, service.repository)


def set_cells(service: SceneService, cells: dict[Point, str | dict[str, Any]]) -> None:
    revision = service.summary()["revision"]
    service.edit(
        EditRequest.model_validate(
            {
                "expected_revision": revision,
                "request_id": f"set-{revision}",
                "operations": [
                    {
                        "op": "set",
                        "blocks": [
                            {
                                "position": point,
                                "state": {"name": state} if isinstance(state, str) else state,
                            }
                            for point, state in cells.items()
                        ],
                    }
                ],
            }
        )
    )


def assert_reference(
    packet: dict[str, Any], service: SceneService, catalog: Catalog, pack: ResourcePack
) -> None:
    reference = render_packet(
        store(service).load(), catalog, pack, source=store(service).attachment()
    )
    assert packet["summary"] == reference["summary"]
    assert packet["chunks"] == reference["chunks"]
    assert packet["models"] == reference["models"]
    assert sorted(packet["warnings"], key=lambda item: item["name"]) == sorted(
        reference["warnings"], key=lambda item: item["name"]
    )
    assert {
        key: value.rsplit(":", 1)[1] for key, value in packet["chunk_versions"].items()
    } == reference["chunk_versions"]


def test_cache_matches_reference_and_reuses_unchanged_projection(
    service: SceneService,
    catalog: Catalog,
    pack: ResourcePack,
    cache: RenderCache,
) -> None:
    set_cells(service, {(-1, -1, -1): "stone", (0, 0, 0): "chest", (32, 16, 1): "oak_planks"})
    path = store(service).path
    first = cache.render(path, catalog, pack)
    assert_reference(first, service, catalog, pack)
    statements: list[str] = []
    cache._entries[path].connection.set_trace_callback(statements.append)
    with (
        patch.object(SqliteStore, "load", side_effect=AssertionError("full scene load")),
        patch(
            "design_workbench.adapters.rendering.cache.decode_chunk",
            side_effect=AssertionError("decode"),
        ),
        patch(
            "design_workbench.adapters.rendering.cache.render_chunk",
            side_effect=AssertionError("rebuild"),
        ),
    ):
        unchanged = cache.render(path, catalog, pack, first["chunk_versions"])
        summary = cache.summary(path)
    assert not unchanged["chunks"] and not unchanged["models"]
    assert unchanged["warnings"] == first["warnings"]
    assert summary["blocks"] == 3 and summary["revision"] == 1
    assert not any("SELECT" in statement.upper() for statement in statements)
    assert not cache._entries[path].connection.in_transaction
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        cache._entries[path].connection.execute("DELETE FROM chunks")


def test_local_edit_decodes_and_rebuilds_only_changed_chunk(
    service: SceneService,
    catalog: Catalog,
    pack: ResourcePack,
    cache: RenderCache,
) -> None:
    set_cells(service, {(0, 0, 0): "stone", (16, 0, 0): "stone", (32, 0, 0): "stone"})
    path = store(service).path
    first = cache.render(path, catalog, pack)
    set_cells(service, {(0, 0, 0): "oak_planks"})
    with (
        patch(
            "design_workbench.adapters.rendering.cache.decode_chunk", wraps=decode_chunk
        ) as decoded,
        patch(
            "design_workbench.adapters.rendering.cache.render_chunk", wraps=render_chunk
        ) as rendered,
    ):
        changed = cache.render(path, catalog, pack, first["chunk_versions"])
    assert decoded.call_count == rendered.call_count == 1
    assert set(changed["chunks"]) == {"0,0,0"}
    assert_reference(cache.render(path, catalog, pack), service, catalog, pack)


@pytest.mark.parametrize("neighbour", [(16, 15, 16), (16, 16, 16), (15, 16, 15)])
def test_fluid_diagonal_and_above_chunk_invalidation(
    neighbour: Point,
    service: SceneService,
    catalog: Catalog,
    pack: ResourcePack,
    cache: RenderCache,
) -> None:
    set_cells(service, {(15, 15, 15): "water", neighbour: "water", (64, 0, 0): "stone"})
    path = store(service).path
    first = cache.render(path, catalog, pack)
    set_cells(
        service,
        {
            neighbour: {"name": "water", "properties": {"level": "7"}}
            if neighbour[1] == 15
            else "air"
        },
    )
    changed = cache.render(path, catalog, pack, first["chunk_versions"])
    assert "0,0,0" in changed["chunks"]
    assert "4,0,0" not in changed["chunks"]
    assert_reference(cache.render(path, catalog, pack), service, catalog, pack)


def test_external_payload_edit_without_revision_increase_is_observed(
    service: SceneService,
    catalog: Catalog,
    pack: ResourcePack,
    cache: RenderCache,
) -> None:
    set_cells(service, {(0, 0, 0): "stone", (16, 0, 0): "stone"})
    path = store(service).path
    first = cache.render(path, catalog, pack)
    with store(service).connection() as connection:
        connection.execute(
            "UPDATE chunks SET payload=? WHERE x=0",
            (
                encode(
                    {
                        "palette": [{"name": "minecraft:oak_planks", "properties": {}}],
                        "cells": [[0, 0, "external", "design"]],
                    }
                ),
            ),
        )
    changed = cache.render(path, catalog, pack, first["chunk_versions"])
    assert changed["revision"] == first["revision"]
    assert set(changed["chunks"]) == {"0,0,0"}
    assert changed["summary"]["groups"] == {"external": 1, "main": 1}
    assert_reference(cache.render(path, catalog, pack), service, catalog, pack)


def test_protection_metadata_invalidation_and_deleted_chunk(
    service: SceneService,
    catalog: Catalog,
    pack: ResourcePack,
    cache: RenderCache,
) -> None:
    set_cells(service, {(0, 0, 0): "stone", (16, 0, 0): "stone"})
    path = store(service).path
    first = cache.render(path, catalog, pack)
    with store(service).connection() as connection:
        data = SqliteStore._meta(connection)
        data["protected"] = [[0, 0, 0]]
        connection.execute("UPDATE meta SET value=? WHERE key='scene'", (json.dumps(data),))
        connection.execute("DELETE FROM chunks WHERE x=1")
    with patch(
        "design_workbench.adapters.rendering.cache.decode_chunk", wraps=decode_chunk
    ) as decoded:
        changed = cache.render(path, catalog, pack, first["chunk_versions"])
    assert decoded.call_count == 0
    assert changed["chunks"]["0,0,0"][0][-1] is True
    assert changed["removed_chunks"] == ["1,0,0"]
    assert changed["summary"]["protected_cells"] == 1 and changed["summary"]["blocks"] == 1


def sign_source(text: str) -> bytes:
    def vector(x: int, y: int, z: int) -> Any:
        return nbtlib.Compound(
            {name: nbtlib.Int(value) for name, value in zip("xyz", (x, y, z), strict=True)}
        )

    root = nbtlib.File(
        {
            "Version": nbtlib.Int(6),
            "MinecraftDataVersion": nbtlib.Int(3465),
            "Regions": nbtlib.Compound(
                {
                    "sign": nbtlib.Compound(
                        {
                            "Position": vector(0, 0, 0),
                            "Size": vector(1, 1, 1),
                            "TileEntities": nbtlib.List[nbtlib.Compound](
                                [
                                    nbtlib.Compound(
                                        {
                                            "id": nbtlib.String("minecraft:sign"),
                                            "x": nbtlib.Int(0),
                                            "y": nbtlib.Int(0),
                                            "z": nbtlib.Int(0),
                                            "Text1": nbtlib.String(json.dumps(text)),
                                        }
                                    )
                                ]
                            ),
                        }
                    )
                }
            ),
        }
    )
    stream = io.BytesIO()
    root.write(stream)
    return stream.getvalue()


def test_attachment_change_invalidates_only_sign_chunk(
    service: SceneService,
    catalog: Catalog,
    pack: ResourcePack,
    cache: RenderCache,
) -> None:
    set_cells(service, {(0, 0, 0): "oak_sign", (32, 0, 0): "stone"})
    path = store(service).path
    with store(service).connection() as connection:
        connection.execute("INSERT INTO attachments VALUES('litematic',?)", (sign_source("first"),))
    first = cache.render(path, catalog, pack)
    with store(service).connection() as connection:
        connection.execute("UPDATE attachments SET payload=?", (sign_source("second"),))
    with patch(
        "design_workbench.adapters.rendering.cache.decode_chunk", wraps=decode_chunk
    ) as decoded:
        changed = cache.render(path, catalog, pack, first["chunk_versions"])
    assert decoded.call_count == 0
    assert set(changed["chunks"]) == {"0,0,0"}
    assert next(iter(changed["models"].values()))["texts"][0]["lines"][0] == "second"
    assert_reference(cache.render(path, catalog, pack), service, catalog, pack)


def test_resource_switch_resends_geometry_and_history_rename_are_coherent(
    service: SceneService,
    catalog: Catalog,
    pack: ResourcePack,
    cache: RenderCache,
) -> None:
    set_cells(service, {(0, 0, 0): "stone"})
    path = store(service).path
    first = cache.render(path, catalog, pack)
    second_pack = cast(ResourcePack, MinimalPack("second"))
    changed = cache.render(path, catalog, second_pack, first["chunk_versions"])
    assert changed["chunks"] and changed["models"]
    service.rename(RenameRequest(expected_revision=1, request_id="rename", name="renamed"))
    with patch(
        "design_workbench.adapters.rendering.cache.decode_chunk",
        side_effect=AssertionError("decode"),
    ):
        summary = cache.summary(path)
    assert summary["name"] == "renamed" and summary["revision"] == 2
    assert summary["events"][0]["revision"] == 2
    service.history("undo", HistoryRequest(expected_revision=2, request_id="undo-rename"))
    assert cache.summary(path)["name"] == "测试"
    service.history("undo", HistoryRequest(expected_revision=3, request_id="undo-set"))
    removed = cache.render(path, catalog, second_pack, changed["chunk_versions"])
    assert removed["removed_chunks"] == ["0,0,0"] and removed["summary"]["blocks"] == 0
    service.history("redo", HistoryRequest(expected_revision=4, request_id="redo-set"))
    assert cache.summary(path)["blocks"] == 1


def test_cache_project_cell_and_byte_limits_close_evicted_connections(
    tmp_path: Path, catalog: Catalog, pack: ResourcePack
) -> None:
    paths = []
    for index in range(3):
        path = tmp_path / f"{index}.dwbench"
        SqliteStore.create(
            path, str(index), catalog.version, catalog.data_version, Bounds((0, 0, 0), (1, 1, 1))
        )
        paths.append(path)
    instance = RenderCache(max_projects=2)
    try:
        instance.summary(paths[0])
        first_connection = instance._entries[paths[0]].connection
        instance.summary(paths[1])
        instance.summary(paths[2])
        assert list(instance._entries) == paths[1:]
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            first_connection.execute("SELECT 1")
    finally:
        instance.close()
    for kwargs in ({"max_cells": 1}, {"max_bytes": 1}):
        instance = RenderCache(**kwargs)
        try:
            repository = SqliteStore(paths[0])
            scene = repository.load()
            scene.cells = {
                (0, 0, 0): Cell(catalog.default("stone")),
                (1, 0, 0): Cell(catalog.default("stone")),
            }
            repository.commit(
                scene,
                [(point, None, cell) for point, cell in scene.cells.items()],
                scene.revision,
                f"cap-{scene.revision}",
                "cap",
            )
            assert instance.render(paths[0], catalog, pack)["summary"]["blocks"] == 2
            assert not instance._entries
        finally:
            instance.close()


def test_concurrent_readers_receive_coherent_revision_and_summary(
    service: SceneService,
    catalog: Catalog,
    pack: ResourcePack,
    cache: RenderCache,
) -> None:
    path = store(service).path

    def writer() -> None:
        for index in range(20):
            set_cells(service, {(index, 0, 0): "stone"})

    def reader() -> None:
        for _ in range(40):
            summary = cache.summary(path)
            assert summary["revision"] == summary["blocks"]
            if summary["events"]:
                assert summary["events"][0]["revision"] == summary["revision"]
            packet = cache.render(path, catalog, pack)
            assert packet["revision"] == packet["summary"]["blocks"]

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(writer), *(executor.submit(reader) for _ in range(4))]
        for future in futures:
            future.result()
    assert cache.summary(path)["blocks"] == 20


def test_http_render_and_summary_use_cache_and_shutdown_closes_it(
    tmp_path: Path, pack: ResourcePack
) -> None:
    settings = Settings(
        data_dir=tmp_path / "data", cache_dir=tmp_path / "cache", log_dir=tmp_path / "logs"
    )
    app = create_app(settings)
    app.state.workbench.pack = pack
    with TestClient(app) as client:
        identifier = client.post("/api/projects", json={"name": "cache"}).json()["project_id"]
        path = f"/api/projects/{identifier}"
        client.post(
            path + "/edit",
            json={
                "expected_revision": 0,
                "request_id": "http",
                "operations": [
                    {"op": "set", "blocks": [{"position": [0, 0, 0], "state": {"name": "stone"}}]}
                ],
            },
        )
        first = client.post(path + "/render", json={}).json()
        with patch.object(SqliteStore, "load", side_effect=AssertionError("full load")):
            assert not client.post(path + "/render", json=first["chunk_versions"]).json()["chunks"]
            assert client.get(path).json()["blocks"] == 1
            assert client.get("/api/projects").json()["items"][0]["blocks"] == 1
    assert not app.state.render_cache._entries


def test_stored_air_summary_and_import_undo_attachment_invalidation(
    service: SceneService,
    catalog: Catalog,
    pack: ResourcePack,
    cache: RenderCache,
) -> None:
    repository = store(service)
    path = repository.path
    initial = cache.render(path, catalog, pack)
    assert service.formats is not None
    scene = Scene(
        "fixture",
        "imported",
        catalog.version,
        catalog.data_version,
        0,
        Bounds((-2, -2, -2), (2, 2, 2)),
        {
            (0, 0, 0): Cell(catalog.default("oak_sign")),
            (1, 0, 0): Cell(BlockState.make("cave_air")),
            (2, 0, 0): Cell(BlockState.make("void_air")),
        },
    )
    payload, _ = service.formats.write(scene)
    root = nbtlib.File.parse(io.BytesIO(gzip.decompress(payload)))
    region = next(iter(root["Regions"].values()))
    region["TileEntities"].append(
        nbtlib.Compound(
            {
                "id": nbtlib.String("minecraft:sign"),
                "x": nbtlib.Int(0),
                "y": nbtlib.Int(0),
                "z": nbtlib.Int(0),
                "Text1": nbtlib.String('"imported text"'),
            }
        )
    )
    stream = io.BytesIO()
    root.write(stream)
    payload = gzip.compress(stream.getvalue())
    service.import_asset(payload, HistoryRequest(expected_revision=0, request_id="import"))
    imported = cache.render(path, catalog, pack, initial["chunk_versions"])
    assert imported["summary"]["blocks"] == 1 and imported["summary"]["stored_cells"] == 3
    assert imported["summary"]["protected_cells"] == 1
    assert_reference(cache.render(path, catalog, pack), service, catalog, pack)
    service.history("undo", HistoryRequest(expected_revision=1, request_id="undo-import"))
    undone = cache.render(path, catalog, pack, imported["chunk_versions"])
    assert undone["removed_chunks"] == ["0,0,0"] and undone["summary"]["blocks"] == 0
    assert repository.attachment() is None
    service.history("redo", HistoryRequest(expected_revision=2, request_id="redo-import"))
    assert_reference(cache.render(path, catalog, pack), service, catalog, pack)


def test_deleted_project_and_corrupt_projection_are_evicted(
    service: SceneService,
    catalog: Catalog,
    pack: ResourcePack,
    cache: RenderCache,
) -> None:
    set_cells(service, {(0, 0, 0): "stone"})
    repository = store(service)
    path = repository.path
    cache.render(path, catalog, pack)
    connection = cache._entries[path].connection
    with repository.connection() as writer:
        writer.execute("UPDATE chunks SET payload=?", (b"invalid compressed chunk",))
    with pytest.raises(WorkbenchError) as corruption:
        cache.summary(path)
    assert corruption.value.code == "DATABASE_CORRUPT"
    assert not cache._entries
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connection.execute("SELECT 1")
    with repository.connection() as writer:
        writer.execute("DELETE FROM chunks")
    assert cache.summary(path)["blocks"] == 0
    cache.close()
    path.unlink()
    with pytest.raises(WorkbenchError) as missing:
        cache.summary(path)
    assert missing.value.code == "PROJECT_NOT_FOUND"


@pytest.mark.skipif(
    sys.platform == "win32", reason="Windows locks an open SQLite file against replacement"
)
def test_project_file_replacement_invalidates_observer(
    service: SceneService,
    catalog: Catalog,
    pack: ResourcePack,
    cache: RenderCache,
    tmp_path: Path,
) -> None:
    set_cells(service, {(0, 0, 0): "stone"})
    path = store(service).path
    with store(service).connection() as connection:
        connection.execute("PRAGMA journal_mode=DELETE")
    cache.render(path, catalog, pack)
    replacement = SqliteStore.create(
        tmp_path / "replacement.dwbench",
        "new project",
        catalog.version,
        catalog.data_version,
        Bounds((0, 0, 0), (1, 1, 1)),
    )
    with replacement.connection() as connection:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.execute("PRAGMA journal_mode=DELETE")
    # The atomic replacement must reopen the observer, even if the old inode
    # remains open and revision/cell counts happen to match.
    replacement.path.replace(path)
    assert cache.summary(path)["name"] == "new project"
