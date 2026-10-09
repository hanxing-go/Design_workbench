from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field

from .errors import WorkbenchError

type Point = tuple[int, int, int]
CHUNK_SIZE = 16


@dataclass(frozen=True, slots=True)
class Bounds:
    low: Point
    high: Point

    def __post_init__(self) -> None:
        if any(a > b for a, b in zip(self.low, self.high, strict=True)):
            raise WorkbenchError("INVALID_BOUNDS", "选区最小坐标不能超过最大坐标。", "bounds")

    def contains(self, point: Point) -> bool:
        return all(a <= value <= b for a, b, value in zip(self.low, self.high, point, strict=True))

    @property
    def volume(self) -> int:
        x, y, z = (b - a + 1 for a, b in zip(self.low, self.high, strict=True))
        return x * y * z

    def points(self) -> Iterator[Point]:
        for y in range(self.low[1], self.high[1] + 1):
            for z in range(self.low[2], self.high[2] + 1):
                for x in range(self.low[0], self.high[0] + 1):
                    yield x, y, z

    def as_dict(self) -> dict[str, Point]:
        return {"low": self.low, "high": self.high}


@dataclass(frozen=True, slots=True)
class BlockState:
    name: str
    properties: tuple[tuple[str, str], ...] = ()

    @classmethod
    def make(cls, name: str, properties: Mapping[str, str] | None = None) -> "BlockState":
        return cls(
            name if ":" in name else f"minecraft:{name}", tuple(sorted((properties or {}).items()))
        )

    @property
    def is_air(self) -> bool:
        return self.name in {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}

    def as_dict(self) -> dict[str, object]:
        return {"name": self.name, "properties": dict(self.properties)}


@dataclass(frozen=True, slots=True)
class Cell:
    state: BlockState
    group: str = "main"
    region: str = "design"

    def as_dict(self) -> dict[str, object]:
        return {**self.state.as_dict(), "group": self.group, "region": self.region}


@dataclass(slots=True)
class Scene:
    id: str
    name: str
    minecraft_version: str
    data_version: int
    revision: int
    bounds: Bounds
    cells: dict[Point, Cell] = field(default_factory=dict)
    protected: set[Point] = field(default_factory=set)

    def summary(self) -> dict[str, object]:
        groups: dict[str, int] = {}
        materials: dict[str, int] = {}
        for cell in self.cells.values():
            if cell.state.is_air:
                continue
            groups[cell.group] = groups.get(cell.group, 0) + 1
            materials[cell.state.name] = materials.get(cell.state.name, 0) + 1
        occupied = None
        occupied_points = [point for point, cell in self.cells.items() if not cell.state.is_air]
        if occupied_points:
            occupied = {
                "low": [min(p[i] for p in occupied_points) for i in range(3)],
                "high": [max(p[i] for p in occupied_points) for i in range(3)],
            }
        return {
            "id": self.id,
            "name": self.name,
            "minecraft_version": self.minecraft_version,
            "data_version": self.data_version,
            "revision": self.revision,
            "bounds": self.bounds.as_dict(),
            "blocks": len(occupied_points),
            "stored_cells": len(self.cells),
            "occupied_bounds": occupied,
            "groups": groups,
            "materials": materials,
            "protected_cells": len(self.protected),
        }


def chunk_key(point: Point) -> Point:
    return tuple(value // CHUNK_SIZE for value in point)  # type: ignore[return-value]
