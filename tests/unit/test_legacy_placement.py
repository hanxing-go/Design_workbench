import pytest

from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.models import BlockState
from design_workbench.domain.placement import snap_state


@pytest.mark.parametrize(
    "torch,wall",
    [
        ("torch", "wall_torch"),
        ("soul_torch", "soul_wall_torch"),
        ("redstone_torch", "redstone_wall_torch"),
    ],
)
def test_torch_shape_converts_both_ways_without_mutating_manual_settings(
    catalog: Catalog, torch: str, wall: str
) -> None:
    manual = catalog.normalize(BlockState.make(wall, {"facing": "west"}))
    for face in ("north", "south", "east", "west"):
        snapped = catalog.normalize(snap_state(manual, face))
        assert snapped.name == "minecraft:" + wall
        assert dict(snapped.properties)["facing"] == face
    floor = catalog.normalize(snap_state(manual, "up"))
    assert floor.name == "minecraft:" + torch and "facing" not in dict(floor.properties)
    assert dict(manual.properties)["facing"] == "west"
    with pytest.raises(WorkbenchError):
        snap_state(manual, "down")


def test_every_wood_sign_and_hanging_sign_converts_legally(catalog: Catalog) -> None:
    for name in catalog.blocks:
        if not name.endswith("_sign"):
            continue
        hanging = name.endswith("_hanging_sign")
        state = catalog.normalize(BlockState.make(name, {"waterlogged": "true"}))
        for face in ("east", "west", "north", "south", "down" if hanging else "up"):
            result = catalog.normalize(snap_state(state, face, "north"))
            props = dict(result.properties)
            assert props["waterlogged"] == "true"
            if face in ("east", "west", "north", "south"):
                assert props["facing"] == face and "rotation" not in props
            else:
                assert props["rotation"] == "0" and "facing" not in props
                if hanging:
                    assert props["attached"] == "true"


def test_attachment_properties_and_unsupported_faces(catalog: Catalog) -> None:
    cases = [
        ("ladder", "east", {"facing": "east"}),
        ("lever", "down", {"face": "ceiling"}),
        ("stone_button", "up", {"face": "floor"}),
        ("lantern", "down", {"hanging": "true"}),
        ("oak_trapdoor", "north", {"facing": "north", "half": "top"}),
        ("end_rod", "down", {"facing": "down"}),
        ("vine", "east", {"west": "true"}),
    ]
    for name, face, expected in cases:
        state = catalog.normalize(snap_state(catalog.default(name), face, height=0.9))
        assert expected.items() <= dict(state.properties).items()
    for name, face in [
        ("ladder", "up"),
        ("lantern", "east"),
        ("oak_sign", "down"),
        ("oak_hanging_sign", "up"),
    ]:
        with pytest.raises(WorkbenchError):
            snap_state(catalog.default(name), face)


def test_support_policy_accepts_full_blocks_and_rejects_partial_models(catalog: Catalog) -> None:
    for name in ("stone", "bedrock", "oak_planks", "glass", "blue_stained_glass"):
        assert catalog.supports_attachment(catalog.default(name))
    for name in ("oak_slab", "oak_stairs", "oak_fence", "glass_pane", "water", "air"):
        assert not catalog.supports_attachment(catalog.default(name))
