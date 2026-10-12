from .editing import partner
from .models import BlockState, Cell, Point, Scene
from .neighbors import VECTORS, add, chest_updates, connected_state, full_face
from .placement import missing_supports


def inspect_consistency(scene: Scene, registry: object | None = None) -> dict[str, object]:
    issues: list[dict[str, object]] = []
    proposals: list[dict[str, object]] = []
    cells = scene.cells
    missing_parts: dict[Point, tuple[BlockState, Cell] | None] = {}
    paired_chests = chest_updates(set(cells), cells)
    for point, cell in cells.items():
        state = cell.state
        properties = dict(state.properties)
        other_position = partner(point, cell)
        if other_position is not None:
            other = cells.get(other_position)
            if other is None or other.state.name != state.name:
                issues.append(
                    {
                        "position": point,
                        "code": "MISSING_PARTNER",
                        "message": "门、床或高植物缺少对应部件。",
                    }
                )
                if (
                    other is None
                    and scene.bounds.contains(other_position)
                    and point not in scene.protected
                    and other_position not in scene.protected
                ):
                    counterpart = dict(properties)
                    key, values = (
                        ("half", {"lower": "upper", "upper": "lower"})
                        if "half" in properties
                        else ("part", {"foot": "head", "head": "foot"})
                    )
                    counterpart[key] = values[properties[key]]
                    expected = BlockState.make(state.name, counterpart)
                    normalize = getattr(registry, "normalize", None)
                    if callable(normalize):
                        expected = normalize(expected)
                    if other_position in missing_parts:
                        missing_parts[other_position] = None
                    else:
                        missing_parts[other_position] = (expected, cell)
            else:
                counterpart = dict(other.state.properties)
                key, values = (
                    ("half", {"lower": "upper", "upper": "lower"})
                    if "half" in properties
                    else ("part", {"foot": "head", "head": "foot"})
                )
                if (
                    partner(other_position, other) != point
                    or counterpart.get(key) != values.get(properties.get(key, ""))
                    or any(
                        properties.get(k) != counterpart.get(k)
                        for k in ("facing", "open", "hinge")
                        if k in properties
                    )
                ):
                    issues.append(
                        {
                            "position": point,
                            "code": "PARTNER_STATE",
                            "message": "多格部件的状态不一致。",
                        }
                    )
        replacement = paired_chests.get(point) or connected_state(point, cells, registry)
        if point in paired_chests and any(
            add(point, vector) in scene.protected for vector in VECTORS.values()
        ):
            replacement = None
        if replacement is not None and point not in scene.protected:
            proposals.append(
                {"position": point, "state": replacement.as_dict(), "group": cell.group}
            )

        # Report support loss without simulating destructive game physics in a
        # design editor. Imported/floating art stays intact until explicitly edited.
        unsupported = missing_supports(cells, point, state, registry)
        if unsupported:
            issues.append(
                {
                    "position": point,
                    "code": "MISSING_SUPPORT",
                    "supports": unsupported,
                    "message": "方块的支撑面已缺失；保留当前设计，可手动移除或补上支撑。",
                }
            )
    proposals.extend(
        {"position": point, "state": candidate[0].as_dict(), "group": candidate[1].group}
        for point, candidate in missing_parts.items()
        if candidate is not None
    )
    return {
        "revision": scene.revision,
        "issues": issues,
        "proposals": proposals,
        "rules": "doors/beds/tall plants; stairs; panes/bars; fence families/gates; walls; attachment support",
        "limitations": ["不模拟游戏物理、流体、红石更新；附着物失去支撑时仅提示"],
        "requires_confirmation": True,
    }


def is_simple_solid(cell: Cell) -> bool:
    """Compatibility wrapper for callers of the previous consistency helper."""
    return full_face(cell, "north")
