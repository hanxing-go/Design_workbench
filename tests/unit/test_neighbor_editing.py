from typing import Any

import pytest

from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.application.contracts import EditRequest, HistoryRequest
from design_workbench.application.scenes import SceneService
from design_workbench.domain.editing import EditLimits, Editor
from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.models import BlockState, Bounds, Cell, Point, Scene
from design_workbench.domain.validation import inspect_consistency


def scene(catalog: Catalog, blocks: list[tuple[Point, str, dict[str, str]]]) -> Scene:
    return Scene(
        "id",
        "neighbors",
        catalog.version,
        catalog.data_version,
        0,
        Bounds((-20, -20, -20), (20, 20, 20)),
        {
            point: Cell(catalog.normalize(BlockState.make(name, props)))
            for point, name, props in blocks
        },
    )


def put(position: Point, name: str, **properties: str) -> dict[str, Any]:
    return {"position": position, "state": {"name": name, "properties": properties}}


def states(value: Scene | Any, point: Point) -> dict[str, str]:
    return dict(value.cells[point].state.properties)


def test_panes_bars_colors_connect_and_delete_updates_both_neighbors(catalog: Catalog) -> None:
    original = scene(catalog, [])
    editor = Editor(catalog, EditLimits())
    plan = editor.plan(
        original,
        [
            {
                "op": "set",
                "blocks": [
                    put((0, 0, 0), "red_stained_glass_pane"),
                    put((1, 0, 0), "iron_bars"),
                    put((2, 0, 0), "blue_stained_glass_pane"),
                ],
            }
        ],
    )
    assert states(plan, (0, 0, 0))["east"] == "true"
    assert states(plan, (1, 0, 0))["west"] == "true"
    assert states(plan, (1, 0, 0))["east"] == "true"
    assert states(plan, (2, 0, 0))["west"] == "true"
    original.cells = plan.cells
    removed = editor.plan(
        original,
        [
            {
                "op": "delete",
                "selector": {
                    "bounds": {"low": [1, 0, 0], "high": [1, 0, 0]},
                },
            }
        ],
    )
    assert states(removed, (0, 0, 0))["east"] == "false"
    assert states(removed, (2, 0, 0))["west"] == "false"
    assert len(removed.changes) == 3


def test_fence_families_and_gate_axis(catalog: Catalog) -> None:
    original = scene(catalog, [])
    plan = Editor(catalog, EditLimits()).plan(
        original,
        [
            {
                "op": "set",
                "blocks": [
                    put((0, 0, 0), "oak_fence"),
                    put((1, 0, 0), "spruce_fence"),
                    put((2, 0, 0), "nether_brick_fence"),
                    put((0, 0, 1), "oak_fence_gate", facing="east"),
                    put((-1, 0, 0), "oak_fence_gate", facing="east"),
                ],
            }
        ],
    )
    assert states(plan, (0, 0, 0))["east"] == "true"
    assert states(plan, (0, 0, 0))["south"] == "true"
    assert states(plan, (0, 0, 0))["west"] == "false"
    assert states(plan, (1, 0, 0))["east"] == "false"
    assert states(plan, (2, 0, 0))["west"] == "false"


@pytest.mark.parametrize(
    "neighbor,properties,connect",
    [
        ("polished_granite", {}, True),
        ("glass", {}, True),
        ("oak_slab", {"type": "bottom"}, False),
        ("oak_slab", {"type": "double"}, True),
        ("chest", {}, False),
        ("lantern", {}, False),
        ("oak_leaves", {}, False),
        ("oak_stairs", {"facing": "west"}, True),
        ("oak_stairs", {"facing": "east"}, False),
    ],
)
def test_connections_use_complete_neighbor_face(
    catalog: Catalog, neighbor: str, properties: dict[str, str], connect: bool
) -> None:
    original = scene(catalog, [((1, 0, 0), neighbor, properties)])
    plan = Editor(catalog, EditLimits()).plan(
        original, [{"op": "set", "blocks": [put((0, 0, 0), "iron_bars")]}]
    )
    assert states(plan, (0, 0, 0))["east"] == str(connect).lower()


