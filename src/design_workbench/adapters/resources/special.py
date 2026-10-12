"""Offline geometry for blocks normally drawn by Minecraft entity renderers.

Entity UVs use the client texture layout. This does not simulate gameplay.
"""

from collections.abc import Callable
from math import degrees
from typing import Any

from design_workbench.domain.models import BlockState

from .geometry import DIRECTIONS, face_uv, quads, rotate

Transform = Callable[[list[float]], list[float]]
Y_ROTATION = {"south": 0, "west": 90, "north": 180, "east": 270}
HEAD_TEXTURES = {
    "skeleton_skull": ("skeleton/skeleton", (64, 32)),
    "wither_skeleton_skull": ("skeleton/wither_skeleton", (64, 32)),
    "zombie_head": ("zombie/zombie", (64, 64)),
    "player_head": ("player/wide/steve", (64, 64)),
    "creeper_head": ("creeper/creeper", (64, 32)),
    "piglin_head": ("piglin/piglin", (64, 64)),
    "dragon_head": ("enderdragon/dragon", (256, 256)),
}
CHEST_TEXTURES = {
    "chest": "normal",
    "trapped_chest": "trapped",
    "ender_chest": "ender",
    "copper_chest": "copper",
    "exposed_copper_chest": "copper_exposed",
    "weathered_copper_chest": "copper_weathered",
    "oxidized_copper_chest": "copper_oxidized",
}
DYE_COLORS = {
    "white": "#f9fffe",
    "orange": "#f9801d",
    "magenta": "#c74ebd",
    "light_blue": "#3ab3da",
    "yellow": "#fed83d",
    "lime": "#80c71f",
    "pink": "#f38baa",
    "gray": "#474f52",
    "light_gray": "#9d9d97",
    "cyan": "#169c9c",
    "purple": "#8932b8",
    "blue": "#3c44aa",
    "brown": "#835432",
    "green": "#5e7c16",
    "red": "#b02e26",
    "black": "#1d1d21",
}


def entity_box(
    low: list[float],
    size: list[float],
    offset: tuple[int, int],
    texture: str,
    transform: Transform,
    texture_size: tuple[int, int] | None = None,
) -> list[dict[str, Any]]:
    """Unfold a six-face cuboid using the entity model's texture dimensions."""
    w, h, d = size
    u, v = offset
    rects = {
        "down": [u + d, v, u + d + w, v + d],
        "up": [u + d + w, v + d, u + d + 2 * w, v],
        "west": [u, v + d, u + d, v + d + h],
        "north": [u + d, v + d, u + d + w, v + d + h],
        "east": [u + d + w, v + d, u + 2 * d + w, v + d + h],
        "south": [u + 2 * d + w, v + d, u + 2 * d + 2 * w, v + d + h],
    }
    width, height = texture_size or (64, 64 if "/bed/" in texture else 32)
    return [
        {
            "vertices": [round(v, 6) for p in points for v in transform(p)],
            "uv": [
                v
                for p in face_uv(
                    rects[direction],
                    width,
                    height,
                    turns=2 if direction not in {"up", "down"} else 0,
                )
                for v in p
            ],
            "texture": texture,
            "tint": False,
            "cull": None,
        }
        for direction, points in quads(low, [low[i] + size[i] for i in range(3)]).items()
    ]


