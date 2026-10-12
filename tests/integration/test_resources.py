import shutil
from pathlib import Path

import pytest

from design_workbench.adapters.rendering.packets import render_packet
from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.adapters.resources.pack import ResourceManager
from design_workbench.application.scenes import SceneService
from design_workbench.domain.models import BlockState, Cell

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
    shutil.copytree(original / catalog.version, relocated / catalog.version)
    pack = ResourceManager(relocated).active(catalog.version)
    assert pack is not None
    assert pack.directory.is_relative_to(relocated)
    assert pack.geometry(catalog.default("oak_stairs"))["status"] == "static"
    assert (pack.directory / "atlas.png").is_file()
    assert pack.language["block.minecraft.oak_stairs"] == "橡木楼梯"


@pytest.mark.resources
def test_piston_head_and_wood_edge_in_all_six_directions(catalog: Catalog) -> None:
    pack = ResourceManager(ROOT / ".local/cache/resources").active(catalog.version)
    assert pack is not None
    for name in ("piston", "sticky_piston", "piston_head"):
        for direction, axis, edge in (
            ("up", 1, 1),
            ("down", 1, 0),
            ("north", 2, 0),
            ("south", 2, 1),
            ("east", 0, 1),
            ("west", 0, 0),
        ):
            state = catalog.normalize(BlockState.make(name, {"facing": direction}))
            faces = pack.geometry(state)["faces"]
            head = next(
                f for f in faces if f["texture"].endswith(("piston_top", "piston_top_sticky"))
            )
            assert all(v == edge for v in head["vertices"][axis::3]), (name, direction, head)
            if name != "piston_head":
                for face in (f for f in faces if f["texture"].endswith("piston_side")):
                    for i in range(4):
                        if face["uv"][2 * i + 1] == 0:
                            assert face["vertices"][3 * i + axis] == edge, (direction, face)


@pytest.mark.resources
def test_special_textures_translucency_and_neighbour_invalidation(
    catalog: Catalog, service: SceneService
) -> None:
    pack = ResourceManager(ROOT / ".local/cache/resources").active(catalog.version)
    assert pack is not None
    for name in (
        "water",
        "lava",
        "oak_sign",
        "oak_wall_sign",
        "oak_hanging_sign",
        "oak_wall_hanging_sign",
        "blue_bed",
    ):
        model = pack.geometry(catalog.default(name))
        assert model["status"] == "static" and model["faces"]
        assert all(f["texture"] in pack.atlas["uv"] for f in model["faces"])
    for name in ("blue_stained_glass", "yellow_stained_glass", "blue_stained_glass_pane"):
        assert pack.geometry(catalog.default(name))["render_layer"] == "translucent"
    assert pack.atlas["uv"]["minecraft:entity/signs/oak"][2:] == [64, 32]
    assert pack.atlas["uv"]["minecraft:entity/bed/red"][2:] == [64, 64]
    scene = service.repository.load()
    scene.cells[(15, 0, 0)] = Cell(catalog.default("water"), "main", "design")
    scene.cells[(16, 0, 0)] = Cell(catalog.default("water"), "main", "design")
    first = render_packet(scene, catalog, pack)
    assert not first["warnings"]
    assert not render_packet(scene, catalog, pack, first["chunk_versions"])["chunks"]
    scene.cells[(16, 0, 0)] = Cell(
        catalog.normalize(BlockState.make("water", {"level": "7"})), "main", "design"
    )
    second = render_packet(scene, catalog, pack, first["chunk_versions"])
    assert set(second["chunks"]) == {"0,0,0", "1,0,0"}