def test_wall_height_post_gate_and_removal(catalog: Catalog) -> None:
    original = scene(catalog, [])
    editor = Editor(catalog, EditLimits())
    plan = editor.plan(
        original,
        [
            {
                "op": "set",
                "blocks": [
                    put((-1, 0, 0), "cobblestone_wall"),
                    put((0, 0, 0), "mossy_cobblestone_wall"),
                    put((1, 0, 0), "oak_fence_gate", facing="north"),
                    put((0, 1, 0), "stone"),
                ],
            }
        ],
    )
    assert states(plan, (0, 0, 0))["west"] == "tall"
    assert states(plan, (0, 0, 0))["east"] == "tall"
    assert states(plan, (0, 0, 0))["up"] == "true"
    assert states(plan, (1, 0, 0))["in_wall"] == "true"
    original.cells = plan.cells
    plan = editor.plan(original, [{"op": "delete", "selector": {"name": "stone"}}])
    assert states(plan, (0, 0, 0))["west"] == "low"
    assert states(plan, (0, 0, 0))["up"] == "false"


def test_stair_corner_and_diagonal_blocker_update(catalog: Catalog) -> None:
    original = scene(catalog, [])
    editor = Editor(catalog, EditLimits())
    plan = editor.plan(
        original,
        [
            {
                "op": "set",
                "blocks": [
                    put((0, 0, 0), "oak_stairs", facing="north"),
                    put((0, 0, -1), "stone_brick_stairs", facing="west"),
                ],
            }
        ],
    )
    assert states(plan, (0, 0, 0))["shape"] == "outer_left"
    original.cells = plan.cells
    plan = editor.plan(
        original, [{"op": "set", "blocks": [put((1, 0, 0), "oak_stairs", facing="north")]}]
    )
    assert states(plan, (0, 0, 0))["shape"] == "straight"


def test_fill_connections_and_transform_reconnect_at_destination(catalog: Catalog) -> None:
    original = scene(catalog, [((5, 0, 0), "glass_pane", {})])
    editor = Editor(catalog, EditLimits())
    plan = editor.plan(
        original,
        [
            {
                "op": "fill",
                "bounds": {"low": [0, 0, 0], "high": [2, 0, 0]},
                "state": {"name": "glass_pane"},
                "group": "line",
            }
        ],
    )
    assert states(plan, (1, 0, 0))["west"] == "true"
    assert states(plan, (1, 0, 0))["east"] == "true"
    original.cells = plan.cells
    moved = editor.plan(
        original, [{"op": "transform", "selector": {"group": "line"}, "offset": [2, 0, 0]}]
    )
    assert states(moved, (4, 0, 0))["east"] == "true"
    assert states(moved, (5, 0, 0))["west"] == "true"


@pytest.mark.parametrize(
    "name", ["oak_door", "sunflower", "red_bed", "tall_seagrass", "small_dripleaf"]
)
def test_multiblock_completion_delete_and_replace(catalog: Catalog, name: str) -> None:
    original = scene(catalog, [])
    editor = Editor(catalog, EditLimits())
    plan = editor.plan(original, [{"op": "set", "blocks": [put((0, 0, 0), name)]}])
    assert len(plan.cells) == 2
    assert not inspect_consistency(
        Scene(
            **{
                **{
                    key: getattr(original, key)
                    for key in (
                        "id",
                        "name",
                        "minecraft_version",
                        "data_version",
                        "revision",
                        "bounds",
                    )
                },
                "cells": plan.cells,
            }
        ),
        catalog,
    )["issues"]
    original.cells = plan.cells
    removed = editor.plan(
        original, [{"op": "delete", "selector": {"bounds": {"low": [0, 0, 0], "high": [0, 0, 0]}}}]
    )
    assert removed.cells == {}
    replaced = editor.plan(original, [{"op": "set", "blocks": [put((0, 0, 0), "stone")]}])
    assert len(replaced.cells) == 1
    assert replaced.cells[(0, 0, 0)].state.name == "minecraft:stone"


def test_multiblock_batch_overlap_fails_and_explicit_complete_pair_succeeds(
    catalog: Catalog,
) -> None:
    original = scene(catalog, [])
    editor = Editor(catalog, EditLimits())
    with pytest.raises(WorkbenchError) as error:
        editor.plan(
            original,
            [
                {
                    "op": "fill",
                    "bounds": {"low": [0, 0, 0], "high": [0, 1, 0]},
                    "state": {"name": "oak_door"},
                }
            ],
        )
    assert error.value.code == "EDIT_COLLISION"
    assert original.cells == {}
    pair = editor.plan(
        original,
        [
            {
                "op": "set",
                "blocks": [
                    put((0, 0, 0), "oak_door", half="lower"),
                    put((0, 1, 0), "oak_door", half="upper"),
                ],
            }
        ],
    )
    assert len(pair.cells) == 2
    with pytest.raises(WorkbenchError) as error:
        editor.plan(
            original,
            [
                {
                    "op": "set",
                    "blocks": [
                        put((0, 0, 0), "oak_door"),
                        put((0, 0, 0), "stone"),
                    ],
                }
            ],
        )
    assert error.value.code == "EDIT_COLLISION"


