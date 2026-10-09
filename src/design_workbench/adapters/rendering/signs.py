"""Read-only, bounded sign text projection from preserved source NBT."""

import json
from functools import lru_cache
from typing import Any

from design_workbench.domain.models import Point

from ..formats.litematic import Litematic, region_bounds, vector


def plain_text(value: Any, depth: int = 0) -> str:
    if depth > 16:
        return ""
    if isinstance(value, str):
        return value[:512]
    if isinstance(value, list):
        return "".join(plain_text(item, depth + 1) for item in value[:32])[:512]
    if isinstance(value, dict):
        return (
            str(value.get("text", value.get("translate", "")))
            + plain_text(value.get("extra", []), depth + 1)
        )[:512]
    return ""


def message(value: Any) -> str:
    try:
        return plain_text(json.loads(str(value)))
    except (ValueError, RecursionError):
        return str(value)[:512]


@lru_cache(maxsize=2)
def sign_texts(payload: bytes) -> dict[Point, list[dict[str, Any]]]:
    root = Litematic.parse(payload)
    result = {}
    for region in root["Regions"].values():
        origin = region_bounds(region).low
        for entry in region.get("TileEntities", []):
            if str(entry.get("id", "")) not in {"minecraft:sign", "minecraft:hanging_sign"}:
                continue
            relative = vector(entry)
            point: Point = tuple(origin[i] + relative[i] for i in range(3))  # type: ignore[assignment]
            sides = []
            for side in ("front_text", "back_text"):
                text = entry.get(side, {})
                lines = text.get(
                    "messages",
                    [
                        entry.get(f"Text{i}", '""') if side == "front_text" else '""'
                        for i in range(1, 5)
                    ],
                )
                sides.append(
                    {
                        "lines": [message(item) for item in lines[:4]],
                        "color": str(text.get("color", "black")),
                        "glowing": bool(text.get("has_glowing_text", False)),
                    }
                )
            result[point] = sides
    return result
