import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from design_workbench.domain.models import BlockState, Cell, Point, Scene, chunk_key

from ..resources.catalog import Catalog
from ..resources.pack import ResourcePack
from .fluids import fluid_model
from .paintings import painting_packet
from .signs import sign_texts


def model_id(cell: Cell) -> str:
    return state_id(cell.state)


@lru_cache(maxsize=65536)
def state_id(state: BlockState) -> str:
    return hashlib.sha256(json.dumps(state.as_dict(), sort_keys=True).encode()).hexdigest()[:20]


@dataclass(slots=True)
class RenderedChunk:
    data: list[list[Any]]
    version: str
    models: dict[str, Any]
    warnings: dict[str, dict[str, Any]]
    byte_size: int


def render_chunk(
    scene: Scene,
    values: list[tuple[Point, Cell]],
    catalog: Catalog,
    pack: ResourcePack,
    texts: dict[Point, list[dict[str, Any]]],
) -> RenderedChunk:
    """Build one chunk, looking up fluid neighbours in the complete scene."""
    data: list[list[Any]] = []
    models: dict[str, Any] = {}
    states: Counter[BlockState] = Counter()
    for point, cell in sorted(values):
        state = cell.state
        if state.is_air:
            continue
        states[state] += 1
        geometry = None
        if point in texts and state.name.endswith("_sign"):
            geometry = {**pack.geometry(state), "texts": texts[point]}
        elif state.name in {"minecraft:water", "minecraft:lava", "minecraft:bubble_column"}:
            geometry = fluid_model(scene, point, state, catalog)
        identifier = (
            hashlib.sha256(
                json.dumps([state.as_dict(), geometry], sort_keys=True).encode()
            ).hexdigest()[:20]
            if geometry is not None
            else state_id(state)
        )
        data.append([*point, identifier, cell.group, point in scene.protected])
        if identifier not in models:
            if geometry is None:
                geometry = pack.geometry(state)
            models[identifier] = {
                **geometry,
                **state.as_dict(),
                "opaque_cube": geometry["opaque_cube"]
                and not catalog.blocks[state.name].get("transparent", False),
            }
    warnings: dict[str, dict[str, Any]] = {}
    for state, count in states.items():
        support = pack.support(state)
        if support["status"] in {"special", "missing"}:
            if state.name not in warnings:
                warnings[state.name] = {"name": state.name, **support, "count": 0}
            warnings[state.name]["count"] += count
    encoded = json.dumps(data, separators=(",", ":")).encode()
    return RenderedChunk(
        data,
        hashlib.sha256(encoded).hexdigest()[:16],
        models,
        warnings,
        len(encoded) + len(json.dumps(models, separators=(",", ":")).encode()),
    )


def render_packet(
    scene: Scene,
    catalog: Catalog,
    pack: ResourcePack,
    known: dict[str, str] | None = None,
    source: bytes | None = None,
) -> dict[str, Any]:
    """Reference renderer; HTTP reuses chunks through RenderCache."""
    texts = sign_texts(source) if source else {}
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
        packet = render_chunk(scene, values, catalog, pack, texts)
        versions[chunk_id] = packet.version
        if known is None or known.get(chunk_id) != packet.version:
            chunks[chunk_id] = packet.data
            models.update(packet.models)
        for name, warning in packet.warnings.items():
            if name not in warnings:
                warnings[name] = {**warning, "count": 0}
            warnings[name]["count"] += warning["count"]
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
