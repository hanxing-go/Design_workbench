import math
from collections.abc import Mapping
from dataclasses import dataclass
from heapq import heapify, heappop, heappush
from typing import Any, Protocol

from .errors import WorkbenchError
from .models import BlockState, Bounds, Cell, Point, Scene
from .neighbors import affected_neighbors, chest_updates, connected_state

DIRECTIONS = ("north", "east", "south", "west")
VECTORS: dict[str, Point] = {
    "north": (0, 0, -1),
    "east": (1, 0, 0),
    "south": (0, 0, 1),
    "west": (-1, 0, 0),
}


class Registry(Protocol):
    def normalize(self, state: BlockState) -> BlockState: ...


@dataclass(frozen=True)
class EditLimits:
    max_blocks: int = 250_000
    max_cells: int = 500_000
    max_operations: int = 256


@dataclass
class EditPlan:
    cells: dict[Point, Cell]
    changes: list[tuple[Point, Cell | None, Cell | None]]
    touched: int


def as_point(value: Any) -> Point:
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 3
        or any(type(v) is not int for v in value)
    ):
        raise WorkbenchError("INVALID_POINT", "坐标必须是三个整数。", "position")
    return value[0], value[1], value[2]


def as_bounds(value: Mapping[str, Any]) -> Bounds:
    return Bounds(as_point(value["low"]), as_point(value["high"]))


def selected(cells: Mapping[Point, Cell], selector: Mapping[str, Any]) -> dict[Point, Cell]:
    bounds = as_bounds(selector["bounds"]) if selector.get("bounds") else None
    name = BlockState.make(selector["name"]).name if selector.get("name") else None
    return {
        point: cell
        for point, cell in cells.items()
        if (not bounds or bounds.contains(point))
        and (not name or cell.state.name == name)
        and (selector.get("group") is None or cell.group == selector["group"])
        and (selector.get("region") is None or cell.region == selector["region"])
    }


def transform_state(state: BlockState, turns: int, mirror: str | None) -> BlockState:
    old = dict(state.properties)
    properties = dict(old)

    def direction(value: str) -> str:
        if value not in DIRECTIONS:
            return value
        if mirror == "x":
            value = {"east": "west", "west": "east"}.get(value, value)
        if mirror == "z":
            value = {"north": "south", "south": "north"}.get(value, value)
        return DIRECTIONS[(DIRECTIONS.index(value) + turns) % 4]

    if "facing" in old:
        properties["facing"] = direction(old["facing"])
    if "orientation" in old:
        properties["orientation"] = "_".join(
            direction(value) for value in old["orientation"].split("_")
        )
    if turns % 2 and old.get("axis") in {"x", "z"}:
        properties["axis"] = "z" if old["axis"] == "x" else "x"
    if "rotation" in old:
        rotation = int(old["rotation"])
        if mirror == "x":
            rotation = -rotation
        elif mirror == "z":
            rotation = 8 - rotation
        properties["rotation"] = str((rotation + turns * 4) % 16)
    for key in DIRECTIONS:
        if key in old:
            del properties[key]
    for key in DIRECTIONS:
        if key in old:
            properties[direction(key)] = old[key]
    shape = old.get("shape", "")
    if shape.startswith("ascending_"):
        properties["shape"] = "ascending_" + direction(shape[10:])
    elif shape in {
        "north_south",
        "east_west",
        "south_east",
        "south_west",
        "north_west",
        "north_east",
    }:
        transformed = {direction(value) for value in shape.split("_")}
        properties["shape"] = next(
            value
            for value in (
                "north_south",
                "east_west",
                "south_east",
                "south_west",
                "north_west",
                "north_east",
            )
            if set(value.split("_")) == transformed
        )
    elif mirror and shape.endswith(("_left", "_right")):
        prefix, side = shape.rsplit("_", 1)
        properties["shape"] = prefix + ("_right" if side == "left" else "_left")
    if mirror and old.get("hinge") in {"left", "right"}:
        properties["hinge"] = "right" if old["hinge"] == "left" else "left"
    if mirror and state.name.endswith("chest") and old.get("type") in {"left", "right"}:
        properties["type"] = "right" if old["type"] == "left" else "left"
    return BlockState.make(state.name, properties)


