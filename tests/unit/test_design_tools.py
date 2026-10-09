from typing import Any

from design_workbench.application.contracts import EditRequest
from design_workbench.application.scenes import SceneService


def apply(service: SceneService, operations: list[dict[str, Any]]) -> None:
    service.edit(
        EditRequest.model_validate(
            {
                "expected_revision": service.summary()["revision"],
                "request_id": f"tools-{service.summary()['revision']}",
                "operations": operations,
            }
        )
    )


def test_polygon_extrusion_and_array_remain_editable(service: SceneService) -> None:
    apply(
        service,
        [
            {
                "op": "extrude",
                "polygon": [[0, 0], [4, 0], [4, 3], [0, 3]],
                "base_y": 0,
                "height": 2,
                "state": {"name": "stone"},
                "group": "body",
            }
        ],
    )
    assert service.summary()["blocks"] == 24
    apply(
        service,
        [{"op": "array", "selector": {"group": "body"}, "count": [2, 1, 1], "step": [6, 0, 0]}],
    )
    assert service.summary()["blocks"] == 48
    apply(
        service, [{"op": "delete", "selector": {"bounds": {"low": [0, 0, 0], "high": [0, 0, 0]}}}]
    )
    assert service.summary()["blocks"] == 47


def test_roof_window_arc_geometry(service: SceneService) -> None:
    apply(
        service,
        [
            {
                "op": "roof",
                "bounds": {"low": [0, 5, 0], "high": [7, 5, 9]},
                "height": 4,
                "ridge_axis": "z",
                "state": {"name": "oak_stairs"},
            }
        ],
    )
    assert service.summary()["blocks"] == 80
    scene = service.repository.load()
    assert (3, 8, 0) in scene.cells and (4, 8, 0) in scene.cells
    assert dict(scene.cells[(0, 5, 0)].state.properties)["facing"] == "east"
    assert dict(scene.cells[(7, 5, 0)].state.properties)["facing"] == "west"
    apply(
        service,
        [
            {
                "op": "window",
                "bounds": {"low": [0, 1, 0], "high": [4, 3, 0]},
                "axis": "z",
                "frame": {"name": "oak_log"},
                "glass": {"name": "glass"},
            }
        ],
    )
    assert scene.cells[(0, 5, 0)].group == "roof"
    assert service.repository.load().cells[(2, 2, 0)].state.name == "minecraft:glass"
    apply(
        service,
        [
            {
                "op": "arc",
                "center": [20, 0, 20],
                "radius": 4,
                "height": 2,
                "state": {"name": "bricks"},
            }
        ],
    )
    assert (24, 0, 20) in service.repository.load().cells
