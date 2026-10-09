from pathlib import Path

import pytest

from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.adapters.storage.sqlite import SqliteStore
from design_workbench.domain.models import Bounds, Cell, chunk_key


@pytest.mark.parametrize("dense", [False, True])
def test_partial_chunk_rewrite_preserves_palette_air_groups_regions_and_negative_positions(
    dense: bool,
    tmp_path: Path,
    catalog: Catalog,
) -> None:
    repository = SqliteStore.create(
        tmp_path / "partial.dwbench",
        "partial",
        catalog.version,
        catalog.data_version,
        Bounds((-64, -32, -64), (64, 32, 64)),
    )
    scene = repository.load()
    stone = Cell(catalog.default("stone"), "group-stone", "region-stone")
    changed_key = (-1, -1, -1)
    scene.cells.update(
        {
            (-1, -1, -1): stone,
            (-16, -16, -16): stone,
            (-17, -1, -1): stone,
            (0, 0, 0): stone,
            (-2, -2, -2): Cell(catalog.default("cave_air"), "air", "preserved"),
        }
    )
    if dense:
        scene.cells.update(
            {(x, y, z): stone for x in range(32) for y in range(8) for z in range(32)}
        )
    repository.commit(
        scene, [(point, None, cell) for point, cell in scene.cells.items()], 0, "initial", "initial"
    )
    with repository.connection() as connection:
        before = {
            tuple(row[:3]): (bytes(row[3]), row[4])
            for row in connection.execute("SELECT x,y,z,payload,revision FROM chunks")
        }
    scene.cells[(-1, -1, -1)] = Cell(catalog.default("oak_planks"), "new-group", "new-region")
    del scene.cells[(-16, -16, -16)]
    with repository.connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        repository._write_chunks(connection, scene.cells, {changed_key}, 2)
        connection.commit()
        after = {
            tuple(row[:3]): (bytes(row[3]), row[4])
            for row in connection.execute("SELECT x,y,z,payload,revision FROM chunks")
        }
    assert repository.load().cells == scene.cells
    assert before.keys() == after.keys()
    assert after[changed_key][1] == 2
    for key in before.keys() - {changed_key}:
        assert before[key] == after[key]
    # Removing the last occupied cells still keeps explicit stored air. Removing
    # that air then removes the chunk without rewriting unrelated chunks.
    for point in list(scene.cells):
        if chunk_key(point) == changed_key:
            del scene.cells[point]
    with repository.connection() as connection:
        repository._write_chunks(connection, scene.cells, {changed_key}, 3)
        assert (
            connection.execute("SELECT 1 FROM chunks WHERE x=-1 AND y=-1 AND z=-1").fetchone()
            is None
        )
    assert repository.load().cells == scene.cells
