"""Pure, local block-state updates shared by editing and consistency inspection."""

from collections.abc import Mapping
from typing import Any

from .models import BlockState, Cell, Point

DIRECTIONS = ("north", "east", "south", "west")
VECTORS: dict[str, Point] = {
    "north": (0, 0, -1),
    "east": (1, 0, 0),
    "south": (0, 0, 1),
    "west": (-1, 0, 0),
}
OPPOSITE = {"north": "south", "east": "west", "south": "north", "west": "east"}


def add(point: Point, vector: Point) -> Point:
    return point[0] + vector[0], point[1] + vector[1], point[2] + vector[2]


def is_pane(name: str) -> bool:
    return name.endswith("_pane") or name == "minecraft:iron_bars"


def is_wall(name: str) -> bool:
    return name.endswith("_wall")


def full_face(
    cell: Cell | None,
    direction: str,
    registry: object | None = None,
    *,
    connection_exceptions: bool = True,
) -> bool:
    """Whether the neighbor presents a complete face for structural connections.

    Registry bounding boxes alone also describe stairs and thin shapes as "block";
    account for their state before using the registry's opaque full-block fallback.
    """
    if cell is None or cell.state.is_air:
        return False
    name = cell.state.name.split(":", 1)[-1]
    props = dict(cell.state.properties)
    if name.endswith("_leaves") or name in {
        "barrier",
        "pumpkin",
        "carved_pumpkin",
        "jack_o_lantern",
        "melon",
    }:
        return not connection_exceptions
    if name.endswith("_slab"):
        return (
            props.get("type") == "double"
            or (direction == "up" and props.get("type") == "top")
            or (direction == "down" and props.get("type") == "bottom")
        )
    if name.endswith("_stairs"):
        facing = props.get("facing", "north")
        shape = props.get("shape", "straight")
        side = DIRECTIONS[(DIRECTIONS.index(facing) + (-1 if shape == "inner_left" else 1)) % 4]
        return (
            (direction == facing and not shape.startswith("outer_"))
            or (shape.startswith("inner_") and direction == side)
            or (direction == "up" and props.get("half") == "top")
            or (direction == "down" and props.get("half") == "bottom")
        )
    if name in {"snow", "snow_layer"}:
        return props.get("layers") == "8"
    if (
        name.endswith(
            (
                "_pane",
                "_fence",
                "_fence_gate",
                "_wall",
                "_door",
                "_trapdoor",
                "_bed",
                "_sign",
                "_banner",
                "_head",
                "_skull",
                "_carpet",
                "_button",
                "_pressure_plate",
                "_rail",
                "_torch",
                "_candle",
                "_coral",
                "_coral_fan",
                "_sapling",
                "_flower",
                "_roots",
                "_bush",
                "_grate",
                "_shulker_box",
            )
        )
        or name
        in {
            "iron_bars",
            "ladder",
            "chain",
            "lantern",
            "soul_lantern",
            "torch",
            "lever",
            "chest",
            "trapped_chest",
            "ender_chest",
            "hopper",
            "cauldron",
            "water_cauldron",
            "lava_cauldron",
            "powder_snow_cauldron",
            "composter",
            "anvil",
            "chipped_anvil",
            "damaged_anvil",
            "enchanting_table",
            "farmland",
            "dirt_path",
            "daylight_detector",
            "scaffolding",
            "brewing_stand",
            "campfire",
            "soul_campfire",
            "cake",
            "flower_pot",
            "decorated_pot",
            "stonecutter",
            "bell",
            "bamboo",
            "cactus",
            "pointed_dripstone",
            "heavy_core",
            "grindstone",
            "lectern",
            "lily_pad",
            "dripleaf",
            "big_dripleaf",
            "small_dripleaf",
            "end_portal_frame",
            "dragon_egg",
            "turtle_egg",
            "sea_pickle",
            "candle",
            "shulker_box",
            "soul_sand",
            "mud",
            "honey_block",
            "slime_block",
        }
        or name.startswith("potted_")
    ):
        return False
    if name in {"glass", "ice", "packed_ice", "blue_ice"} or name.endswith("_stained_glass"):
        return True
    blocks: Any = getattr(registry, "blocks", {})
    metadata = blocks.get(cell.state.name, {}) if isinstance(blocks, Mapping) else {}
    if metadata:
        return metadata.get("boundingBox") == "block" and not metadata.get("transparent", False)
    return name in {
        "stone",
        "granite",
        "diorite",
        "andesite",
        "cobblestone",
        "bricks",
        "dirt",
        "grass_block",
        "sandstone",
        "quartz_block",
        "smooth_quartz",
        "stone_bricks",
        "deepslate",
        "netherrack",
        "end_stone",
        "obsidian",
        "bedrock",
        "sand",
        "gravel",
    } or name.endswith(
        (
            "_planks",
            "_log",
            "_wood",
            "_concrete",
            "_wool",
            "_terracotta",
            "_bricks",
            "_ore",
            "_block",
            "_nylium",
            "_hyphae",
            "_stem",
            "_sandstone",
        )
    )