def sign_geometry(state: BlockState) -> dict[str, Any]:
    name = state.name.split(":", 1)[1]
    props = dict(state.properties)
    hanging = name.endswith("hanging_sign")
    wall = "wall_" in name
    suffix = (
        ("_wall_hanging_sign" if wall else "_hanging_sign")
        if hanging
        else ("_wall_sign" if wall else "_sign")
    )
    wood = name.removesuffix(suffix)
    texture = "minecraft:entity/signs/" + ("hanging/" if hanging else "") + wood
    angle = -Y_ROTATION[props["facing"]] if wall else -int(props.get("rotation", "0")) * 22.5

    def transform(point: list[float]) -> list[float]:
        x, y, z = point
        if hanging:
            point = [x / 16, -y / 16 + 0.625, -z / 16]
        else:
            point = [
                x / 24,
                -y / 24 + 0.5 - (0.3125 if wall else 0),
                -z / 24 - (0.4375 if wall else 0),
            ]
        return [
            v + o for v, o in zip(rotate(point, "y", angle, [0, 0, 0]), [0.5, 0, 0.5], strict=True)
        ]

    if not hanging:
        faces = entity_box([-12, -14, -1], [24, 12, 2], (0, 0), texture, transform)
        if not wall:
            faces += entity_box([-1, -2, -1], [2, 14, 2], (0, 14), texture, transform)
    else:
        faces = entity_box([-7, 0, -1], [14, 10, 2], (0, 12), texture, transform)
        if wall:
            faces += entity_box([-8, -6, -2], [16, 2, 4], (0, 0), texture, transform)
        if not wall and props.get("attached") == "true":
            faces += entity_box([-6, -6, 0], [12, 6, 0], (14, 6), texture, transform)
        else:
            for x in (-5, 5):
                for angle_chain, uv_x in ((-45, 0), (45, 6)):

                    def chain(
                        point: list[float], x: int = x, angle_chain: int = angle_chain
                    ) -> list[float]:
                        point = rotate(point, "y", angle_chain, [0, 0, 0])
                        return transform([point[0] + x, point[1] - 6, point[2]])

                    faces += entity_box([-1.5, 0, 0], [3, 6, 0], (uv_x, 6), texture, chain)
    return {
        "faces": faces,
        "opaque_cube": False,
        "render_layer": "cutout",
        "text_planes": [faces[2]["vertices"], faces[3]["vertices"]],
    }


def bed_geometry(state: BlockState) -> dict[str, Any]:
    props = dict(state.properties)
    head = props.get("part") == "head"
    texture = "minecraft:entity/bed/" + state.name.split(":", 1)[1].removesuffix("_bed")

    def transform(point: list[float]) -> list[float]:
        point = rotate(point, "z", 180 + Y_ROTATION[props.get("facing", "south")], [8, 8, 8])
        point = rotate(point, "x", 90, [0, 0, 0])
        return [point[0] / 16, (point[1] + 9) / 16, point[2] / 16]

    faces = entity_box([0, 0, 0], [16, 16, 6], (0, 0 if head else 22), texture, transform)
    legs = (
        [([0, 6, 0], 90, 6), ([-16, 6, 0], 180, 18)]
        if head
        else [([0, 6, -16], 0, 0), ([-16, 6, -16], 270, 12)]
    )
    for low, angle, uv_y in legs:

        def leg(point: list[float], angle: int = angle) -> list[float]:
            point = rotate(point, "x", 90, [0, 0, 0])
            point = rotate(point, "z", angle, [0, 0, 0])
            return transform(point)

        faces += entity_box([float(v) for v in low], [3, 3, 3], (50, uv_y), texture, leg)
    return {"faces": faces, "opaque_cube": False, "render_layer": "opaque"}


