import math

import pytest

from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.models import BlockState


def test_registry_cardinality_and_all_property_combinations(catalog: Catalog) -> None:
    actual = catalog.document["blocks"]
    assert len({block["name"] for block in actual}) == len(actual)
    for block in actual:
        names = catalog.describe(block["name"])["properties"]
        assert (
            math.prod(len(values) for values in names.values())
            == block["maxStateId"] - block["minStateId"] + 1
        )
        for state in catalog.states(block["name"]):
            assert catalog.normalize(state) == state
    collected = []
    for offset in range(0, len(actual), 37):
        collected.extend(item["name"] for item in catalog.search(offset=offset, limit=37)["items"])
    assert len(collected) == len(set(collected)) == len(actual)


def test_default_direction_and_hallucinations(catalog: Catalog) -> None:
    assert dict(catalog.default("oak_stairs").properties) == {
        "facing": "north",
        "half": "bottom",
        "shape": "straight",
        "waterlogged": "false",
    }
    with pytest.raises(WorkbenchError, match="没有方块"):
        catalog.default("diamond_roof")
    with pytest.raises(WorkbenchError, match="非法"):
        catalog.normalize(BlockState.make("oak_stairs", {"facing": "up"}))
    with pytest.raises(WorkbenchError, match="非法"):
        catalog.normalize(BlockState.make("stone", {"imaginary": "yes"}))