def gate_connects(cell: Cell, direction: str) -> bool:
    facing = dict(cell.state.properties).get("facing", "north")
    return cell.state.name.endswith("_fence_gate") and (
        (direction in {"east", "west"}) == (facing in {"north", "south"})
    )


def stair_shape(point: Point, cells: Mapping[Point, Cell], properties: dict[str, str]) -> str:
    facing = properties.get("facing", "north")
    half = properties.get("half", "bottom")
    vector = VECTORS[facing]
    front = cells.get(add(point, vector))
    back = cells.get(add(point, VECTORS[OPPOSITE[facing]]))
    for neighbor, prefix in ((front, "outer"), (back, "inner")):
        if neighbor is None or not neighbor.state.name.endswith("_stairs"):
            continue
        props = dict(neighbor.state.properties)
        other = props.get("facing", facing)
        if (
            props.get("half", "bottom") != half
            or (DIRECTIONS.index(other) - DIRECTIONS.index(facing)) % 2 == 0
        ):
            continue
        blocking_direction = OPPOSITE[other] if prefix == "outer" else other
        blocking = cells.get(add(point, VECTORS[blocking_direction]))
        blocking_props = dict(blocking.state.properties) if blocking else {}
        if (
            blocking
            and blocking.state.name.endswith("_stairs")
            and blocking_props.get("facing") == facing
            and blocking_props.get("half") == half
        ):
            continue
        left = other == DIRECTIONS[(DIRECTIONS.index(facing) - 1) % 4]
        return prefix + ("_left" if left else "_right")
    return "straight"


def connected_state(
    point: Point, cells: Mapping[Point, Cell], registry: object | None = None
) -> BlockState | None:
    cell = cells.get(point)
    if cell is None:
        return None
    state = cell.state
    properties = dict(state.properties)
    replacement = dict(properties)
    name = state.name
    if is_pane(name) or name.endswith("_fence") or is_wall(name):
        above = cells.get(add(point, (0, 1, 0)))
        tall = full_face(above, "down", registry)
        above_props = dict(above.state.properties) if above else {}
        for direction, vector in VECTORS.items():
            neighbor = cells.get(add(point, vector))
            connect = full_face(neighbor, OPPOSITE[direction], registry)
            if neighbor:
                other = neighbor.state.name
                if is_pane(name):
                    connect |= is_pane(other) or is_wall(other)
                elif is_wall(name):
                    connect |= (
                        is_wall(other) or is_pane(other) or gate_connects(neighbor, direction)
                    )
                else:
                    same_material = (name == "minecraft:nether_brick_fence") == (
                        other == "minecraft:nether_brick_fence"
                    )
                    connect |= (other.endswith("_fence") and same_material) or gate_connects(
                        neighbor, direction
                    )
            arm_tall = tall or bool(
                above and is_wall(above.state.name) and above_props.get(direction, "none") != "none"
            )
            replacement[direction] = (
                ("tall" if arm_tall else "low")
                if connect and is_wall(name)
                else "none"
                if is_wall(name)
                else "true"
                if connect
                else "false"
            )
        if is_wall(name):
            connections = {d for d in DIRECTIONS if replacement[d] != "none"}
            straight = connections in ({"north", "south"}, {"east", "west"})
            above_post = bool(
                above
                and is_wall(above.state.name)
                and dict(above.state.properties).get("up") == "true"
            )
            replacement["up"] = "true" if not straight or tall or above_post else "false"
    elif name.endswith("_fence_gate"):
        facing = properties.get("facing", "north")
        sides = ("east", "west") if facing in {"north", "south"} else ("north", "south")
        replacement["in_wall"] = (
            "true"
            if any(
                (neighbor := cells.get(add(point, VECTORS[side]))) and is_wall(neighbor.state.name)
                for side in sides
            )
            else "false"
        )
    elif name.endswith("_stairs"):
        replacement["shape"] = stair_shape(point, cells, properties)
    return BlockState.make(name, replacement) if replacement != properties else None