def head_geometry(state: BlockState) -> dict[str, Any]:
    """Head dimensions, offsets and UVs from the Java skull entity models."""
    name = state.name.split(":", 1)[1]
    kind = name.replace("_wall_", "_")
    texture_path, texture_size = HEAD_TEXTURES[kind]
    texture = "minecraft:entity/" + texture_path
    props = dict(state.properties)
    wall = "_wall_" in name
    facing = props.get("facing", "north")
    vector = DIRECTIONS[facing] if wall else [0, 0, 0]
    # Skull rotation=0 faces north. Its model transform differs from a sign's.
    angle = (Y_ROTATION[facing] + 180) % 360 if wall else int(props.get("rotation", "0")) * 22.5

    def transform(point: list[float]) -> list[float]:
        point = rotate(point, "y", angle, [0, 0, 0])
        scale = 0.75 if kind == "dragon_head" else 1
        return [
            0.5 - vector[0] * 0.25 - point[0] * scale / 16,
            (0.25 if wall else 0)
            + (0.374375 if kind == "dragon_head" else 0)
            - point[1] * scale / 16,
            0.5 - vector[2] * 0.25 + point[2] * scale / 16,
        ]

    def box(
        low: list[float], size: list[float], offset: tuple[int, int], fn: Transform = transform
    ) -> list[dict[str, Any]]:
        return entity_box(low, size, offset, texture, fn, texture_size)

    if kind == "dragon_head":
        faces = box([-8, -8, -10], [16, 16, 16], (112, 30))
        faces += box([-6, -1, -24], [12, 5, 16], (176, 44))
        for x in (-5, 3):
            faces += box([x, -12, -4], [2, 4, 6], (0, 0))
            faces += box([x, -3, -22], [2, 2, 4], (112, 0))

        def jaw(point: list[float]) -> list[float]:
            point = rotate(point, "x", degrees(0.2), [0, 0, 0])
            return transform([point[0], point[1] + 4, point[2] - 8])

        faces += box([-6, 0, -16], [12, 4, 16], (176, 65), jaw)
    elif kind == "piglin_head":
        faces = box([-5, -8, -4], [10, 8, 8], (0, 0))
        faces += box([-2, -4, -5], [4, 4, 1], (31, 1))
        faces += box([2, -2, -5], [1, 2, 1], (2, 4))
        faces += box([-3, -2, -5], [1, 2, 1], (2, 0))
        for sign, uv_x in ((1, 51), (-1, 39)):

            def ear(point: list[float], sign: int = sign) -> list[float]:
                point = rotate(point, "z", -sign * degrees(0.7), [0, 0, 0])
                return transform([point[0] + sign * 4.5, point[1] - 6, point[2]])

            faces += box([0 if sign == 1 else -1, 0, -2], [1, 5, 4], (uv_x, 6), ear)
    else:
        faces = box([-4, -8, -4], [8, 8, 8], (0, 0))
        if kind == "player_head":

            def hat(point: list[float]) -> list[float]:
                return transform(
                    [point[0] * 1.0625, (point[1] + 4) * 1.0625 - 4, point[2] * 1.0625]
                )

            faces += box([-4, -8, -4], [8, 8, 8], (32, 0), hat)
    return {
        "faces": faces,
        "opaque_cube": False,
        "render_layer": "cutout",
        "preview_note": "默认 Steve 皮肤静态预览；自定义皮肤原数据保留"
        if kind == "player_head"
        else "头颅静态预览；朝向与墙面位置已解析",
    }


def chest_geometry(state: BlockState) -> dict[str, Any]:
    props = dict(state.properties)
    part = props.get("type", "single")
    name = state.name.split(":", 1)[1]
    texture = "minecraft:entity/chest/" + CHEST_TEXTURES[name.removeprefix("waxed_")]
    if part != "single":
        texture += "_" + part
    angle = -Y_ROTATION[props.get("facing", "north")]

    def transform(point: list[float]) -> list[float]:
        return rotate([v / 16 for v in point], "y", angle, [0.5, 0.5, 0.5])

    x, width, lock_x, lock_width = (
        (1, 14, 7, 2) if part == "single" else ((0, 15, 0, 1) if part == "left" else (1, 15, 15, 1))
    )
    faces = entity_box([x, 0, 1], [width, 10, 14], (0, 19), texture, transform, (64, 64))
    faces += entity_box([x, 9, 1], [width, 5, 14], (0, 0), texture, transform, (64, 64))
    faces += entity_box([lock_x, 7, 15], [lock_width, 4, 1], (0, 0), texture, transform, (64, 64))
    return {
        "faces": faces,
        "opaque_cube": False,
        "render_layer": "cutout",
        "preview_note": "箱子闭合静态预览；已解析方向与双箱形态",
    }


