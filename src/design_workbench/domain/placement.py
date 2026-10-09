"""Deterministic attachment rules for the editor, independent of game/render APIs."""

from .errors import WorkbenchError
from .models import BlockState, Point

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
