from __future__ import annotations

import math
from collections.abc import Mapping
from typing import TYPE_CHECKING

from .errors import WorkbenchError
from .models import BlockState, Cell, Point
from .neighbors import full_face

if TYPE_CHECKING:
    from .editing import Registry

_HORIZONTAL: dict[str, Point] = {
    "north": (0, 0, -1),
    "east": (1, 0, 0),
    "south": (0, 0, 1),
    "west": (-1, 0, 0),
}
_OPPOSITE = {"north": "south", "east": "west", "south": "north", "west": "east"}
_TALL_PLANTS = {
    "sunflower",
    "lilac",
    "rose_bush",
    "peony",
    "tall_grass",
    "large_fern",
    "pitcher_plant",
    "tall_seagrass",
    "small_dripleaf",
}
_TORCHES = {
    "torch": ("torch", "wall_torch"),
    "copper_torch": ("copper_torch", "copper_wall_torch"),
    "copper_wall_torch": ("copper_torch", "copper_wall_torch"),
    "wall_torch": ("torch", "wall_torch"),
    "soul_torch": ("soul_torch", "soul_wall_torch"),
    "soul_wall_torch": ("soul_torch", "soul_wall_torch"),
    "redstone_torch": ("redstone_torch", "redstone_wall_torch"),
    "redstone_wall_torch": ("redstone_torch", "redstone_wall_torch"),
}


def _offset(point: Point, vector: Point, amount: int = 1) -> Point:
    return (
        point[0] + vector[0] * amount,
        point[1] + vector[1] * amount,
        point[2] + vector[2] * amount,
    )


def _opposite_vector(vector: Point) -> Point:
    return -vector[0], -vector[1], -vector[2]


def _short(state: BlockState) -> str:
    return state.name.split(":", 1)[1]


def _support(
    cells: Mapping[Point, Cell],
    point: Point,
    face: Point,
    registry: object | None,
    center: bool = False,
) -> bool:
    """Check the actual supporting shape, including the virtual ground.

    Small attachments can also sit on the central post of fences and walls.
    No survival physics or automatic support removal is applied to the scene.
    """
    cell = cells.get(point)
    if cell is None or cell.state.is_air:
        return point[1] == -1 and face == (0, 1, 0)
    name = _short(cell.state)
    if (
        center
        and face[1]
        and (name.endswith(("_fence", "_fence_gate", "_wall")) or name == "iron_bars")
    ):
        return True
    direction = next(
        (key for key, vector in _HORIZONTAL.items() if vector == face),
        "up" if face[1] > 0 else "down",
    )
    return full_face(cell, direction, registry, connection_exceptions=False)


def _attachment_family(name: str) -> tuple[str, str, str] | None:
    if name == "piston_head":
        return None
    if name in _TORCHES:
        floor, wall = _TORCHES[name]
        return "torch", floor, wall
    for kind, suffix, wall_suffix in (
        ("hanging_sign", "_hanging_sign", "_wall_hanging_sign"),
        ("sign", "_sign", "_wall_sign"),
        ("banner", "_banner", "_wall_banner"),
        ("head", "_skull", "_wall_skull"),
        ("head", "_head", "_wall_head"),
        ("coral_fan", "_coral_fan", "_coral_wall_fan"),
    ):
        if name.endswith(wall_suffix):
            prefix = name.removesuffix(wall_suffix)
        elif name.endswith(suffix):
            prefix = name.removesuffix(suffix)
        else:
            continue
        return kind, prefix + suffix, prefix + wall_suffix
    return None


def _is_lantern(name: str) -> bool:
    return name in {"lantern", "soul_lantern"} or name.endswith("copper_lantern")