def test_bed_reorientation_relocates_partner_and_is_atomic(catalog: Catalog) -> None:
    original = scene(catalog, [])
    editor = Editor(catalog, EditLimits())
    first = editor.plan(
        original, [{"op": "set", "blocks": [put((0, 0, 0), "red_bed", facing="north")]}]
    )
    original.cells = first.cells
    plan = editor.plan(
        original, [{"op": "set", "blocks": [put((0, 0, 0), "red_bed", facing="east")]}]
    )
    assert (0, 0, -1) not in plan.cells
    assert states(plan, (1, 0, 0))["part"] == "head"
    original.cells[(1, 0, 0)] = Cell(catalog.default("stone"))
    before = dict(original.cells)
    with pytest.raises(WorkbenchError):
        editor.plan(original, [{"op": "set", "blocks": [put((0, 0, 0), "red_bed", facing="east")]}])
    assert original.cells == before


def test_mature_pitcher_crop_completes_and_young_crop_removes_upper(catalog: Catalog) -> None:
    original = scene(catalog, [])
    editor = Editor(catalog, EditLimits())
    mature = editor.plan(
        original, [{"op": "set", "blocks": [put((0, 0, 0), "pitcher_crop", age="3")]}]
    )
    assert len(mature.cells) == 2
    original.cells = mature.cells
    young = editor.plan(
        original, [{"op": "set", "blocks": [put((0, 0, 0), "pitcher_crop", age="1")]}]
    )
    assert len(young.cells) == 1


def test_multiblock_obstruction_bounds_and_implicit_protection(catalog: Catalog) -> None:
    editor = Editor(catalog, EditLimits())
    original = scene(catalog, [((0, 1, 0), "stone", {})])
    with pytest.raises(WorkbenchError) as error:
        editor.plan(original, [{"op": "set", "blocks": [put((0, 0, 0), "oak_door")]}])
    assert error.value.code == "EDIT_COLLISION"
    with pytest.raises(WorkbenchError) as error:
        editor.plan(scene(catalog, []), [{"op": "set", "blocks": [put((0, 20, 0), "oak_door")]}])
    assert error.value.code == "OUT_OF_BOUNDS"
    original = scene(
        catalog,
        [((0, 0, 0), "oak_door", {"half": "lower"}), ((0, 1, 0), "oak_door", {"half": "upper"})],
    )
    original.protected.add((0, 1, 0))
    with pytest.raises(WorkbenchError) as error:
        editor.plan(
            original,
            [{"op": "delete", "selector": {"bounds": {"low": [0, 0, 0], "high": [0, 0, 0]}}}],
        )
    assert error.value.code == "PROTECTED_CONTENT"


def test_neighbor_changes_respect_implicit_limits_and_protection(catalog: Catalog) -> None:
    original = scene(catalog, [((0, 0, 0), "iron_bars", {})])
    original.protected.add((0, 0, 0))
    with pytest.raises(WorkbenchError) as error:
        Editor(catalog, EditLimits()).plan(
            original, [{"op": "set", "blocks": [put((1, 0, 0), "iron_bars")]}]
        )
    assert error.value.code == "PROTECTED_CONTENT"
    with pytest.raises(WorkbenchError) as error:
        Editor(catalog, EditLimits(max_blocks=1)).plan(
            scene(catalog, []), [{"op": "set", "blocks": [put((0, 0, 0), "oak_door")]}]
        )
    assert error.value.code == "EDIT_LIMIT"


def test_exact_mode_preserves_partial_structure_and_user_shape(catalog: Catalog) -> None:
    plan = Editor(catalog, EditLimits()).plan(
        scene(catalog, []),
        [
            {
                "op": "set",
                "blocks": [
                    put((0, 0, 0), "oak_door"),
                    put((2, 0, 0), "oak_stairs", shape="inner_left"),
                    put((4, 0, 0), "iron_bars"),
                    put((5, 0, 0), "iron_bars"),
                ],
            }
        ],
        auto_connect=False,
        complete_structures=False,
    )
    assert len(plan.cells) == 4
    assert states(plan, (2, 0, 0))["shape"] == "inner_left"
    assert states(plan, (4, 0, 0))["east"] == "false"


