"""Read the versioned attachment coordinates of known painting entities."""

from collections.abc import Mapping
from operator import index
from typing import Any

from design_workbench.domain.models import Point
from design_workbench.domain.paintings import VARIANTS, Painting


def read_painting_entity(
    entry: Mapping[str, Any], origin: Point, identifier: str
) -> Painting | None:
    if str(entry.get("id", "")) != "minecraft:painting":
        return None
    variant = str(entry.get("variant", "")).removeprefix("minecraft:")
    if variant not in VARIANTS:
        return None
    try:
        # Java 1.21.5 replaced TileX/Y/Z with BlockPos.CODEC (an int stream
        # of exactly three coordinates). Prefer it if both formats exist.
        if "block_pos" in entry:
            position = entry["block_pos"]
            if len(position) != 3:
                return None
            local = [index(value) for value in position]
        elif all("Tile" + axis in entry for axis in "XYZ"):
            local = [index(entry["Tile" + axis]) for axis in "XYZ"]
        else:
            return None
        facing = ("south", "west", "north", "east")[index(entry.get("facing", 0)) % 4]
    except (TypeError, ValueError):
        return None
    anchor: Point = (origin[0] + local[0], origin[1] + local[1], origin[2] + local[2])
    return Painting(identifier, anchor, facing, variant)
