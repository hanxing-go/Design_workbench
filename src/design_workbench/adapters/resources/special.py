"""Offline geometry for fluids, signs and beds in Java 1.20.1.

Entity UVs use the client texture layout. This does not simulate gameplay.
"""

from collections.abc import Callable
from typing import Any

from design_workbench.domain.models import BlockState

from .geometry import DIRECTIONS, face_uv, quads, rotate

Transform = Callable[[list[float]], list[float]]
Y_ROTATION = {"south": 0, "west": 90, "north": 180, "east": 270}


def entity_box(
    low: list[float], size: list[float], offset: tuple[int, int], texture: str, transform: Transform
) -> list[dict[str, Any]]:
    """Unfold a six-face entity cuboid onto its 64px texture sheet."""
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
    height = 64 if "/bed/" in texture else 32
    return [
        {
            "vertices": [round(v, 6) for p in points for v in transform(p)],
            "uv": [
                v
                for p in face_uv(
                    rects[direction], 64, height, turns=2 if direction not in {"up", "down"} else 0
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
    if state.name.endswith("_sign"):
        return sign_geometry(state)
    if state.name.endswith("_bed"):
        return bed_geometry(state)
    return None