def test_support_loss_is_reported_without_deleting_attachment(catalog: Catalog) -> None:
    original = scene(catalog, [((0, 0, 0), "stone", {}), ((1, 0, 0), "ladder", {"facing": "east"})])
    plan = Editor(catalog, EditLimits()).plan(
        original, [{"op": "delete", "selector": {"name": "stone"}}]
    )
    original.cells = plan.cells
    assert (1, 0, 0) in original.cells
    assert inspect_consistency(original, catalog)["issues"][0]["code"] == "MISSING_SUPPORT"


def test_place_operation_history_covers_pair_and_neighbors(service: SceneService) -> None:
    request = EditRequest.model_validate(
        {
            "expected_revision": 0,
            "request_id": "place-door",
            "operations": [
                {
                    "op": "place",
                    "state": {"name": "oak_door"},
                    "hit": [0, -1, 0],
                    "normal": [0, 1, 0],
                    "location": [0.5, 1, 0.5],
                    "facing": "north",
                }
            ],
        }
    )
    assert service.edit(request, preview=True)["changed"] == 2
    assert service.summary()["blocks"] == 0
    assert service.edit(request)["changed"] == 2
    assert service.edit(request)["changed"] == 2
    service.history("undo", HistoryRequest(expected_revision=1, request_id="undo"))
    assert service.summary()["blocks"] == 0
    service.history("redo", HistoryRequest(expected_revision=2, request_id="redo"))
    assert service.summary()["blocks"] == 2


def test_neighbor_history_preview_and_export_preserve_derived_states(service: SceneService) -> None:
    service.edit(
        EditRequest.model_validate(
            {
                "expected_revision": 0,
                "request_id": "first-pane",
                "operations": [
                    {
                        "op": "set",
                        "blocks": [put((0, 0, 0), "red_stained_glass_pane")],
                    }
                ],
            }
        )
    )
    second = EditRequest.model_validate(
        {
            "expected_revision": 1,
            "request_id": "second-pane",
            "operations": [
                {
                    "op": "set",
                    "blocks": [put((1, 0, 0), "iron_bars")],
                }
            ],
        }
    )
    assert service.edit(second, preview=True)["changed"] == 2
    assert states(service.repository.load(), (0, 0, 0))["east"] == "false"
    assert service.edit(second)["changed"] == 2
    payload, _ = service.export_asset(2)
    assert service.formats is not None
    exported, _ = service.formats.read(payload)
    assert states(exported, (0, 0, 0))["east"] == "true"
    assert states(exported, (1, 0, 0))["west"] == "true"
    service.history("undo", HistoryRequest(expected_revision=2, request_id="undo-neighbor"))
    assert states(service.repository.load(), (0, 0, 0))["east"] == "false"
    assert (1, 0, 0) not in service.repository.load().cells
    service.history("redo", HistoryRequest(expected_revision=3, request_id="redo-neighbor"))
    assert states(service.repository.load(), (0, 0, 0))["east"] == "true"


def test_chest_pairing_direction_triples_types_and_removal(catalog: Catalog) -> None:
    original = scene(catalog, [])
    editor = Editor(catalog, EditLimits())
    plan = editor.plan(
        original,
        [
            {
                "op": "set",
                "blocks": [
                    put((0, 0, 0), "chest", facing="north"),
                    put((1, 0, 0), "chest", facing="north"),
                    put((2, 0, 0), "chest", facing="north"),
                    put((3, 0, 0), "trapped_chest", facing="north"),
                ],
            }
        ],
    )
    assert states(plan, (0, 0, 0))["type"] == "left"
    assert states(plan, (1, 0, 0))["type"] == "right"
    assert states(plan, (2, 0, 0))["type"] == "single"
    assert states(plan, (3, 0, 0))["type"] == "single"
    original.cells = plan.cells
    removed = editor.plan(
        original, [{"op": "delete", "selector": {"bounds": {"low": [1, 0, 0], "high": [1, 0, 0]}}}]
    )
    assert states(removed, (0, 0, 0))["type"] == "single"
    assert states(removed, (2, 0, 0))["type"] == "single"
    assert len(removed.changes) == 2