def partner(point: Point, cell: Cell) -> Point | None:
    properties = dict(cell.state.properties)
    name = cell.state.name
    if name.endswith("_door") and not name.endswith("_trapdoor"):
        return point[0], point[1] + (1 if properties.get("half") == "lower" else -1), point[2]
    if name.endswith("_bed"):
        vector = VECTORS.get(properties.get("facing", ""))
        if vector:
            sign = 1 if properties.get("part") == "foot" else -1
            return tuple(point[i] + vector[i] * sign for i in range(3))  # type: ignore[return-value]
    if properties.get("half") in {"lower", "upper"} and name.split(":", 1)[1] in {
        "sunflower",
        "lilac",
        "rose_bush",
        "peony",
        "tall_grass",
        "large_fern",
        "pitcher_plant",
        "tall_seagrass",
        "small_dripleaf",
    }:
        return point[0], point[1] + (1 if properties["half"] == "lower" else -1), point[2]
    if name == "minecraft:pitcher_crop" and int(properties.get("age", "0")) >= 3:
        return point[0], point[1] + (1 if properties.get("half") == "lower" else -1), point[2]
    return None


class Editor:
    def __init__(self, registry: Registry, limits: EditLimits) -> None:
        self.registry = registry
        self.limits = limits

    def plan(
        self,
        scene: Scene,
        operations: list[dict[str, Any]],
        *,
        auto_connect: bool = True,
        complete_structures: bool = True,
    ) -> EditPlan:
        if not 1 <= len(operations) <= self.limits.max_operations:
            raise WorkbenchError("OPERATION_LIMIT", "编辑操作数量超出预算。")
        cells = dict(scene.cells)
        touched = 0
        written: set[Point] = set()
        dirty: set[Point] = set()
        pending: dict[Point, Cell | None] = {}
        manual_points: set[Point] = set()

        def apply(point: Point, cell: Cell | None) -> None:
            nonlocal touched
            if not scene.bounds.contains(point):
                raise WorkbenchError("OUT_OF_BOUNDS", f"坐标 {point} 超出工作区。", "position")
            old = cells.get(point)
            if point in scene.protected and (
                cell is None or old is None or cell.state != old.state
            ):
                raise WorkbenchError(
                    "PROTECTED_CONTENT",
                    f"{point} 含导入的实体/NBT，当前支持保留与查看。",
                    "position",
                )
            if cell is None:
                cells.pop(point, None)
            else:
                cells[point] = cell
            if (old.state if old else None) != (cell.state if cell else None):
                dirty.add(point)
            written.add(point)
            touched += 1
            if touched > self.limits.max_cells or len(cells) > self.limits.max_blocks:
                raise WorkbenchError("EDIT_LIMIT", "修改超出方块/操作预算。")

        def put(
            point: Point,
            state: BlockState,
            group: str = "main",
            region: str | None = None,
            *,
            overwrite_pending: bool = False,
        ) -> None:
            normalized = self.registry.normalize(state)
            old = cells.get(point)
            replacement = (
                None
                if normalized.is_air
                else Cell(normalized, group, region or (old.region if old else "design"))
            )
            if point in pending and pending[point] != replacement and not overwrite_pending:
                raise WorkbenchError("EDIT_COLLISION", "同一操作的目标位置/部件彼此重叠。")
            pending[point] = replacement

        def counterpart(cell: Cell) -> Cell:
            properties = dict(cell.state.properties)
            key, opposite = (
                ("part", {"foot": "head", "head": "foot"})
                if cell.state.name.endswith("_bed")
                else ("half", {"lower": "upper", "upper": "lower"})
            )
            properties[key] = opposite[properties[key]]
            return Cell(
                self.registry.normalize(BlockState.make(cell.state.name, properties)),
                cell.group,
                cell.region,
            )

        def finish_operation(complete: bool) -> None:
            primary = dict(pending)
            if complete:
                # Remove only an actual reciprocal partner, never unrelated content
                # that happens to occupy a malformed imported structure's other cell.
                for point, replacement in primary.items():
                    old = cells.get(point)
                    other_point = partner(point, old) if old else None
                    if old is None or other_point is None:
                        continue
                    other = cells.get(other_point)
                    if (
                        not other
                        or other.state.name != old.state.name
                        or partner(other_point, other) != point
                    ):
                        continue
                    if (
                        replacement
                        and replacement.state.name == old.state.name
                        and partner(point, replacement) == other_point
                    ):
                        continue
                    if other_point not in primary:
                        pending[other_point] = None
                # Preflight all implicit parts against both primary writes and the
                # existing scene, so overlaps fail without committing half a structure.
                for point, cell in primary.items():
                    if cell is None:
                        continue
                    other_point = partner(point, cell)
                    if other_point is None:
                        continue
                    expected = counterpart(cell)
                    if other_point in pending:
                        planned_other = pending[other_point]
                        if planned_other is None and other_point not in primary:
                            pending[other_point] = expected
                        elif planned_other is None or planned_other.state != expected.state:
                            raise WorkbenchError(
                                "EDIT_COLLISION", "门、床或高植物的部件位置/状态冲突。"
                            )
                        continue
                    old_other = cells.get(other_point)
                    if old_other and (
                        old_other.state.name != cell.state.name
                        or partner(other_point, old_other) != point
                    ):
                        raise WorkbenchError(
                            "EDIT_COLLISION", "门、床或高植物需要完整且未被占用的位置。"
                        )
                    pending[other_point] = (
                        Cell(expected.state, expected.group, old_other.region)
                        if old_other
                        else expected
                    )
                dirty.update(pending)
            for point, cell in sorted(pending.items(), key=lambda item: item[1] is not None):
                apply(point, cell)
            pending.clear()

        def operation_state(operation: dict[str, Any], key: str = "state") -> BlockState:
            value = operation[key]
            return self.registry.normalize(
                BlockState.make(value["name"], value.get("properties", {}))
            )

        for operation in operations:
            kind = operation["op"]
            group = operation.get("group", "main")
            if kind == "place":
                from .placement import plan_placement

                value = operation["state"]
                state = BlockState.make(value["name"], value.get("properties", {}))
                for point, placed in plan_placement(
                    cells,
                    state,
                    as_point(operation["hit"]),
                    as_point(operation["normal"]),
                    tuple(operation["location"]),
                    operation["facing"],
                    operation.get("automatic", True),
                    self.registry,
                ):
                    put(point, placed, group)
                    if not operation.get("automatic", True):
                        manual_points.add(point)
            elif kind == "set":
                for block in operation["blocks"]:
                    point, state = as_point(block["position"]), operation_state(block)
                    block_group = block.get("group", group)
                    if operation.get("complete_beds") and state.name.endswith("_bed"):
                        other = partner(point, Cell(state, block_group, "design"))
                        if other is None:
                            raise WorkbenchError("INVALID_STATE", "床缺少朝向。")
                        if any(p in cells and not cells[p].state.is_air for p in (point, other)):
                            raise WorkbenchError("EDIT_COLLISION", "床的两格位置必须为空。")
                        put(
                            other,
                            counterpart(Cell(state, block_group, "design")).state,
                            block_group,
                        )
                    put(point, state, block_group)
            elif kind == "fill":
                bounds = as_bounds(operation["bounds"])
                if bounds.volume > self.limits.max_cells:
                    raise WorkbenchError("EDIT_LIMIT", "填充选区超过预算。")
                state = operation_state(operation)
                for point in bounds.points():
                    if not operation.get("hollow") or any(
                        value in {bounds.low[i], bounds.high[i]} for i, value in enumerate(point)
                    ):
                        put(point, state, group)
            elif kind in {"delete", "replace", "group"}:
                chosen = selected(cells, operation.get("selector", {}))
                for point, cell in chosen.items():
                    state = (
                        BlockState.make("air")
                        if kind == "delete"
                        else operation_state(operation)
                        if kind == "replace"
                        else cell.state
                    )
                    if kind == "replace" and complete_structures:
                        old_props = dict(cell.state.properties)
                        new_props = dict(state.properties)
                        old_partner = partner(point, cell)
                        new_partner = partner(point, Cell(state, cell.group, cell.region))
                        if old_partner is not None and new_partner is not None:
                            if cell.state.name.endswith("_bed") and state.name.endswith("_bed"):
                                new_props["part"] = old_props["part"]
                                # A material replacement retains the bed's footprint;
                                # spatial rotation belongs to the transform operation.
                                new_props["facing"] = old_props["facing"]
                            elif "half" in old_props and "half" in new_props:
                                new_props["half"] = old_props["half"]
                            state = self.registry.normalize(BlockState.make(state.name, new_props))
                    put(
                        point,
                        state,
                        operation["name"] if kind == "group" else cell.group,
                        cell.region,
                    )
            elif kind in {"transform", "array"}:
                chosen = selected(cells, operation.get("selector", {}))
                if not chosen:
                    raise WorkbenchError("EMPTY_SELECTION", "选区没有方块。")
                for point, cell in chosen.items():
                    if point in scene.protected:
                        raise WorkbenchError("PROTECTED_CONTENT", "含实体/NBT 的选区当前不能变换。")
                    other = partner(point, cell)
                    other_cell = cells.get(other) if other is not None else None
                    if (
                        other is not None
                        and other_cell is not None
                        and other not in chosen
                        and other_cell.state.name == cell.state.name
                        and partner(other, other_cell) == point
                    ):
                        raise WorkbenchError(
                            "INCOMPLETE_MULTIBLOCK", "请同时选择门、床或高植物的完整部件。"
                        )
                origin = as_point(operation.get("origin", [0, 0, 0]))
                mirror = operation.get("mirror")
                turns = operation.get("rotation", 0) // 90
                offsets = [as_point(operation.get("offset", [0, 0, 0]))]
                if kind == "array":
                    count = as_point(operation["count"])
                    step = as_point(operation["step"])
                    if (
                        any(v < 1 or v > 128 for v in count)
                        or math.prod(count) * len(chosen) > self.limits.max_cells
                    ):
                        raise WorkbenchError("EDIT_LIMIT", "阵列超过预算。")
                    offsets = [
                        (x * step[0], y * step[1], z * step[2])
                        for x in range(count[0])
                        for y in range(count[1])
                        for z in range(count[2])
                        if (x, y, z) != (0, 0, 0)
                    ]
                destination: dict[Point, Cell] = {}
                for offset in offsets:
                    for point, cell in chosen.items():
                        x, y, z = (point[i] - origin[i] for i in range(3))
                        if mirror == "x":
                            x = -x
                        elif mirror == "z":
                            z = -z
                        for _ in range(turns):
                            x, z = -z, x
                        target = (
                            x + origin[0] + offset[0],
                            y + origin[1] + offset[1],
                            z + origin[2] + offset[2],
                        )
                        if target in destination:
                            raise WorkbenchError("EDIT_COLLISION", "变换/阵列目标彼此重叠。")
                        destination[target] = Cell(
                            self.registry.normalize(transform_state(cell.state, turns, mirror)),
                            operation.get("group") or cell.group,
                            cell.region,
                        )
                move = kind == "transform" and not operation.get("copy", False)
                occupied = set(cells) - (set(chosen) if move else set())
                if not operation.get("overwrite", False) and occupied.intersection(destination):
                    raise WorkbenchError(
                        "EDIT_COLLISION", "目标位置已有方块；请调整选区或明确覆盖。"
                    )
                if move:
                    for point in chosen:
                        put(point, BlockState.make("air"))
                for point, cell in destination.items():
                    put(point, cell.state, cell.group, cell.region, overwrite_pending=True)
            elif kind == "extrude":
                polygon = operation["polygon"]
                height, base_y = operation["height"], operation["base_y"]
                x0, x1 = min(p[0] for p in polygon), max(p[0] for p in polygon)
                z0, z1 = min(p[1] for p in polygon), max(p[1] for p in polygon)
                if (x1 - x0 + 1) * (z1 - z0 + 1) * height > self.limits.max_cells:
                    raise WorkbenchError("EDIT_LIMIT", "挤出体积超过预算。")
                state = operation_state(operation)
                for x in range(x0, x1):
                    for z in range(z0, z1):
                        inside, px, pz = False, x + 0.5, z + 0.5
                        for i, (ax, az) in enumerate(polygon):
                            bx, bz = polygon[(i + 1) % len(polygon)]
                            if (az > pz) != (bz > pz) and px < (bx - ax) * (pz - az) / (
                                bz - az
                            ) + ax:
                                inside = not inside
                        if inside:
                            for y in range(base_y, base_y + height):
                                put((x, y, z), state, group)
            elif kind == "arc":
                center = as_point(operation["center"])
                radius, thickness, height = (
                    operation["radius"],
                    operation["thickness"],
                    operation["height"],
                )
                if (2 * radius + 1) ** 2 * height > self.limits.max_cells:
                    raise WorkbenchError("EDIT_LIMIT", "圆弧超过预算。")
                state = operation_state(operation)
                for x in range(-radius, radius + 1):
                    for z in range(-radius, radius + 1):
                        angle = math.degrees(math.atan2(z, x)) % 360
                        if (
                            max(0, radius - thickness) ** 2 <= x * x + z * z <= radius**2
                            and operation["start"] <= angle <= operation["end"]
                        ):
                            for dy in range(height):
                                put((center[0] + x, center[1] + dy, center[2] + z), state, group)
            elif kind == "roof":
                bounds = as_bounds(operation["bounds"])
                state = operation_state(operation)
                axis = 0 if operation["ridge_axis"] == "z" else 2
                if (bounds.high[0] - bounds.low[0] + 1) * (
                    bounds.high[2] - bounds.low[2] + 1
                ) > self.limits.max_cells:
                    raise WorkbenchError("EDIT_LIMIT", "屋顶超过预算。")
                for x in range(bounds.low[0], bounds.high[0] + 1):
                    for z in range(bounds.low[2], bounds.high[2] + 1):
                        coordinate = x if axis == 0 else z
                        level = min(
                            coordinate - bounds.low[axis],
                            bounds.high[axis] - coordinate,
                            operation["height"] - 1,
                        )
                        properties = dict(state.properties)
                        if state.name.endswith("_stairs"):
                            properties.update(
                                {
                                    "facing": ("east" if axis == 0 else "south")
                                    if coordinate <= (bounds.low[axis] + bounds.high[axis]) / 2
                                    else ("west" if axis == 0 else "north"),
                                    "half": "bottom",
                                    "shape": "straight",
                                }
                            )
                        put(
                            (x, bounds.low[1] + level, z),
                            BlockState.make(state.name, properties),
                            group,
                        )
            elif kind == "window":
                bounds = as_bounds(operation["bounds"])
                axis = 0 if operation["axis"] == "x" else 2
                horizontal = 2 if axis == 0 else 0
                if bounds.low[axis] != bounds.high[axis] or bounds.volume > self.limits.max_cells:
                    raise WorkbenchError("INVALID_WINDOW", "窗组必须是单格厚的平面且在预算内。")
                frame, glass = (
                    operation_state(operation, "frame"),
                    operation_state(operation, "glass"),
                )
                for point in bounds.points():
                    edge = point[1] in {bounds.low[1], bounds.high[1]} or point[horizontal] in {
                        bounds.low[horizontal],
                        bounds.high[horizontal],
                    }
                    put(point, frame if edge else glass, group)
            else:
                raise WorkbenchError("UNKNOWN_OPERATION", f"未支持的编辑操作：{kind}。", "op")
            if kind != "place" or operation.get("automatic", True):
                manual_points.difference_update(pending)
            finish_operation(
                complete_structures and kind != "group" or bool(operation.get("complete_beds"))
            )
        if auto_connect:
            candidates = affected_neighbors(dirty, cells)
            for point, chest_state in chest_updates(candidates, cells, manual_points).items():
                cell = cells[point]
                apply(point, Cell(self.registry.normalize(chest_state), cell.group, cell.region))
            for point in sorted(candidates):
                candidate = cells.get(point)
                if (
                    point in manual_points
                    or candidate is None
                    or not candidate.state.name.endswith("_stairs")
                ):
                    continue
                updated_state = connected_state(point, cells, self.registry)
                if updated_state is not None:
                    apply(
                        point,
                        Cell(
                            self.registry.normalize(updated_state),
                            candidate.group,
                            candidate.region,
                        ),
                    )
            # A wall's post can inherit the post above it. Settle from top to bottom
            # while keeping the update local to this transaction's changed cells.
            neighbor_queue = [(-point[1], point[0], point[2]) for point in candidates]
            heapify(neighbor_queue)
            visited: set[Point] = set()
            while neighbor_queue:
                negative_y, x, z = heappop(neighbor_queue)
                point = (x, -negative_y, z)
                if point in visited:
                    continue
                visited.add(point)
                if point in manual_points:
                    continue
                updated_state = connected_state(point, cells, self.registry)
                if updated_state is not None:
                    old = cells[point]
                    apply(
                        point, Cell(self.registry.normalize(updated_state), old.group, old.region)
                    )
                    below = (point[0], point[1] - 1, point[2])
                    below_cell = cells.get(below)
                    if (
                        updated_state.name.endswith("_wall")
                        and below_cell
                        and below_cell.state.name.endswith("_wall")
                    ):
                        heappush(neighbor_queue, (-below[1], below[0], below[2]))
        changes = [
            (point, scene.cells.get(point), cells.get(point))
            for point in sorted(written)
            if scene.cells.get(point) != cells.get(point)
        ]
        return EditPlan(cells, changes, touched)
