"""Painting entities, dimensions and support cells for Java 1.20.1."""

from dataclasses import dataclass
from typing import Any

from .errors import WorkbenchError
from .models import Bounds, Cell, Point
from .placement import FACES

VARIANTS = {
    **dict.fromkeys(("kebab", "aztec", "alban", "aztec2", "bomb", "plant", "wasteland"), (1, 1)),
    **dict.fromkeys(("pool", "courbet", "sea", "sunset", "creebet"), (2, 1)),
    **dict.fromkeys(("wanderer", "graham"), (1, 2)),
    **dict.fromkeys(
        (
            "match",
            "bust",
            "stage",
            "void",
            "skull_and_roses",
            "wither",
            "earth",
            "wind",
            "water",
            "fire",
        ),
        (2, 2),
    ),
    "fighters": (4, 2),
    "skeleton": (4, 3),
    "donkey_kong": (4, 3),
    "pointer": (4, 4),
    "pigscene": (4, 4),
    "burning_skull": (4, 4),
}
HORIZONTAL = {"south": (1, 0, 0), "north": (-1, 0, 0), "east": (0, 0, -1), "west": (0, 0, 1)}


@dataclass(frozen=True)
class Painting:
    id: str
    anchor: Point
    facing: str
    variant: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "anchor": self.anchor,
            "facing": self.facing,
            "variant": self.variant,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Painting":
        return cls(value["id"], tuple(value["anchor"]), value["facing"], value["variant"])

    def positions(self) -> list[Point]:
        width, height = VARIANTS[self.variant]
        right = HORIZONTAL[self.facing]
        return [
            tuple(
                self.anchor[i]
                + right[i] * (x - (width - 1) // 2)
                + (y - (height - 1) // 2 if i == 1 else 0)
                for i in range(3)
            )  # type: ignore[misc]
            for y in range(height)
            for x in range(width)
        ]

    def center(self) -> list[float]:
        width, height = VARIANTS[self.variant]
        right, normal = HORIZONTAL[self.facing], FACES[self.facing]
        return [
            self.anchor[i]
            + 0.5
            + right[i] * (0.5 if width % 2 == 0 else 0)
            + (0.5 if i == 1 and height % 2 == 0 else 0)
            - normal[i] * (0.5 - 1 / 32)
            for i in range(3)
        ]


def fits(
    painting: Painting,
    cells: dict[Point, Cell],
    bounds: Bounds,
    others: list[Painting],
    protected: set[Point],
) -> bool:
    normal = FACES[painting.facing]
    points = painting.positions()
    occupied = {p for other in others for p in other.positions()}
    for point in points:
        support = tuple(point[i] - normal[i] for i in range(3))
        cell = cells.get(support)  # type: ignore[arg-type]
        front = cells.get(point)
        if (
            not bounds.contains(point)
            or point in occupied
            or point in protected
            or (front and not front.state.is_air)
            or cell is None
            or cell.state.is_air
        ):
            return False
    return True


def validate_variant(variant: str) -> str:
    short = variant.removeprefix("minecraft:")
    if short not in VARIANTS:
        raise WorkbenchError("INVALID_PAINTING", "画的图案不属于当前版本。")
    return short