def test_shape_support_faces_settle_before_pane_connections(catalog: Catalog) -> None:
    plan = Editor(catalog, EditLimits()).plan(
        scene(catalog, []),
        [
            {
                "op": "set",
                "blocks": [
                    put((0, 0, 0), "iron_bars"),
                    put((1, 0, 0), "oak_stairs", facing="north"),
                    put((1, 0, 1), "oak_stairs", facing="west"),
                ],
            }
        ],
    )
    assert states(plan, (1, 0, 0))["shape"] == "inner_left"
    assert states(plan, (0, 0, 0))["east"] == "true"


def test_wall_posts_propagate_down_stack_on_roof_add_and_remove(catalog: Catalog) -> None:
    original = scene(catalog, [])
    editor = Editor(catalog, EditLimits())
    plan = editor.plan(
        original,
        [
            {
                "op": "set",
                "blocks": [
                    put((x, y, 0), "cobblestone_wall") for x in (-1, 0, 1) for y in range(6)
                ],
            }
        ],
    )
    assert all(states(plan, (0, y, 0))["up"] == "false" for y in range(6))
    original.cells = plan.cells
    roof = editor.plan(original, [{"op": "set", "blocks": [put((0, 6, 0), "stone")]}])
    assert all(states(roof, (0, y, 0))["up"] == "true" for y in range(6))
    original.cells = roof.cells
    removed = editor.plan(original, [{"op": "delete", "selector": {"name": "stone"}}])
    assert all(states(removed, (0, y, 0))["up"] == "false" for y in range(6))


@pytest.mark.parametrize(
    "old,new,properties",
    [
        ("oak_door", "spruce_door", {"facing": "west"}),
        ("red_bed", "blue_bed", {"facing": "east"}),
        ("sunflower", "lilac", {}),
    ],
)
def test_replace_complete_multiblock_preserves_parts_and_footprint(
    catalog: Catalog, old: str, new: str, properties: dict[str, str]
) -> None:
    original = scene(catalog, [])
    editor = Editor(catalog, EditLimits())
    original.cells = editor.plan(
        original, [{"op": "set", "blocks": [put((0, 0, 0), old, **properties)]}]
    ).cells
    positions = set(original.cells)
    replaced = editor.plan(
        original, [{"op": "replace", "selector": {"name": old}, "state": {"name": new}}]
    )
    assert set(replaced.cells) == positions
    assert all(cell.state.name == f"minecraft:{new}" for cell in replaced.cells.values())
    original.cells = replaced.cells
    assert not any(
        issue["code"] in {"MISSING_PARTNER", "PARTNER_STATE"}
        for issue in inspect_consistency(original, catalog)["issues"]
    )


def test_exact_connection_mode_still_completes_door(catalog: Catalog) -> None:
    plan = Editor(catalog, EditLimits()).plan(
        scene(catalog, []),
        [{"op": "set", "blocks": [put((0, 0, 0), "oak_door")]}],
        auto_connect=False,
    )
    assert len(plan.cells) == 2


def test_missing_partner_repair_proposals_avoid_conflicts_and_protected(catalog: Catalog) -> None:
    original = scene(catalog, [((0, 0, 0), "oak_door", {"half": "lower"})])
    proposals = inspect_consistency(original, catalog)["proposals"]
    assert len(proposals) == 1
    assert proposals[0]["position"] == (0, 1, 0)
    plan = Editor(catalog, EditLimits()).plan(original, [{"op": "set", "blocks": proposals}])
    original.cells = plan.cells
    assert not inspect_consistency(original, catalog)["issues"]
    original = scene(
        catalog,
        [
            ((0, 0, 0), "oak_door", {"half": "lower"}),
            ((0, 2, 0), "oak_door", {"half": "upper"}),
        ],
    )
    assert not inspect_consistency(original, catalog)["proposals"]
    original.cells.pop((0, 2, 0))
    original.protected.add((0, 0, 0))
    assert not inspect_consistency(original, catalog)["proposals"]


def test_multiblock_edit_keeps_counterpart_source_region(catalog: Catalog) -> None:
    original = scene(
        catalog,
        [
            ((0, 0, 0), "oak_door", {"half": "lower"}),
            ((0, 1, 0), "oak_door", {"half": "upper"}),
        ],
    )
    original.cells[(0, 1, 0)] = Cell(original.cells[(0, 1, 0)].state, "main", "imported-upper")
    plan = Editor(catalog, EditLimits()).plan(
        original, [{"op": "set", "blocks": [put((0, 0, 0), "oak_door", open="true")]}]
    )
    assert plan.cells[(0, 1, 0)].region == "imported-upper"
