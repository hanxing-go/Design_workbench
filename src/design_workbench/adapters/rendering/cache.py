"""Bounded, read-only scene projections for incremental rendering.

Database writes remain authoritative. A persistent SQLite observer invalidates
the projection on every external commit, even if revision fields were unchanged.
Compressed BLOB comparison happens only after a write; only changed chunks are
decompressed, and only affected render chunks are rebuilt.
"""

from collections import Counter, OrderedDict
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any

from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.models import Bounds, Cell, Point, Scene, chunk_key
from design_workbench.domain.paintings import Painting

from ..resources.catalog import Catalog
from ..resources.pack import ResourcePack
from ..storage.sqlite import RenderRead, SqliteStore, decode_chunk
from .packets import RenderedChunk, render_chunk
from .paintings import painting_packet
from .signs import sign_texts

FLUIDS = {"minecraft:water", "minecraft:lava", "minecraft:bubble_column"}


def file_identity(path: Path) -> tuple[int, int]:
    try:
        stat = path.stat()
    except FileNotFoundError as error:
        raise WorkbenchError("PROJECT_NOT_FOUND", f"项目不存在：{path}。") from error
    return stat.st_dev, stat.st_ino


@dataclass(slots=True)
class ChunkSummary:
    stored: int
    blocks: int
    groups: Counter[str]
    materials: Counter[str]
    low: Point | None
    high: Point | None

    @classmethod
    def build(cls, cells: dict[Point, Cell]) -> "ChunkSummary":
        groups: Counter[str] = Counter()
        materials: Counter[str] = Counter()
        low = high = None
        count = 0
        for point, cell in cells.items():
            if cell.state.is_air:
                continue
            groups[cell.group] += 1
            materials[cell.state.name] += 1
            count += 1
            if low is None or high is None:
                low = high = point
            else:
                low = (min(low[0], point[0]), min(low[1], point[1]), min(low[2], point[2]))
                high = (max(high[0], point[0]), max(high[1], point[1]), max(high[2], point[2]))
        return cls(len(cells), count, groups, materials, low, high)


class _ProjectProjection:
    def __init__(self, store: SqliteStore) -> None:
        self.store = store
        self.identity = file_identity(store.path)
        self.connection = store.open_render_reader()
        self.data_version: int | None = None
        self.raw: dict[Point, bytes] = {}
        self.decoded: dict[Point, dict[Point, Cell]] = {}
        self.summaries: dict[Point, ChunkSummary] = {}
        self.rendered: dict[Point, RenderedChunk] = {}
        self.fluid_keys: set[Point] = set()
        self.scene: Scene | None = None
        self.source: bytes | None = None
        self.texts: dict[Point, list[dict[str, Any]]] = {}
        self.summary: dict[str, Any] = {}
        self.history: dict[str, Any] = {}
        self.pack: ResourcePack | None = None
        self.catalog: Catalog | None = None
        self.resource_hash: str | None = None
        self.render_dirty: set[Point] = set()

    def close(self) -> None:
        self.connection.close()

    @property
    def cells(self) -> int:
        return len(self.scene.cells) if self.scene else 0

    @property
    def byte_size(self) -> int:
        # Cell and Python-container overhead is additionally bounded by max_cells.
        return (
            sum(len(value) for value in self.raw.values())
            + len(self.source or b"")
            + sum(chunk.byte_size for chunk in self.rendered.values())
        )

    def refresh(self) -> None:
        read = self.store.read_render_data(self.connection, self.data_version)
        if read is None:
            return
        self._update(read)
        self.data_version = read.data_version

    def _update(self, read: RenderRead) -> None:
        changed = {
            key
            for key in self.raw.keys() | read.chunks.keys()
            if self.raw.get(key) != read.chunks.get(key)
        }
        data = read.metadata
        protected = {tuple(point) for point in data.get("protected", [])}
        previous_protected = self.scene.protected if self.scene else set()
        self.render_dirty.update(chunk_key(point) for point in protected ^ previous_protected)
        cells = self.scene.cells if self.scene else {}
        for key in changed:
            for point in self.decoded.pop(key, {}):
                cells.pop(point, None)
            self.summaries.pop(key, None)
            self.fluid_keys.discard(key)
            if key in read.chunks:
                chunk_cells = decode_chunk(key, read.chunks[key])
                self.decoded[key] = chunk_cells
                self.summaries[key] = ChunkSummary.build(chunk_cells)
                cells.update(chunk_cells)
                if any(cell.state.name in FLUIDS for cell in chunk_cells.values()):
                    self.fluid_keys.add(key)
        self.scene = Scene(
            data["id"],
            data["name"],
            data["minecraft_version"],
            data["data_version"],
            data["revision"],
            Bounds(tuple(data["bounds"]["low"]), tuple(data["bounds"]["high"])),
            cells,
            protected,
            [Painting.from_dict(value) for value in data.get("paintings", [])],
        )
        self.render_dirty.update(changed)
        # Fluid corners sample the 3x3 XZ neighbourhood and cells one layer above.
        # A whole changed chunk can therefore invalidate fluid chunks at its own
        # chunk Y and the chunk below, including horizontal diagonals.
        for x, y, z in changed:
            self.render_dirty.update(
                key
                for dx in (-1, 0, 1)
                for dy in (-1, 0)
                for dz in (-1, 0, 1)
                if (key := (x + dx, y + dy, z + dz)) in self.fluid_keys
            )
        if read.source != self.source:
            texts = sign_texts(read.source) if read.source else {}
            self.render_dirty.update(
                chunk_key(point)
                for point in self.texts.keys() | texts.keys()
                if self.texts.get(point) != texts.get(point)
            )
            self.texts = texts
            self.source = read.source
        self.raw = read.chunks
        self.history = read.history
        self.summary = self._summary()

    def _summary(self) -> dict[str, Any]:
        assert self.scene is not None
        groups: Counter[str] = Counter()
        materials: Counter[str] = Counter()
        low = high = None
        blocks = stored = 0
        for summary in self.summaries.values():
            blocks += summary.blocks
            stored += summary.stored
            groups.update(summary.groups)
            materials.update(summary.materials)
            if summary.low is None or summary.high is None:
                continue
            if low is None or high is None:
                low, high = summary.low, summary.high
            else:
                low = (
                    min(low[0], summary.low[0]),
                    min(low[1], summary.low[1]),
                    min(low[2], summary.low[2]),
                )
                high = (
                    max(high[0], summary.high[0]),
                    max(high[1], summary.high[1]),
                    max(high[2], summary.high[2]),
                )
        scene = self.scene
        return {
            "id": scene.id,
            "name": scene.name,
            "minecraft_version": scene.minecraft_version,
            "data_version": scene.data_version,
            "revision": scene.revision,
            "bounds": scene.bounds.as_dict(),
            "blocks": blocks,
            "stored_cells": stored,
            "paintings": len(scene.paintings),
            "occupied_bounds": {"low": list(low), "high": list(high)} if low and high else None,
            "groups": dict(groups),
            "materials": dict(materials),
            "protected_cells": len(scene.protected),
        }

    def render(
        self, catalog: Catalog, pack: ResourcePack, known: dict[str, str] | None
    ) -> dict[str, Any]:
        assert self.scene is not None
        resource_hash = str(pack.manifest["bundle_hash"])
        if (
            self.pack is not pack
            or self.catalog is not catalog
            or self.resource_hash != resource_hash
        ):
            self.render_dirty.update(self.decoded)
            self.pack, self.catalog, self.resource_hash = pack, catalog, resource_hash
        for key in self.render_dirty:
            summary = self.summaries.get(key)
            if summary is None or summary.blocks == 0:
                self.rendered.pop(key, None)
            else:
                self.rendered[key] = render_chunk(
                    self.scene,
                    list(self.decoded[key].items()),
                    catalog,
                    pack,
                    self.texts,
                )
        self.render_dirty.clear()
        versions: dict[str, str] = {}
        chunks: dict[str, Any] = {}
        models: dict[str, Any] = {}
        warnings: dict[str, dict[str, Any]] = {}
        # Never mutate objects already handed to a concurrent HTTP serializer.
        # Resource identity is part of the transport token, so a pack replacement
        # sends models again even when the authoritative block state is unchanged.
        for key, chunk in self.rendered.items():
            identifier = ",".join(str(v) for v in key)
            version = f"{resource_hash}:{chunk.version}"
            versions[identifier] = version
            if known is None or known.get(identifier) != version:
                chunks[identifier] = chunk.data
                models.update(chunk.models)
            for name, warning in chunk.warnings.items():
                if name not in warnings:
                    warnings[name] = {**warning, "count": 0}
                warnings[name]["count"] += warning["count"]
        return {
            "revision": self.scene.revision,
            "summary": self.summary,
            "chunks": chunks,
            "chunk_versions": versions,
            "removed_chunks": sorted(set(known or {}) - set(versions)),
            "models": models,
            "warnings": list(warnings.values()),
            "atlas": pack.atlas,
            "resource_hash": resource_hash,
            "paintings": painting_packet(self.scene, self.source),
        }