def _support_requirements(point: Point, state: BlockState) -> list[tuple[Point, Point, bool]]:
    name = _short(state)
    properties = dict(state.properties)
    family = _attachment_family(name)
    if family is not None:
        kind, _, wall_name = family
        direction = (
            _HORIZONTAL.get(properties.get("facing", ""))
            if name == wall_name
            else (0, -1, 0)
            if kind == "hanging_sign"
            else (0, 1, 0)
        )
        return [(_offset(point, direction, -1), direction, name != wall_name)] if direction else []
    if (
        name in {"ladder", "tripwire_hook"}
        or name.endswith("_button")
        or name in {"lever", "grindstone", "bell"}
    ):
        face = properties.get("face", properties.get("attachment", "wall"))
        direction = (
            (0, 1, 0)
            if face == "floor"
            else (0, -1, 0)
            if face == "ceiling"
            else _HORIZONTAL.get(properties.get("facing", ""))
        )
        if direction is None:
            return []
        requirements = [
            (_offset(point, direction, -1), direction, name == "bell" and bool(direction[1]))
        ]
        if face == "double_wall":
            requirements.append((_offset(point, direction), _opposite_vector(direction), False))
        return requirements
    if _is_lantern(name):
        direction = (0, -1, 0) if properties.get("hanging") == "true" else (0, 1, 0)
        return [(_offset(point, direction, -1), direction, True)]
    if name in {"vine", "glow_lichen", "sculk_vein"}:
        faces = {**_HORIZONTAL, "up": (0, 1, 0), "down": (0, -1, 0)}
        return [
            (_offset(point, vector), _opposite_vector(vector), False)
            for key, vector in faces.items()
            if properties.get(key) == "true"
        ]
    if (
        (name.endswith("_door") and not name.endswith("_trapdoor"))
        or name in _TALL_PLANTS
        or (name == "pitcher_crop" and int(properties.get("age", "0")) >= 3)
    ):
        lower = _offset(point, (0, -1, 0)) if properties.get("half") == "upper" else point
        return [(_offset(lower, (0, -1, 0)), (0, 1, 0), False)]
    if name.endswith("_bed"):
        return [(_offset(point, (0, -1, 0)), (0, 1, 0), False)]
    return []


def missing_supports(
    cells: Mapping[Point, Cell], point: Point, state: BlockState, registry: object | None = None
) -> list[Point]:
    """Return missing/unsuitable supports without changing a floating design."""
    return [
        support_point
        for support_point, face, center in _support_requirements(point, state)
        if not _support(cells, support_point, face, registry, center)
    ]


