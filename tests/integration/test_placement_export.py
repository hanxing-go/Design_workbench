from pathlib import Path

from litemapy import Schematic

from design_workbench.application.contracts import EditRequest, HistoryRequest
from design_workbench.application.scenes import SceneService


def test_automatic_state_history_and_export_match_independent_reader(
    service: SceneService,
    tmp_path: Path,
) -> None:
    result = service.edit(
        EditRequest.model_validate(
            {
                "expected_revision": 0,
                "request_id": "connected-structure",
                "operations": [
                    {
                        "op": "set",
                        "blocks": [
                            {"position": [0, 0, 0], "state": {"name": "iron_bars"}},
                            {"position": [1, 0, 0], "state": {"name": "blue_stained_glass_pane"}},
                            {
                                "position": [4, 0, 0],
                                "state": {"name": "oak_door", "properties": {"facing": "east"}},
                            },
                        ],
                    }
                ],
            }
        )
    )
    assert result["changed"] == 4
    place = {
        "op": "place",
        "state": {"name": "oak_slab"},
        "hit": [8, -1, 0],
        "normal": [0, 1, 0],
        "location": [0.5, 1, 0.5],
        "facing": "north",
    }
    service.edit(
        EditRequest.model_validate(
            {
                "expected_revision": 1,
                "request_id": "half-slab",
                "operations": [place],
            }
        )
    )
    service.edit(
        EditRequest.model_validate(
            {
                "expected_revision": 2,
                "request_id": "merge-slab",
                "operations": [{**place, "hit": [8, 0, 0], "location": [0.5, 0.5, 0.5]}],
            }
        )
    )
    before = service.repository.load()
    assert dict(before.cells[(8, 0, 0)].state.properties)["type"] == "double"
    service.history("undo", HistoryRequest(expected_revision=3, request_id="undo-slab"))
    assert dict(service.repository.load().cells[(8, 0, 0)].state.properties)["type"] == "bottom"
    service.history("redo", HistoryRequest(expected_revision=4, request_id="redo-slab"))
    after = service.repository.load()
    assert before.cells == after.cells

    payload, report = service.export_asset(5)
    exported = tmp_path / "automatic.litematic"
    exported.write_bytes(payload)
    independent = Schematic.load(str(exported))
    actual = {}
    for region in independent.regions.values():
        for position in region.block_positions():
            state = region[position]
            if state.id != "minecraft:air":
                world = (region.x + position[0], region.y + position[1], region.z + position[2])
                actual[world] = (state.id, dict(state.properties()))
    expected = {
        point: (cell.state.name, dict(cell.state.properties)) for point, cell in after.cells.items()
    }
    assert actual == expected
    assert report["revision"] == 5
    assert actual[(0, 0, 0)][1]["east"] == "true"
    assert actual[(1, 0, 0)][1]["west"] == "true"
    assert actual[(4, 1, 0)][1]["half"] == "upper"