def affected_neighbors(points: set[Point], cells: Mapping[Point, Cell] | None = None) -> set[Point]:
    # Stair corner blocking depends on a diagonal. Wall height also depends on the
    # cell above; the fixed radius avoids a whole-scene scan for every mouse click.
    return {
        candidate
        for point in points
        for dy in (-1, 0, 1)
        for dx in (-1, 0, 1)
        for dz in (-1, 0, 1)
        if dy == 0 or dx == dz == 0
        for candidate in [(point[0] + dx, point[1] + dy, point[2] + dz)]
        if cells is None or candidate in cells
    }


def chest_updates(
    points: set[Point],
    cells: Mapping[Point, Cell],
    excluded: set[Point] | None = None,
) -> dict[Point, BlockState]:
    """Pair ordinary/trapped chests without ever forming a triple chest.

    Keep valid existing pairs first, then pair remaining matching singles in a
    deterministic order. The connected component prevents deletion in a long row
    from leaving a mismatched partner just outside the immediate update radius.
    """
    excluded = excluded or set()
    component: set[Point] = set()
    queue = list(points)

    def eligible(point: Point) -> bool:
        cell = cells.get(point)
        return bool(
            cell
            and cell.state.name in {"minecraft:chest", "minecraft:trapped_chest"}
            and point not in excluded
        )

    def side(point: Point, clockwise: bool) -> Point:
        facing = dict(cells[point].state.properties).get("facing", "north")
        direction = DIRECTIONS[(DIRECTIONS.index(facing) + (1 if clockwise else -1)) % 4]
        return add(point, VECTORS[direction])

    def compatible(point: Point, other: Point) -> bool:
        return (
            eligible(other)
            and cells[other].state.name == cells[point].state.name
            and dict(cells[other].state.properties).get("facing")
            == dict(cells[point].state.properties).get("facing")
        )

    while queue:
        point = queue.pop()
        if point in component or not eligible(point):
            continue
        component.add(point)
        queue.extend(other for cw in (True, False) if compatible(point, other := side(point, cw)))
    types = {point: "single" for point in component}
    paired: set[Point] = set()
    for point in sorted(component):
        kind = dict(cells[point].state.properties).get("type", "single")
        if point in paired or kind not in {"left", "right"}:
            continue
        other = side(point, kind == "left")
        opposite = "right" if kind == "left" else "left"
        if (
            other in component
            and other not in paired
            and compatible(point, other)
            and dict(cells[other].state.properties).get("type") == opposite
        ):
            types[point], types[other] = kind, opposite
            paired.update((point, other))
    for point in sorted(component):
        if point in paired:
            continue
        for clockwise in (True, False):
            other = side(point, clockwise)
            if other in component and other not in paired and compatible(point, other):
                types[point], types[other] = ("left", "right") if clockwise else ("right", "left")
                paired.update((point, other))
                break
    changes: dict[Point, BlockState] = {}
    for point, kind in types.items():
        cell = cells[point]
        properties = dict(cell.state.properties)
        if properties.get("type") != kind:
            properties["type"] = kind
            changes[point] = BlockState.make(cell.state.name, properties)
    return changes
