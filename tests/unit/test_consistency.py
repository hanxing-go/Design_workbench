import pytest

from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.domain.editing import EditLimits, Editor
from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.models import BlockState, Bounds, Cell, Scene
from design_workbench.domain.validation import inspect_consistency


def test_missing_partner_and_connections_are_suggestions(catalog: Catalog) -> None:
    scene = Scene("id", "test", "1.20.1", 3465, 7, Bounds((-10, -10, -10), (10, 10, 10)))
    scene.cells[(0, 0, 0)] = Cell(catalog.default("oak_door"))
    scene.cells[(2, 0, 0)] = Cell(catalog.default("oak_fence"))
    scene.cells[(3, 0, 0)] = Cell(catalog.default("oak_fence"))
    before = dict(scene.cells)
    result = inspect_consistency(scene)
    assert result["revision"] == 7
    assert result["issues"][0]["code"] == "MISSING_PARTNER"
    assert len(result["proposals"]) == 3
    assert any(proposal["position"] == (0, 1, 0) for proposal in result["proposals"])
    assert scene.cells == before
    assert result["requires_confirmation"]


def test_complete_door_transform_and_protected_nbt(catalog: Catalog) -> None:
    scene = Scene(
        "id",
        "test",
        "1.20.1",
        3465,
        0,
        Bounds((-10, -10, -10), (10, 10, 10)),
        {
            (0, 0, 0): Cell(catalog.normalize(BlockState.make("oak_door", {"half": "lower"}))),
            (0, 1, 0): Cell(catalog.normalize(BlockState.make("oak_door", {"half": "upper"}))),
        },
    )
    editor = Editor(catalog, EditLimits())
    with pytest.raises(WorkbenchError) as error:
        editor.plan(
            scene,
            [
                {
                    "op": "transform",
                    "selector": {"bounds": {"low": [0, 0, 0], "high": [0, 0, 0]}},
                    "offset": [1, 0, 0],
                }
            ],
        )
    assert error.value.code == "INCOMPLETE_MULTIBLOCK"
    plan = editor.plan(scene, [{"op": "transform", "selector": {}, "offset": [1, 0, 0]}])
    assert (1, 0, 0) in plan.cells and (1, 1, 0) in plan.cells
    scene.protected.add((0, 0, 0))
    with pytest.raises(WorkbenchError) as error:
        editor.plan(scene, [{"op": "delete", "selector": {}}])
    assert error.value.code == "PROTECTED_CONTENT"