def banner_geometry(state: BlockState) -> dict[str, Any]:
    name = state.name.split(":", 1)[1]
    wall = "_wall_" in name
    color = name.removesuffix("_wall_banner" if wall else "_banner")
    props = dict(state.properties)
    angle = (
        -Y_ROTATION[props.get("facing", "north")]
        if wall
        else -int(props.get("rotation", "0")) * 22.5
    )
    texture = "minecraft:entity/banner_base"

    def transform(point: list[float]) -> list[float]:
        x, y, z = point
        point = [x / 24, -y / 24 - (0.3125 if wall else 0), -z / 24 - (0.4375 if wall else 0)]
        point = rotate(point, "y", angle, [0, 0, 0])
        return [point[0] + 0.5, point[1] + (-1 / 6 if wall else 0.5), point[2] + 0.5]

    faces = entity_box([-10, -32, -1], [20, 2, 2], (0, 42), texture, transform, (64, 64))
    if not wall:
        faces += entity_box([-1, -30, -1], [2, 42, 2], (44, 0), texture, transform, (64, 64))
    cloth = entity_box(
        [-10, -32, -2], [20, 40, 1], (0, 0), "minecraft:entity/banner/base", transform, (64, 64)
    )
    for face in cloth:
        face["color"] = DYE_COLORS[color]
    faces += cloth
    return {
        "faces": faces,
        "opaque_cube": False,
        "render_layer": "cutout",
        "preview_note": "旗帜基础色静态预览；自定义图案暂不显示，原数据保留",
    }


def shulker_geometry(state: BlockState) -> dict[str, Any]:
    color = state.name.split(":", 1)[1].removesuffix("_shulker_box")
    texture = "minecraft:entity/shulker/shulker" + ("" if color == "shulker_box" else "_" + color)
    facing = dict(state.properties).get("facing", "up")
    axis, angle = {
        "up": ("x", 0),
        "down": ("x", 180),
        "north": ("x", -90),
        "south": ("x", 90),
        "east": ("z", -90),
        "west": ("z", 90),
    }[facing]

    def transform(point: list[float]) -> list[float]:
        point = [point[0] / 16 + 0.5, -point[1] / 16, -point[2] / 16 + 0.5]
        return rotate(point, axis, angle, [0.5, 0.5, 0.5])

    faces = entity_box([-8, -8, -8], [16, 8, 16], (0, 28), texture, transform, (64, 64))
    faces += entity_box([-8, -16, -8], [16, 12, 16], (0, 0), texture, transform, (64, 64))
    return {
        "faces": faces,
        "opaque_cube": False,
        "render_layer": "cutout",
        "preview_note": "潜影盒闭合静态预览；朝向已解析",
    }


def conduit_geometry() -> dict[str, Any]:
    def transform(point: list[float]) -> list[float]:
        return [v / 16 + 0.5 for v in point]

    return {
        "faces": entity_box(
            [-3, -3, -3], [6, 6, 6], (0, 0), "minecraft:entity/conduit/base", transform, (32, 16)
        ),
        "opaque_cube": False,
        "render_layer": "opaque",
        "preview_note": "潮涌核心未激活外壳静态预览；不模拟激活和动画",
    }


