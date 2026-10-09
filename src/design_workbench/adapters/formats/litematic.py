import copy
import gzip
import io
import math
import time
import uuid
from collections import defaultdict
from typing import Any

import nbtlib

from design_workbench.domain.editing import Registry
from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.models import BlockState, Bounds, Cell, Point, Scene

REGION_KEYS = {
    "Position",
    "Size",
    "BlockStatePalette",
    "BlockStates",
    "Entities",
    "TileEntities",
    "PendingBlockTicks",
    "PendingFluidTicks",
}


def vector(value: Any) -> Point:
    return int(value["x"]), int(value["y"]), int(value["z"])


def point3(values: Any) -> Point:
    x, y, z = values
    return int(x), int(y), int(z)


def nbt_vector(point: Point) -> Any:
    return nbtlib.Compound(
        {axis: nbtlib.Int(value) for axis, value in zip("xyz", point, strict=True)}
    )


def region_bounds(region: Any) -> Bounds:
    origin, size = vector(region["Position"]), vector(region["Size"])
    if any(value == 0 for value in size):
        raise WorkbenchError("INVALID_LITEMATIC", "区域尺寸不能为零。")
    return Bounds(
        point3(origin[i] + min(0, size[i] + 1) for i in range(3)),
        point3(origin[i] + max(0, size[i] - 1) for i in range(3)),
    )


def overlap(first: Bounds, second: Bounds) -> bool:
    return all(first.low[i] <= second.high[i] and second.low[i] <= first.high[i] for i in range(3))


def unpack_states(words: Any, length: int, palette_size: int) -> list[int]:
    bits = max(2, (palette_size - 1).bit_length())
    if len(words) * 64 < length * bits:
        raise WorkbenchError("INVALID_LITEMATIC", "方块状态数组被截断。")
    unsigned = [int(word) & ((1 << 64) - 1) for word in words]
    mask = (1 << bits) - 1
    result = []
    for index in range(length):
        word, offset = divmod(index * bits, 64)
        value = unsigned[word] >> offset
        if offset + bits > 64:
            value |= unsigned[word + 1] << (64 - offset)
        value &= mask
        if value >= palette_size:
            raise WorkbenchError("INVALID_PALETTE_INDEX", "方块引用不存在的调色板项。")
        result.append(value)
    return result


