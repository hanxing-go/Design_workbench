from pathlib import Path

import pytest

from design_workbench.adapters.rendering.cache import RenderCache
from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.adapters.resources.pack import ResourceManager
from design_workbench.adapters.resources.special import CHEST_TEXTURES, HEAD_TEXTURES
from design_workbench.adapters.storage.sqlite import SqliteStore
from design_workbench.application.contracts import EditRequest
from design_workbench.application.scenes import SceneService

ROOT = Path(__file__).parents[2]


@pytest.mark.resources
@pytest.mark.parametrize("version", ["1.20.1", "26.1"])
def test_official_entity_models_resolve_all_textures_and_states(version: str) -> None:
    catalog = Catalog(version)
    pack = ResourceManager(ROOT / ".local/cache/resources").active(version)
    assert pack is not None, "资源测试需要 resources setup；未配置不能视为通过。"
    for name in catalog.blocks:
        if not (
            name.split(":", 1)[1].replace("_wall_", "_") in HEAD_TEXTURES
            or name.split(":", 1)[1].removeprefix("waxed_") in CHEST_TEXTURES
            or name.endswith(("_banner", "_shulker_box"))
            or name
            in {
                "minecraft:chest",
                "minecraft:trapped_chest",
                "minecraft:ender_chest",
                "minecraft:shulker_box",
                "minecraft:conduit",
                "minecraft:decorated_pot",
                "minecraft:bubble_column",
            }
        ):
            continue
        for state in catalog.states(name):
            model = pack.geometry(state)
            assert model["status"] == "static" and model["faces"], (state, model)
            assert all(face["texture"] in pack.atlas["uv"] for face in model["faces"])
    assert "自定义皮肤" in pack.support(catalog.default("player_head"))["reason"]
    assert "自定义图案" in pack.support(catalog.default("red_banner"))["reason"]
    for name in ("moving_piston", "end_portal", "end_gateway"):
        assert pack.support(catalog.default(name)) == {
            "status": "special",
            "reason": "暂不支持预览；方块状态可保存",
        }


@pytest.mark.resources
def test_bubble_column_neighbour_change_invalidates_render_cache(
    service: SceneService, catalog: Catalog
) -> None:
    pack = ResourceManager(ROOT / ".local/cache/resources").active(catalog.version)
    assert pack is not None
    assert isinstance(service.repository, SqliteStore)
    service.edit(
        EditRequest.model_validate(
            {
                "expected_revision": 0,
                "request_id": "bubbles",
                "operations": [
                    {
                        "op": "set",
                        "blocks": [
                            {"position": [15, 0, 0], "state": {"name": "bubble_column"}},
                            {"position": [16, 0, 0], "state": {"name": "water"}},
                        ],
                    }
                ],
            }
        )
    )
    cache = RenderCache()
    try:
        initial = cache.render(service.repository.path, catalog, pack)
        assert not cache.render(service.repository.path, catalog, pack, initial["chunk_versions"])[
            "chunks"
        ]
        service.edit(
            EditRequest.model_validate(
                {
                    "expected_revision": 1,
                    "request_id": "replace-water",
                    "operations": [
                        {
                            "op": "set",
                            "blocks": [{"position": [16, 0, 0], "state": {"name": "stone"}}],
                        }
                    ],
                }
            )
        )
        updated = cache.render(service.repository.path, catalog, pack, initial["chunk_versions"])
        assert set(updated["chunks"]) == {"0,0,0", "1,0,0"}
        assert initial["chunks"]["0,0,0"][0][3] != updated["chunks"]["0,0,0"][0][3]
    finally:
        cache.close()
