import shutil
from pathlib import Path

import pytest

from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.adapters.resources.pack import ResourceManager

ROOT = Path(__file__).parents[2]


@pytest.mark.resources
def test_official_pack_all_states_and_representative_models(catalog: Catalog) -> None:
    pack = ResourceManager(ROOT / ".local/cache/resources").active(catalog.version)
    if pack is None:
        pytest.fail("资源测试需要 resources setup；未配置不能视为通过。")
    assert pack.manifest["data_version"] == catalog.data_version
    catalog.language = pack.language
    assert catalog.search("橡木楼梯")["total"] >= 1
    for name in catalog.blocks:
        for state in catalog.states(name):
            result = pack.support(state)
            assert result["status"] != "missing", (state, result)
    for name in (
        "oak_planks",
        "oak_stairs",
        "oak_slab",
        "glass",
        "oak_door",
        "oak_trapdoor",
        "oak_fence",
        "cobblestone_wall",
        "poppy",
    ):
        geometry = pack.geometry(catalog.default(name))
        assert geometry["status"] == "static"
        assert geometry["faces"]
        assert all(face["texture"] in pack.atlas["uv"] for face in geometry["faces"])
    slab = pack.geometry(catalog.default("oak_slab"))
    assert (
        max(
            face["vertices"][i]
            for face in slab["faces"]
            for i in range(1, len(face["vertices"]), 3)
        )
        == 0.5
    )


@pytest.mark.resources
def test_resource_cache_moved_to_clean_path(tmp_path: Path, catalog: Catalog) -> None:
    original = ROOT / ".local/cache/resources"
    relocated = tmp_path / "portable/resources"
    shutil.copytree(original, relocated)
    pack = ResourceManager(relocated).active(catalog.version)
    assert pack is not None
    assert pack.directory.is_relative_to(relocated)
    assert pack.geometry(catalog.default("oak_stairs"))["status"] == "static"
    assert (pack.directory / "atlas.png").is_file()
    assert pack.language["block.minecraft.oak_stairs"] == "橡木楼梯"