def plan_placement(
    cells: Mapping[Point, Cell],
    state: BlockState,
    hit: Point,
    normal: Point,
    location: tuple[float, float, float],
    facing: str,
    automatic: bool,
    registry: Registry,
) -> list[tuple[Point, BlockState]]:
    """Plan one click without mutating the scene; all parts commit atomically.

    ``location`` is relative to the hit cell, and ``normal`` points out of the
    clicked face. Raw ``set`` remains the API for exact, unsupported structures.
    """
    if normal not in (*_HORIZONTAL.values(), (0, 1, 0), (0, -1, 0)):
        raise WorkbenchError("INVALID_PLACEMENT", "点击面必须是方块的六个方向之一。", "normal")
    if facing not in _HORIZONTAL:
        raise WorkbenchError("INVALID_PLACEMENT", "放置视角必须是水平方向。", "facing")
    if len(location) != 3 or any(not math.isfinite(value) for value in location):
        raise WorkbenchError("INVALID_PLACEMENT", "点击位置必须是三个有限数值。", "location")
    location = tuple(max(0.0, min(1.0, value)) for value in location)  # type: ignore[assignment]
    state = registry.normalize(state)
    if state.is_air:
        raise WorkbenchError("INVALID_PLACEMENT", "请用删除工具移除方块。", "state")
    namespace, name = state.name.split(":", 1)
    properties = dict(state.properties)
    point = _offset(hit, normal)
    wall_facing = next((key for key, vector in _HORIZONTAL.items() if vector == normal), None)
    tall_plant = name in _TALL_PLANTS or (
        name == "pitcher_crop" and int(properties.get("age", "0")) >= 3
    )

    def support(support_point: Point, face: Point, center: bool = False) -> bool:
        return _support(cells, support_point, face, registry, center)

    def require_support(support_point: Point, face: Point, center: bool = False) -> None:
        if not support(support_point, face, center):
            raise WorkbenchError("MISSING_SUPPORT", "该放置方向缺少可附着的支撑面。", "hit")

    def change_name(new_name: str) -> None:
        nonlocal name, properties
        defaults = dict(registry.normalize(BlockState.make(namespace + ":" + new_name)).properties)
        defaults.update({key: value for key, value in properties.items() if key in defaults})
        name, properties = new_name, defaults

    if name.endswith("_slab") and automatic:
        clicked = cells.get(hit)
        if clicked is not None and clicked.state.name == state.name:
            existing_type = dict(clicked.state.properties).get("type", "bottom")
            free_half = (
                existing_type == "bottom"
                and (normal[1] == 1 or (wall_facing is not None and location[1] >= 0.5))
            ) or (
                existing_type == "top"
                and (normal[1] == -1 or (wall_facing is not None and location[1] < 0.5))
            )
            if free_half:
                merged = dict(clicked.state.properties)
                merged.update(type="double", waterlogged="false")
                return [(hit, registry.normalize(BlockState.make(state.name, merged)))]
        properties["type"] = (
            "top" if normal[1] < 0 or (wall_facing is not None and location[1] > 0.5) else "bottom"
        )
    elif name.endswith("_stairs") and automatic:
        properties.update(
            facing=facing,
            half="top"
            if normal[1] < 0 or (wall_facing is not None and location[1] > 0.5)
            else "bottom",
            shape="straight",
        )
    elif automatic and (family := _attachment_family(name)) is not None:
        kind, floor_name, wall_name = family
        if wall_facing is not None:
            change_name(wall_name)
            properties["facing"] = wall_facing
        elif kind == "hanging_sign" and normal[1] < 0:
            change_name(floor_name)
            properties.update(
                rotation={"north": "0", "east": "4", "south": "8", "west": "12"}[facing],
                attached="false",
            )
        elif kind != "hanging_sign" and normal[1] > 0:
            change_name(floor_name)
            if "rotation" in properties:
                # Skull models face north at rotation zero; standing signs
                # and banners face south, so their rotations differ by 180°.
                rotations = (
                    {"north": "8", "east": "12", "south": "0", "west": "4"}
                    if kind == "head"
                    else {"north": "0", "east": "4", "south": "8", "west": "12"}
                )
                properties["rotation"] = rotations[facing]
        else:
            raise WorkbenchError("INVALID_PLACEMENT", "该物品不能附着在所点击的面上。", "normal")
    elif name == "ladder" and automatic:
        choices = ([wall_facing] if wall_facing is not None else []) + [
            _OPPOSITE[facing],
            *_HORIZONTAL,
        ]
        support_facing = next(
            (
                direction
                for direction in choices
                if support(_offset(point, _HORIZONTAL[direction], -1), _HORIZONTAL[direction])
            ),
            None,
        )
        if support_facing is None:
            raise WorkbenchError("MISSING_SUPPORT", "梯子旁边需要可附着的墙面。", "hit")
        properties["facing"] = support_facing
    elif (name.endswith("_button") or name in {"lever", "grindstone"}) and automatic:
        properties.update(
            face="floor" if normal[1] > 0 else "ceiling" if normal[1] < 0 else "wall",
            facing=wall_facing or facing,
        )
    elif name == "bell" and automatic:
        attachment = "floor" if normal[1] > 0 else "ceiling" if normal[1] < 0 else "single_wall"
        if wall_facing is not None and support(_offset(point, normal), _opposite_vector(normal)):
            attachment = "double_wall"
        properties.update(attachment=attachment, facing=wall_facing or facing)
    elif name == "tripwire_hook" and automatic:
        if wall_facing is None:
            raise WorkbenchError("INVALID_PLACEMENT", "绊线钩需要放在墙面上。", "normal")
        properties["facing"] = wall_facing
    elif name in {"vine", "glow_lichen", "sculk_vein"} and automatic:
        attached_face = _OPPOSITE[wall_facing] if wall_facing else "down" if normal[1] > 0 else "up"
        if attached_face not in properties:
            raise WorkbenchError("INVALID_PLACEMENT", "该物品不能附着在所点击的面上。", "normal")
        for key in (*_HORIZONTAL, "up", "down"):
            if key in properties:
                properties[key] = "true" if key == attached_face else "false"
    elif name == "hopper" and automatic:
        properties["facing"] = _OPPOSITE[wall_facing] if wall_facing else "down"
    elif _is_lantern(name) and automatic:
        if not normal[1]:
            raise WorkbenchError("INVALID_PLACEMENT", "灯笼需要放在顶面或悬挂在底面。", "normal")
        properties["hanging"] = "true" if normal[1] < 0 else "false"
    elif name.endswith("_trapdoor") and automatic:
        properties.update(
            facing=wall_facing or _OPPOSITE[facing],
            half="top"
            if normal[1] < 0 or (wall_facing is not None and location[1] > 0.5)
            else "bottom",
        )
    elif automatic:
        if "axis" in properties:
            properties["axis"] = "x" if normal[0] else "z" if normal[2] else "y"
            if name == "nether_portal":
                properties["axis"] = "x" if facing in {"north", "south"} else "z"
        if name in {
            "end_rod",
            "lightning_rod",
            "amethyst_cluster",
            "large_amethyst_bud",
            "medium_amethyst_bud",
            "small_amethyst_bud",
        }:
            properties["facing"] = wall_facing or ("up" if normal[1] > 0 else "down")
        elif "facing" in properties:
            properties["facing"] = facing if name.endswith(("_door", "_bed")) else _OPPOSITE[facing]
        elif "rotation" in properties:
            properties["rotation"] = {"north": "0", "east": "4", "south": "8", "west": "12"}[facing]

    if automatic and ((name.endswith("_door") and not name.endswith("_trapdoor")) or tall_plant):
        properties["half"] = "lower"
    if automatic and name.endswith("_bed"):
        properties["part"] = "foot"
    resolved = registry.normalize(BlockState.make(namespace + ":" + name, properties))
    properties = dict(resolved.properties)
    if name in {"vine", "glow_lichen", "sculk_vein"} and not any(
        properties.get(key) == "true" for key in (*_HORIZONTAL, "up", "down")
    ):
        raise WorkbenchError("MISSING_SUPPORT", "附着方块至少需要一个支撑面。", "state")
    for support_point, support_face, center in _support_requirements(point, resolved):
        require_support(support_point, support_face, center)

    placements = [(point, resolved)]
    if (name.endswith("_door") and not name.endswith("_trapdoor")) or tall_plant:
        lower = _offset(point, (0, -1, 0)) if properties.get("half") == "upper" else point
        upper = _offset(lower, (0, 1, 0))
        require_support(_offset(lower, (0, -1, 0)), (0, 1, 0))
        if name.endswith("_door") and automatic:
            direction = _HORIZONTAL[properties["facing"]]
            left = (direction[2], 0, -direction[0])
            right = (-direction[2], 0, direction[0])
            left_cell, right_cell = (
                cells.get(_offset(lower, left)),
                cells.get(_offset(lower, right)),
            )
            left_door = (
                left_cell is not None
                and left_cell.state.name == resolved.name
                and dict(left_cell.state.properties).get("facing") == properties["facing"]
            )
            right_door = (
                right_cell is not None
                and right_cell.state.name == resolved.name
                and dict(right_cell.state.properties).get("facing") == properties["facing"]
            )
            left_support = sum(support(_offset(level, left), right) for level in (lower, upper))
            right_support = sum(support(_offset(level, right), left) for level in (lower, upper))
            # A neighbouring door gets the opposite hinge; otherwise the
            # more obstructed side or the clicked edge supplies the hinge.
            if left_door != right_door:
                neighbor = left_cell if left_door else right_cell
                assert neighbor is not None
                properties["hinge"] = (
                    "right" if dict(neighbor.state.properties).get("hinge") == "left" else "left"
                )
            elif left_support != right_support:
                properties["hinge"] = "left" if left_support > right_support else "right"
            else:
                properties["hinge"] = (
                    "left"
                    if (location[0] - 0.5) * left[0] + (location[2] - 0.5) * left[2] >= 0
                    else "right"
                )
        placements = [
            (
                lower,
                registry.normalize(BlockState.make(resolved.name, {**properties, "half": "lower"})),
            ),
            (
                upper,
                registry.normalize(BlockState.make(resolved.name, {**properties, "half": "upper"})),
            ),
        ]
    elif name.endswith("_bed"):
        direction = _HORIZONTAL[properties["facing"]]
        foot = _offset(point, direction, -1) if properties["part"] == "head" else point
        head = _offset(foot, direction)
        for part_point in (foot, head):
            require_support(_offset(part_point, (0, -1, 0)), (0, 1, 0))
        placements = [
            (
                foot,
                registry.normalize(BlockState.make(resolved.name, {**properties, "part": "foot"})),
            ),
            (
                head,
                registry.normalize(BlockState.make(resolved.name, {**properties, "part": "head"})),
            ),
        ]

    for target, placed in placements:
        existing = cells.get(target)
        if existing is not None and not existing.state.is_air:
            if automatic and placed.name.endswith("_slab") and existing.state.name == placed.name:
                current_type = dict(existing.state.properties).get("type")
                desired_type = dict(placed.properties).get("type")
                if {current_type, desired_type} == {"bottom", "top"}:
                    merged_properties = dict(existing.state.properties)
                    merged_properties.update(type="double", waterlogged="false")
                    return [
                        (
                            target,
                            registry.normalize(BlockState.make(placed.name, merged_properties)),
                        )
                    ]
            raise WorkbenchError("EDIT_COLLISION", "放置位置已被占用，请先移除原有方块。", "hit")
    return placements