def pack_states(indices: list[int], palette_size: int) -> Any:
    bits = max(2, (palette_size - 1).bit_length())
    words = [0] * ((len(indices) * bits + 63) // 64)
    mask64 = (1 << 64) - 1
    for index, value in enumerate(indices):
        word, offset = divmod(index * bits, 64)
        words[word] |= (value << offset) & mask64
        if offset + bits > 64:
            words[word + 1] |= value >> (64 - offset)
    return nbtlib.LongArray([word if word < 1 << 63 else word - (1 << 64) for word in words])


class Litematic:
    def __init__(
        self,
        registry: Registry,
        version: str = "1.20.1",
        data_version: int = 3465,
        max_volume: int = 2_000_000,
    ) -> None:
        self.registry, self.version, self.data_version, self.max_volume = (
            registry,
            version,
            data_version,
            max_volume,
        )

    @staticmethod
    def parse(payload: bytes) -> Any:
        if len(payload) > 32_000_000:
            raise WorkbenchError("ASSET_LIMIT", "蓝图文件超过 32 MB。")
        try:
            if payload[:2] == b"\x1f\x8b":
                with gzip.GzipFile(fileobj=io.BytesIO(payload)) as compressed:
                    raw = compressed.read(64_000_001)
                if len(raw) > 64_000_000:
                    raise WorkbenchError("ASSET_LIMIT", "蓝图解压超过 64 MB。")
            else:
                raw = payload
            document = nbtlib.File.parse(io.BytesIO(raw))
            if int(document.get("Version", 0)) != 6:
                raise WorkbenchError("UNSUPPORTED_FORMAT", "当前兼容范围为 Litematica v6。")
            if "MinecraftDataVersion" not in document or "Regions" not in document:
                raise WorkbenchError("INVALID_LITEMATIC", "蓝图缺少版本或区域。")
            return document
        except (ValueError, KeyError, EOFError, OSError, IndexError) as error:
            raise WorkbenchError("INVALID_LITEMATIC", "蓝图不是完整有效的 NBT 文件。") from error

    def state(self, entry: Any) -> BlockState:
        return self.registry.normalize(
            BlockState.make(
                str(entry["Name"]),
                {str(key): str(value) for key, value in entry.get("Properties", {}).items()},
            )
        )

    def read(self, payload: bytes) -> tuple[Scene, dict[str, Any]]:
        root = self.parse(payload)
        if int(root["MinecraftDataVersion"]) != self.data_version:
            raise WorkbenchError(
                "VERSION_MISMATCH",
                f"蓝图 DataVersion={int(root['MinecraftDataVersion'])}；项目需要 {self.data_version}（{self.version}）。",
            )
        cells: dict[Point, Cell] = {}
        protected: set[Point] = set()
        boxes: list[Bounds] = []
        volume = 0
        block_entities, entities = 0, 0
        unknown: dict[str, list[str]] = {}
        try:
            regions = root["Regions"]
            if not regions or len(regions) > 256:
                raise WorkbenchError("REGION_LIMIT", "蓝图需包含 1..256 个区域。")
            for name, region in regions.items():
                bounds = region_bounds(region)
                if any(overlap(bounds, previous) for previous in boxes):
                    raise WorkbenchError(
                        "REGION_OVERLAP",
                        "区域包围盒重叠，空气覆盖顺序存在歧义；请先拆分为不重叠区域。",
                    )
                boxes.append(bounds)
                volume += bounds.volume
                if volume > self.max_volume:
                    raise WorkbenchError("ASSET_LIMIT", "蓝图区域总体积超过预算。")
                palette = [self.state(entry) for entry in region["BlockStatePalette"]]
                if not palette:
                    raise WorkbenchError("INVALID_PALETTE", "区域调色板为空。")
                indices = unpack_states(region["BlockStates"], bounds.volume, len(palette))
                sx, _, sz = (b - a + 1 for a, b in zip(bounds.low, bounds.high, strict=True))
                for index, state_index in enumerate(indices):
                    state = palette[state_index]
                    if state.name == "minecraft:air":
                        continue
                    point = (
                        bounds.low[0] + index % sx,
                        bounds.low[1] + index // (sx * sz),
                        bounds.low[2] + index // sx % sz,
                    )
                    if point in cells:
                        raise WorkbenchError(
                            "REGION_OVERLAP", "多个区域的内容重叠；请先拆分或明确合并。"
                        )
                    cells[point] = Cell(state, str(name), str(name))
                for entry in region.get("TileEntities", []):
                    position = vector(entry)
                    protected.add(point3(bounds.low[i] + position[i] for i in range(3)))
                    block_entities += 1
                for entry in region.get("Entities", []):
                    if "Pos" in entry:
                        protected.add(
                            point3(
                                bounds.low[i] + math.floor(float(entry["Pos"][i])) for i in range(3)
                            )
                        )
                    entities += 1
                for kind in ("PendingBlockTicks", "PendingFluidTicks"):
                    for entry in region.get(kind, []):
                        if all(axis in entry for axis in "xyz"):
                            position = vector(entry)
                            protected.add(point3(bounds.low[i] + position[i] for i in range(3)))
                extra = sorted(set(region) - REGION_KEYS)
                if extra:
                    unknown[str(name)] = extra
                    protected.update(bounds.points())
            enclosing = Bounds(
                point3(min(box.low[i] for box in boxes) for i in range(3)),
                point3(max(box.high[i] for box in boxes) for i in range(3)),
            )
            meta = root.get("Metadata", {})
            scene = Scene(
                str(uuid.uuid4()),
                str(meta.get("Name", "导入建筑")),
                self.version,
                self.data_version,
                0,
                enclosing,
                cells,
                protected,
            )
            report = {
                "version": 6,
                "data_version": self.data_version,
                "regions": len(regions),
                "blocks": sum(not cell.state.is_air for cell in cells.values()),
                "volume": volume,
                "block_entities": block_entities,
                "entities": entities,
                "unknown_region_tags": unknown,
                "preserved_source": True,
                "special_content_editing": "read_only",
            }
            return scene, report
        except (KeyError, ValueError, TypeError, IndexError) as error:
            raise WorkbenchError("INVALID_LITEMATIC", "蓝图区域结构不完整。") from error

    @staticmethod
    def tag_state(state: BlockState) -> Any:
        entry = nbtlib.Compound({"Name": nbtlib.String(state.name)})
        if state.properties:
            entry["Properties"] = nbtlib.Compound(
                {key: nbtlib.String(value) for key, value in state.properties}
            )
        return entry

    def write(
        self, scene: Scene, source: bytes | None = None, allow_lossy: bool = False
    ) -> tuple[bytes, dict[str, Any]]:
        if scene.data_version != self.data_version:
            raise WorkbenchError("VERSION_MISMATCH", "场景版本与导出适配器不同。")
        if source is not None:
            root = copy.deepcopy(self.parse(source))
            if int(root["MinecraftDataVersion"]) != self.data_version:
                raise WorkbenchError("VERSION_MISMATCH", "原始蓝图版本与场景不同。")
        else:
            root = nbtlib.File(
                {
                    "Version": nbtlib.Int(6),
                    "SubVersion": nbtlib.Int(1),
                    "MinecraftDataVersion": nbtlib.Int(self.data_version),
                    "Metadata": nbtlib.Compound(
                        {
                            "Author": nbtlib.String("Design Workbench"),
                            "Name": nbtlib.String(scene.name),
                            "Description": nbtlib.String(""),
                            "TimeCreated": nbtlib.Long(int(time.time() * 1000)),
                        }
                    ),
                    "Regions": nbtlib.Compound(),
                }
            )
        regions = root["Regions"]
        boxes = {str(name): region_bounds(region) for name, region in regions.items()}
        assigned: dict[str, dict[Point, Cell]] = defaultdict(dict)
        additions: dict[Point, Cell] = {}
        for point, cell in scene.cells.items():
            containing = [name for name, box in boxes.items() if box.contains(point)]
            if len(containing) > 1:
                raise WorkbenchError("REGION_OVERLAP", "导出区域重叠，无法确定方块归属。")
            target = (
                cell.region
                if cell.region in boxes and boxes[cell.region].contains(point)
                else containing[0]
                if containing
                else None
            )
            if target is None:
                additions[point] = cell
            else:
                assigned[target][point] = cell
        if additions or not boxes:
            box = (
                Bounds(
                    point3(min(p[i] for p in additions) for i in range(3)),
                    point3(max(p[i] for p in additions) for i in range(3)),
                )
                if additions
                else Bounds((0, 0, 0), (0, 0, 0))
            )
            if any(overlap(box, previous) for previous in boxes.values()):
                raise WorkbenchError(
                    "EXPORT_REGION_OVERLAP",
                    "新增方块的包围盒与原蓝图区域重叠；请在一侧扩建设计，或导出无实体/NBT 的独立新场景。",
                )
            if sum(box.volume for box in boxes.values()) + box.volume > self.max_volume:
                raise WorkbenchError("EXPORT_LIMIT", "导出区域总体积超过预算。")
            name = "Design"
            while name in boxes:
                name += "_new"
            regions[name] = nbtlib.Compound(
                {
                    "Position": nbt_vector(box.low),
                    "Size": nbt_vector(
                        point3(b - a + 1 for a, b in zip(box.low, box.high, strict=True))
                    ),
                    "BlockStatePalette": nbtlib.List[nbtlib.Compound](
                        [self.tag_state(BlockState.make("air"))]
                    ),
                    "BlockStates": pack_states([0] * box.volume, 1),
                    "Entities": nbtlib.List[nbtlib.Compound](),
                    "TileEntities": nbtlib.List[nbtlib.Compound](),
                    "PendingBlockTicks": nbtlib.List[nbtlib.Compound](),
                    "PendingFluidTicks": nbtlib.List[nbtlib.Compound](),
                }
            )
            boxes[name], assigned[name] = box, additions
        total_volume = sum(box.volume for box in boxes.values())
        if total_volume > self.max_volume:
            raise WorkbenchError("EXPORT_LIMIT", "导出区域总体积超过预算；请缩小空间范围。")
        for name, region in regions.items():
            box = boxes[str(name)]
            palette_tags = region["BlockStatePalette"]
            palette = [self.state(entry) for entry in palette_tags]
            lookup = {state: index for index, state in enumerate(palette)}
            air = BlockState.make("air")
            if air not in lookup:
                lookup[air] = len(palette)
                palette.append(air)
                palette_tags.append(self.tag_state(air))
            # The scene is authoritative, including explicitly stored cave/void air.
            # Reusing original air entries would resurrect deleted special air.
            indices = [lookup[air]] * box.volume
            sx, _, sz = (b - a + 1 for a, b in zip(box.low, box.high, strict=True))
            for point, cell in assigned[str(name)].items():
                state = self.registry.normalize(cell.state)
                if state not in lookup:
                    lookup[state] = len(palette)
                    palette.append(state)
                    palette_tags.append(self.tag_state(state))
                index = (
                    point[0]
                    - box.low[0]
                    + (point[2] - box.low[2]) * sx
                    + (point[1] - box.low[1]) * sx * sz
                )
                indices[index] = lookup[state]
            region["BlockStates"] = pack_states(indices, len(palette))
        meta = root["Metadata"]
        meta["Name"] = nbtlib.String(scene.name)
        meta["TimeModified"] = nbtlib.Long(int(time.time() * 1000))
        meta["RegionCount"] = nbtlib.Int(len(boxes))
        meta["TotalBlocks"] = nbtlib.Int(
            sum(not cell.state.is_air for cell in scene.cells.values())
        )
        meta["TotalVolume"] = nbtlib.Int(total_volume)
        meta["EnclosingSize"] = nbt_vector(
            point3(
                max(box.high[i] for box in boxes.values())
                - min(box.low[i] for box in boxes.values())
                + 1
                for i in range(3)
            )
        )
        stream = io.BytesIO()
        root.write(stream)
        result = gzip.compress(stream.getvalue(), mtime=0)
        report = {
            "revision": scene.revision,
            "regions": len(boxes),
            "blocks": int(meta["TotalBlocks"]),
            "volume": total_volume,
            "losses": [],
            "preserved_source": source is not None,
            "bytes": len(result),
            "allow_lossy": allow_lossy,
        }
        return result, report