class RenderCache:
    def __init__(
        self,
        max_projects: int = 4,
        max_cells: int = 500_000,
        max_bytes: int = 128_000_000,
    ) -> None:
        if min(max_projects, max_cells, max_bytes) < 1:
            raise ValueError("render cache limits must be positive")
        self.max_projects, self.max_cells, self.max_bytes = max_projects, max_cells, max_bytes
        self._entries: OrderedDict[Path, _ProjectProjection] = OrderedDict()
        # The lock covers connection use, cache updates, LRU eviction and shutdown.
        self._lock = RLock()

    def _projection(self, path: Path, timeout: float) -> _ProjectProjection:
        path = path.resolve()
        current = self._entries.get(path)
        if current is not None and current.identity != file_identity(path):
            self._entries.pop(path).close()
            current = None
        if current is None:
            current = _ProjectProjection(SqliteStore(path, timeout))
            self._entries[path] = current
        self._entries.move_to_end(path)
        current.refresh()
        return current

    def _trim(self) -> None:
        while self._entries and (
            len(self._entries) > self.max_projects
            or sum(entry.cells for entry in self._entries.values()) > self.max_cells
            or sum(entry.byte_size for entry in self._entries.values()) > self.max_bytes
        ):
            _, entry = self._entries.popitem(last=False)
            entry.close()

    def summary(self, path: Path, timeout: float = 10.0) -> dict[str, Any]:
        with self._lock:
            try:
                projection = self._projection(path, timeout)
                return {**projection.summary, **projection.history}
            except Exception:
                self._discard(path)
                raise
            finally:
                self._trim()

    def render(
        self,
        path: Path,
        catalog: Catalog,
        pack: ResourcePack,
        known: dict[str, str] | None = None,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        with self._lock:
            try:
                return self._projection(path, timeout).render(catalog, pack, known)
            except Exception:
                self._discard(path)
                raise
            finally:
                self._trim()

    def _discard(self, path: Path) -> None:
        projection = self._entries.pop(path.resolve(), None)
        if projection is not None:
            projection.close()

    def close(self) -> None:
        with self._lock:
            for projection in self._entries.values():
                projection.close()
            self._entries.clear()
