from .editing import VECTORS, partner
from .models import BlockState, Cell, Point, Scene


def add(point: Point, vector: Point) -> Point:
    return point[0] + vector[0], point[1] + vector[1], point[2] + vector[2]


def inspect_consistency(scene: Scene) -> dict[str, object]:
    issues: list[dict[str, object]] = []
    proposals: list[dict[str, object]] = []
    cells = scene.cells
    for point, cell in cells.items():
        state = cell.state
        properties = dict(state.properties)
        other_position = partner(point, cell)
        if other_position is not None:
            other = cells.get(other_position)
            if other is None or other.state.name != state.name:
                issues.append(
                    {
                        "position": point,
                        "code": "MISSING_PARTNER",
                        "message": "门、床或高植物缺少对应部件。",
                    }
                )
            else:
                counterpart = dict(other.state.properties)
                expected_opposite = (
                    ("half", {"lower": "upper", "upper": "lower"})
                    if "half" in properties
                    else ("part", {"foot": "head", "head": "foot"})
                )
                key, values = expected_opposite
                if counterpart.get(key) != values.get(properties.get(key, "")) or any(
                    properties.get(k) != counterpart.get(k)
                    for k in ("facing", "open", "hinge")
                    if k in properties
                ):
                    issues.append(
                        {
                            "position": point,
                            "code": "PARTNER_STATE",
                            "message": "多格部件的状态不一致。",
                        }
                    )
        replacement = dict(properties)
        supported = False
        if (
            state.name.endswith(("_fence", "_pane"))
            or state.name == "minecraft:iron_bars"
            or state.name.endswith("_wall")
        ):
            supported = True
            for direction, vector in VECTORS.items():
                neighbour = cells.get(add(point, vector))
                connect = neighbour is not None and (
                    neighbour.state.name == state.name or is_simple_solid(neighbour)
                )
                if state.name.endswith("_wall"):
                    replacement[direction] = "low" if connect else "none"
                else:
                    replacement[direction] = "true" if connect else "false"
            if state.name.endswith("_wall"):
                connections = {d for d in VECTORS if replacement[d] != "none"}
                replacement["up"] = (
                    "false" if connections in ({"north", "south"}, {"east", "west"}) else "true"
                )
        elif state.name.endswith("_stairs"):
            supported = True
            facing = properties.get("facing", "north")
            order = ("north", "east", "south", "west")
            shape = "straight"
            vector = VECTORS[facing]
            front, back = (
                cells.get(add(point, vector)),
                cells.get(add(point, (-vector[0], -vector[1], -vector[2]))),
            )
            for neighbour, prefix in ((front, "outer"), (back, "inner")):
                if neighbour and neighbour.state.name.endswith("_stairs"):
                    neighbour_props = dict(neighbour.state.properties)
                    other_facing = neighbour_props.get("facing", facing)
                    if (
                        neighbour_props.get("half") == properties.get("half")
                        and (order.index(other_facing) - order.index(facing)) % 2
                    ):
                        blocking_direction = (
                            order[(order.index(other_facing) + 2) % 4]
                            if prefix == "outer"
                            else other_facing
                        )
                        blocking = cells.get(add(point, VECTORS[blocking_direction]))
                        blocking_props = dict(blocking.state.properties) if blocking else {}
                        if (
                            not blocking
                            or not blocking.state.name.endswith("_stairs")
                            or blocking_props.get("facing") != facing
                            or blocking_props.get("half") != properties.get("half")
                        ):
                            left = other_facing == order[(order.index(facing) - 1) % 4]
                            shape = prefix + ("_left" if left else "_right")
                            break
            replacement["shape"] = shape
        if supported and replacement != properties:
            proposals.append(
                {
                    "position": point,
                    "state": BlockState.make(state.name, replacement).as_dict(),
                    "group": cell.group,
                }
            )
    return {
        "revision": scene.revision,
        "issues": issues,
        "proposals": proposals,
        "rules": "doors/beds/tall plants; stairs; basic fence/pane/wall neighbours",
        "limitations": [
            "不模拟游戏物理",
            "连接检查仅覆盖相同连接块与普通完整实心块；墙高形状及特殊邻接需游戏核对",
        ],
        "requires_confirmation": True,
    }


def is_simple_solid(cell: Cell) -> bool:
    name = cell.state.name.split(":", 1)[-1]
    return name in {
        "stone",
        "cobblestone",
        "bricks",
        "dirt",
        "grass_block",
        "sandstone",
        "quartz_block",
        "smooth_quartz",
        "stone_bricks",
    } or name.endswith(("_planks", "_log", "_wood", "_concrete", "_wool"))
