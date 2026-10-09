from typing import Any

import pytest

from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.domain.editing import EditLimits, Editor
from design_workbench.domain.models import Bounds, Cell, Scene


@pytest.mark.parametrize(
    "operations",
    [
        [
            {
                "op": "set",
                "blocks": [
                    {"position": [-1, 0, 0], "state": {"name": "oak_planks"}, "group": "changed"},
                    {"position": [0, 0, 0], "state": {"name": "oak_planks"}},
                ],
            },
            {
                "op": "set",
                "blocks": [
                    {"position": [-1, 0, 0], "state": {"name": "stone"}, "group": "original"}
                ],
            },
            {
                "op": "fill",
                "bounds": {"low": [2, 0, 0], "high": [4, 0, 0]},
                "state": {"name": "cave_air"},
            },
            {"op": "delete", "selector": {"bounds": {"low": [2, 0, 0], "high": [4, 0, 0]}}},
        ],
        [
            {
                "op": "array",
                "selector": {"bounds": {"low": [-1, 0, 0], "high": [0, 0, 0]}},
                "count": [3, 1, 1],
                "step": [3, 0, 0],
            },
            {
                "op": "transform",
                "selector": {"bounds": {"low": [-1, 0, 0], "high": [6, 0, 0]}},
                "offset": [0, 1, 0],
                "rotation": 90,
                "origin": [0, 0, 0],
            },
            {
                "op": "group",
                "selector": {"bounds": {"low": [-8, 1, -8], "high": [8, 1, 8]}},
                "name": "transformed",
            },
        ],
    ],
)
def test_local_delta_matches_full_snapshot_diff_and_preserves_original(
    catalog: Catalog,
    operations: list[dict[str, Any]],
) -> None:
    stone = Cell(catalog.default("stone"), "original", "retained-region")
    cells = {(x, 0, z): stone for x in range(100) for z in range(10, 110)}
    cells[(-1, 0, 0)] = cells[(0, 0, 0)] = stone
    scene = Scene(
        "delta",
        "delta",
        catalog.version,
        catalog.data_version,
        0,
        Bounds((-128, -32, -128), (127, 32, 127)),
        cells,
    )
    original = dict(cells)
    plan = Editor(catalog, EditLimits()).plan(scene, operations)
    expected = [
        (point, original.get(point), plan.cells.get(point))
        for point in sorted(original.keys() | plan.cells.keys())
        if original.get(point) != plan.cells.get(point)
    ]
    assert plan.changes == expected
    assert len(plan.changes) < 30
    assert scene.cells == original
    assert plan.touched > len(plan.changes)