def pot_geometry(state: BlockState) -> dict[str, Any]:
    angle = 180 - Y_ROTATION[dict(state.properties).get("facing", "north")]
    base = "minecraft:entity/decorated_pot/decorated_pot_base"

    def transform(point: list[float]) -> list[float]:
        return rotate([v / 16 for v in point], "y", angle, [0.5, 0, 0.5])

    faces = []
    # Four unpatterned body sides. The entity renderer uses a 14x16 crop.
    for direction, points in quads([1, 0, 1], [15, 16, 15]).items():
        if direction in {"up", "down"}:
            uv = face_uv([0, 13, 14, 27], 32, 32)
            texture = base
        else:
            uv = face_uv([1, 0, 15, 16])
            texture = "minecraft:entity/decorated_pot/decorated_pot_side"
        faces.append(
            {
                "vertices": [round(v, 6) for p in points for v in transform(p)],
                "uv": [v for p in uv for v in p],
                "texture": texture,
                "tint": False,
                "cull": None,
            }
        )

    def neck(point: list[float]) -> list[float]:
        return transform([point[0], 37 - point[1], 16 - point[2]])

    # Inflation adjusts geometry, not texture coordinates.
    def collar(point: list[float]) -> list[float]:
        return neck(
            [
                8 + (point[0] - 8) * 7.8 / 8,
                18.5 + (point[1] - 18.5) * 2.8 / 3,
                8 + (point[2] - 8) * 7.8 / 8,
            ]
        )

    def rim(point: list[float]) -> list[float]:
        return neck(
            [
                8 + (point[0] - 8) * 6.4 / 6,
                20.5 + (point[1] - 20.5) * 1.4,
                8 + (point[2] - 8) * 6.4 / 6,
            ]
        )

    faces += entity_box([4, 17, 4], [8, 3, 8], (0, 0), base, collar, (32, 32))
    faces += entity_box([5, 20, 5], [6, 1, 6], (0, 5), base, rim, (32, 32))
    return {
        "faces": faces,
        "opaque_cube": False,
        "render_layer": "opaque",
        "preview_note": "饰纹陶罐基础静态预览；陶片图案暂不显示，原数据保留",
    }


def fluid_height(state: BlockState) -> float:
    level = int(dict(state.properties).get("level", "0"))
    return (8 - (level if level < 8 else 0)) / 9


def fluid_geometry(
    state: BlockState, corners: list[float] | None = None, hidden: set[str] | None = None
) -> dict[str, Any]:
    water = state.name == "minecraft:water"
    heights = corners or [fluid_height(state)] * 4  # NW, NE, SE, SW
    texture = "minecraft:block/" + ("water" if water else "lava")
    faces = []
    for direction, points in quads([0, 0, 0], [1, 1, 1]).items():
        if direction in (hidden or set()):
            continue
        for p in points:
            if p[1] == 1:
                p[1] = heights[{(0, 0): 0, (1, 0): 1, (1, 1): 2, (0, 1): 3}[(int(p[0]), int(p[2]))]]
        flowing = direction not in {"up", "down"} or dict(state.properties).get("level", "0") != "0"
        uvs = face_uv([0, 0, 8 if flowing else 16, 8 if flowing else 16])
        faces.append(
            {
                "vertices": [v for p in points for v in p],
                "uv": [v for p in uvs for v in p],
                "texture": texture + ("_flow" if flowing else "_still"),
                "tint": False,
                "color": "#3f76e4" if water else "#ffffff",
                "cull": DIRECTIONS[direction],
            }
        )
    return {
        "faces": faces,
        "opaque_cube": False,
        "render_layer": "translucent" if water else "emissive",
    }


def special_geometry(state: BlockState) -> dict[str, Any] | None:
    if not state.name.startswith("minecraft:"):
        return None
    if state.name in {"minecraft:water", "minecraft:lava"}:
        return fluid_geometry(state)
    if state.name == "minecraft:bubble_column":
        geometry = fluid_geometry(BlockState.make("water"), [1.0] * 4)
        geometry["preview_note"] = "气泡柱水体静态预览；不显示气泡粒子"
        return geometry
    if state.name.endswith("_sign"):
        return sign_geometry(state)
    if state.name.endswith("_bed"):
        return bed_geometry(state)
    name = state.name.split(":", 1)[1]
    if name.replace("_wall_", "_") in HEAD_TEXTURES:
        return head_geometry(state)
    if name.removeprefix("waxed_") in CHEST_TEXTURES:
        return chest_geometry(state)
    if name.endswith("_banner"):
        return banner_geometry(state)
    if name == "shulker_box" or name.endswith("_shulker_box"):
        return shulker_geometry(state)
    if name == "conduit":
        return conduit_geometry()
    if name == "decorated_pot":
        return pot_geometry(state)
    return None
