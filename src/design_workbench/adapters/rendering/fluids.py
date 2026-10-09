"""Neighbour-dependent fluid surfaces, kept outside the authoritative scene."""

from typing import Any

from design_workbench.domain.models import BlockState, Point, Scene

from ..resources.catalog import Catalog
from ..resources.special import fluid_geometry, fluid_height


def fluid_model(scene: Scene, point: Point, state: BlockState, catalog: Catalog) -> dict[str, Any]:
    def same(p: Point) -> bool:
        cell = scene.cells.get(p)
        return cell is not None and cell.state.name == state.name

    heights = []
    for cx, cz in ((0, 0), (1, 0), (1, 1), (0, 1)):
        samples = [
            (point[0] + dx, point[1], point[2] + dz) for dx in (cx - 1, cx) for dz in (cz - 1, cz)
        ]
        if any(same((p[0], p[1] + 1, p[2])) for p in samples):
            heights.append(1.0)
            continue
        total = weight = 0.0
        for p in samples:
            cell = scene.cells.get(p)
            if same(p) and cell:
                h = fluid_height(cell.state)
                w = 10 if h >= 0.8 else 1
                total += h * w
                weight += w
            elif (
                cell is None
                or cell.state.is_air
                or catalog.blocks[cell.state.name].get("transparent", False)
            ):
                weight += 1
        heights.append(round(total / weight, 6) if weight else fluid_height(state))
    return {"status": "static", "reason": "邻格流体静态预览", **fluid_geometry(state, heights)}