FACES: dict[str, Point] = {
    "north": (0, 0, -1),
    "south": (0, 0, 1),
    "west": (-1, 0, 0),
    "east": (1, 0, 0),
    "up": (0, 1, 0),
    "down": (0, -1, 0),
}
OPPOSITE = {"north": "south", "south": "north", "west": "east", "east": "west"}
ROTATION = {"south": "0", "west": "4", "north": "8", "east": "12"}


def needs_support(state: BlockState) -> bool:
    name = state.name.split(":", 1)[1]
    return name.endswith(("_sign", "_button", "_trapdoor")) or name in {
        "torch",
        "wall_torch",
        "soul_torch",
        "soul_wall_torch",
        "redstone_torch",
        "redstone_wall_torch",
        "ladder",
        "lever",
        "grindstone",
        "lantern",
        "soul_lantern",
        "end_rod",
        "lightning_rod",
        "amethyst_cluster",
        "large_amethyst_bud",
        "medium_amethyst_bud",
        "small_amethyst_bud",
        "vine",
    }


def snap_state(
    state: BlockState, face: str, heading: str = "north", height: float = 0.5
) -> BlockState:
    properties = dict(state.properties)
    short = state.name.split(":", 1)[1]
    horizontal = face in OPPOSITE
    facing = face if horizontal else OPPOSITE[heading]
    name = short
    torch = {
        "torch": "wall_torch",
        "soul_torch": "soul_wall_torch",
        "redstone_torch": "redstone_wall_torch",
    }
    if short in torch or short in torch.values():
        base = next((base for base, wall in torch.items() if short == wall), short)
        if face == "down":
            raise WorkbenchError("UNSUPPORTED_ATTACHMENT", "火把不能吸附在方块底面。")
        name = torch[base] if horizontal else base
        properties.pop("facing", None)
        if horizontal:
            properties["facing"] = face
    elif short.endswith("_hanging_sign"):
        wood = short.removesuffix("_wall_hanging_sign").removesuffix("_hanging_sign")
        if face == "up":
            raise WorkbenchError("UNSUPPORTED_ATTACHMENT", "悬挂告示牌需要侧面或底面支撑。")
        name = wood + ("_wall_hanging_sign" if horizontal else "_hanging_sign")
        for key in ("facing", "rotation", "attached"):
            properties.pop(key, None)
        if horizontal:
            properties["facing"] = face
        else:
            properties.update(rotation=ROTATION[OPPOSITE[heading]], attached="true")
    elif short.endswith("_sign"):
        wood = short.removesuffix("_wall_sign").removesuffix("_sign")
        if face == "down":
            raise WorkbenchError(
                "UNSUPPORTED_ATTACHMENT", "普通告示牌不能贴在底面，请选悬挂告示牌。"
            )
        name = wood + ("_wall_sign" if horizontal else "_sign")
        for key in ("facing", "rotation"):
            properties.pop(key, None)
        properties.update(
            {"facing": face} if horizontal else {"rotation": ROTATION[OPPOSITE[heading]]}
        )
    elif short == "ladder":
        if not horizontal:
            raise WorkbenchError("UNSUPPORTED_ATTACHMENT", "这个材料需要竖直支撑面。")
        properties["facing"] = face
    elif short == "lever" or short.endswith("_button") or short == "grindstone":
        properties.update(
            face="wall" if horizontal else "ceiling" if face == "down" else "floor", facing=facing
        )
    elif short in {"lantern", "soul_lantern"}:
        if horizontal:
            raise WorkbenchError("UNSUPPORTED_ATTACHMENT", "灯笼需要顶面或底面支撑。")
        properties["hanging"] = "true" if face == "down" else "false"
    elif short.endswith("_trapdoor"):
        properties.update(
            facing=facing, half="top" if face == "down" or horizontal and height > 0.5 else "bottom"
        )
    elif short in {
        "end_rod",
        "lightning_rod",
        "amethyst_cluster",
        "large_amethyst_bud",
        "medium_amethyst_bud",
        "small_amethyst_bud",
    }:
        properties["facing"] = face
    elif short == "vine":
        if horizontal:
            properties.update({key: "false" for key in (*OPPOSITE, "up")})
            properties[OPPOSITE[face]] = "true"
        elif face == "down":
            properties["up"] = "true"
        else:
            raise WorkbenchError("UNSUPPORTED_ATTACHMENT", "藤蔓需要侧面或底面支撑。")
    return BlockState.make("minecraft:" + name, properties)
