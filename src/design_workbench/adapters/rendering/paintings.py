from functools import lru_cache
from typing import Any

from design_workbench.domain.models import Scene
from design_workbench.domain.paintings import HORIZONTAL, VARIANTS, Painting
from design_workbench.domain.placement import FACES

from ..formats.litematic import Litematic, region_bounds
from ..formats.painting_entities import read_painting_entity


@lru_cache(maxsize=2)
def imported_paintings(payload: bytes) -> list[Painting]:
    root = Litematic.parse(payload)
    result = []
    for name, region in root["Regions"].items():
        origin = region_bounds(region).low
        for i, entry in enumerate(region.get("Entities", [])):
            painting = read_painting_entity(entry, origin, f"import:{name}:{i}")
            if painting is not None:
                result.append(painting)
    return result


def painting_packet(scene: Scene, source: bytes | None = None) -> list[dict[str, Any]]:
    result = []
    paintings = [(p, False) for p in scene.paintings]
    if source:
        paintings += [(p, True) for p in imported_paintings(source)]
    for painting, protected in paintings:
        center, right, normal = (
            painting.center(),
            HORIZONTAL[painting.facing],
            FACES[painting.facing],
        )
        width, height = VARIANTS[painting.variant]
        vertices = [
            [center[i] + right[i] * x + (y if i == 1 else 0) + normal[i] * 0.001 for i in range(3)]
            for x, y in (
                (-width / 2, -height / 2),
                (width / 2, -height / 2),
                (width / 2, height / 2),
                (-width / 2, height / 2),
            )
        ]
        result.append(
            {
                **painting.as_dict(),
                "protected": protected,
                "texture": "minecraft:painting/" + painting.variant,
                "vertices": [v for p in vertices for v in p],
            }
        )
    return result
