import math

import pytest

from design_workbench.adapters.rendering.fluids import fluid_model
from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.adapters.resources.geometry import DIRECTIONS
from design_workbench.adapters.resources.special import HEAD_TEXTURES, special_geometry
from design_workbench.application.scenes import SceneService
from design_workbench.domain.models import BlockState, Cell


def points(face: dict) -> list[list[float]]:
    return [face["vertices"][i : i + 3] for i in range(0, 12, 3)]


def normal(face: dict) -> list[float]:
    a, b, _, d = points(face)
    u, v = [[other[i] - a[i] for i in range(3)] for other in (b, d)]
    cross = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
    length = math.sqrt(sum(value**2 for value in cross))
    return [value / length for value in cross]


def test_every_entity_preview_state_has_finite_geometry_and_valid_uvs(catalog: Catalog) -> None:
    names = [
        name
        for name in catalog.blocks
        if name.split(":", 1)[1].replace("_wall_", "_") in HEAD_TEXTURES
        or name.endswith(("_banner", "_shulker_box"))
        or name
        in {
            "minecraft:chest",
            "minecraft:trapped_chest",
            "minecraft:ender_chest",
            "minecraft:shulker_box",
            "minecraft:conduit",
            "minecraft:decorated_pot",
            "minecraft:bubble_column",
        }
    ]
    for name in names:
        for state in catalog.states(name):
            model = special_geometry(state)
            assert model is not None and model["faces"], state
            assert model["preview_note"], state
            for face in model["faces"]:
                assert len(face["vertices"]) == 12 and len(face["uv"]) == 8
                assert all(math.isfinite(value) for value in face["vertices"])
                assert all(0 <= value <= 1 for value in face["uv"]), (state, face)


@pytest.mark.parametrize("name", HEAD_TEXTURES)
def test_floor_and_wall_head_front_faces_follow_minecraft_rotation(
    name: str, catalog: Catalog
) -> None:
    for rotation, facing in ((0, "north"), (4, "east"), (8, "south"), (12, "west")):
        floor = special_geometry(
            catalog.normalize(BlockState.make(name, {"rotation": str(rotation)}))
        )
        assert floor is not None
        assert normal(floor["faces"][2]) == pytest.approx(DIRECTIONS[facing], abs=0.00001)
    wall_name = name.replace("_head", "_wall_head").replace("_skull", "_wall_skull")
    for facing in ("north", "east", "south", "west"):
        wall = special_geometry(catalog.normalize(BlockState.make(wall_name, {"facing": facing})))
        assert wall is not None
        assert normal(wall["faces"][2]) == pytest.approx(DIRECTIONS[facing], abs=0.00001)
        if name not in {"piglin_head", "dragon_head", "player_head"}:
            # Cube skulls touch their support block, 0.25m above the cell floor.
            axis = 0 if facing in {"west", "east"} else 2
            values = [p[axis] for f in wall["faces"] for p in points(f)]
            assert (max(values) if facing in {"north", "west"} else min(values)) == (
                1 if facing in {"north", "west"} else 0
            )
            assert min(p[1] for f in wall["faces"] for p in points(f)) == 0.25


@pytest.mark.parametrize("facing", ["north", "south", "west", "east"])
def test_closed_chest_lock_faces_the_requested_direction(facing: str, catalog: Catalog) -> None:
    state = catalog.normalize(BlockState.make("chest", {"facing": facing}))
    model = special_geometry(state)
    assert model is not None
    lock = [p for f in model["faces"][12:] for p in points(f)]
    axis = 0 if facing in {"west", "east"} else 2
    assert (
        min(p[axis] for p in lock) if facing in {"north", "west"} else max(p[axis] for p in lock)
    ) == (0 if facing in {"north", "west"} else 1)
    assert min(p[1] for p in lock) == 7 / 16


def test_double_chest_parts_join_at_cell_boundary(catalog: Catalog) -> None:
    # South-facing left half occupies the cell to the east of the right half.
    extents = {}
    for part in ("left", "right"):
        model = special_geometry(
            catalog.normalize(BlockState.make("chest", {"type": part, "facing": "south"}))
        )
        assert model is not None
        xs = [p[0] for f in model["faces"] for p in points(f)]
        extents[part] = min(xs), max(xs)
        assert all(face["texture"].endswith("normal_" + part) for face in model["faces"])
    assert extents == {"left": (0, 15 / 16), "right": (1 / 16, 1)}


def test_banner_color_and_wall_support_and_shulker_extent(catalog: Catalog) -> None:
    red = special_geometry(catalog.default("red_banner"))
    assert red is not None and {f.get("color") for f in red["faces"] if f.get("color")} == {
        "#b02e26"
    }
    for facing in ("north", "south", "west", "east"):
        model = special_geometry(
            catalog.normalize(BlockState.make("red_wall_banner", {"facing": facing}))
        )
        assert model is not None and len(model["faces"]) == 12
        axis = 0 if facing in {"west", "east"} else 2
        values = [p[axis] for f in model["faces"] for p in points(f)]
        assert (min(values) if facing in {"south", "east"} else max(values)) == pytest.approx(
            1 / 48 if facing in {"south", "east"} else 47 / 48, abs=0.000001
        )
    for state in catalog.states("minecraft:blue_shulker_box"):
        model = special_geometry(state)
        assert model is not None
        for axis in range(3):
            values = [p[axis] for f in model["faces"] for p in points(f)]
            assert (min(values), max(values)) == (0, 1)


def test_bubble_column_is_full_height_static_water(catalog: Catalog) -> None:
    model = special_geometry(catalog.default("bubble_column"))
    assert model is not None and model["render_layer"] == "translucent"
    assert all(p[1] == 1 for p in points(model["faces"][0]))
    assert model["faces"][0]["texture"] == "minecraft:block/water_still"
    assert "粒子" in model["preview_note"]


def test_water_and_bubble_columns_share_continuous_surface(
    service: SceneService, catalog: Catalog
) -> None:
    scene = service.repository.load()
    water, bubbles = catalog.default("water"), catalog.default("bubble_column")
    scene.cells = {
        (0, 0, 0): Cell(water, "main", "design"),
        (1, 0, 0): Cell(bubbles, "main", "design"),
    }
    a = fluid_model(scene, (0, 0, 0), water, catalog)
    b = fluid_model(scene, (1, 0, 0), bubbles, catalog)
    av, bv = a["faces"][0]["vertices"], b["faces"][0]["vertices"]
    assert av[4] == bv[1] and av[7] == bv[10]
    assert b["faces"][0]["texture"] == "minecraft:block/water_still"
    scene.cells[(0, 1, 0)] = Cell(bubbles, "main", "design")
    assert all(
        v == 1 for v in fluid_model(scene, (0, 0, 0), water, catalog)["faces"][0]["vertices"][1::3]
    )
