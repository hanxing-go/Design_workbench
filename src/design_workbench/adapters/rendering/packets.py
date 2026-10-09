import hashlib
import json
from collections import defaultdict
from typing import Any

from design_workbench.domain.models import Cell, Point, Scene, chunk_key

from ..resources.catalog import Catalog
from ..resources.pack import ResourcePack
from .fluids import fluid_model
from .paintings import painting_packet
from .signs import sign_texts


def model_id(cell: Cell) -> str:
    return hashlib.sha256(json.dumps(cell.state.as_dict(), sort_keys=True).encode()).hexdigest()[
        :20
    ]


def render_packet(
    scene: Scene,
    catalog: Catalog,
    pack: ResourcePack,
    known: dict[str, str] | None = None,
    source: bytes | None = None,
) -> dict[str, Any]:
    contextual: dict[Point, tuple[str, dict[str, Any]]] = {}
    texts = sign_texts(source) if source else {}
    for point, cell in scene.cells.items():
        if point in texts and cell.state.name.endswith("_sign"):
            geometry = {**pack.geometry(cell.state), "texts": texts[point]}
            identifier = hashlib.sha256(
                json.dumps([cell.state.as_dict(), geometry], sort_keys=True).encode()
            ).hexdigest()[:20]
            contextual[point] = identifier, geometry
        elif cell.state.name in {"minecraft:water", "minecraft:lava"}:
            geometry = fluid_model(scene, point, cell.state, catalog)
            identifier = hashlib.sha256(
                json.dumps([cell.state.as_dict(), geometry], sort_keys=True).encode()
            ).hexdigest()[:20]
            contextual[point] = identifier, geometry

    def identifier_at(point: Point, cell: Cell) -> str:
        return contextual[point][0] if point in contextual else model_id(cell)

    groups: dict[Point, list[tuple[Point, Cell]]] = defaultdict(list)
    for point, cell in scene.cells.items():
        if not cell.state.is_air:
            groups[chunk_key(point)].append((point, cell))
    chunks: dict[str, Any] = {}
    versions: dict[str, str] = {}
    models: dict[str, Any] = {}
    warnings: dict[str, dict[str, Any]] = {}
    for key, values in groups.items():
        chunk_id = ",".join(str(v) for v in key)
        data = [
            [*point, identifier_at(point, cell), cell.group, point in scene.protected]
            for point, cell in sorted(values)
        ]
        version = hashlib.sha256(json.dumps(data, separators=(",", ":")).encode()).hexdigest()[:16]
        versions[chunk_id] = version
        changed = known is None or known.get(chunk_id) != version
        if changed:
            chunks[chunk_id] = data
        for point, cell in values:
            identifier = identifier_at(point, cell)
            if changed and identifier not in models:
                geometry = (
                    contextual[point][1] if point in contextual else pack.geometry(cell.state)
                )
                block = catalog.blocks[cell.state.name]
                models[identifier] = {
                    **geometry,
                    **cell.state.as_dict(),
                    "opaque_cube": geometry["opaque_cube"] and not block.get("transparent", False),
                }
            support = pack.support(cell.state)
            if support["status"] in {"special", "missing"}:
                key_state = cell.state.name
                if key_state not in warnings:
                    warnings[key_state] = {"name": key_state, **support, "count": 0}
                warnings[key_state]["count"] += 1
    return {
        "revision": scene.revision,
        "summary": scene.summary(),
        "chunks": chunks,
        "chunk_versions": versions,
        "removed_chunks": sorted(set(known or {}) - set(versions)),
        "models": models,
        "warnings": list(warnings.values()),
        "atlas": pack.atlas,
        "resource_hash": pack.manifest["bundle_hash"],
        "paintings": painting_packet(scene, source),
    }
