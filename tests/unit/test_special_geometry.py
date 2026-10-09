import json
from pathlib import Path

import nbtlib
import pytest
from PIL import Image

from design_workbench.adapters.rendering.fluids import fluid_model
from design_workbench.adapters.rendering.signs import sign_texts
from design_workbench.adapters.resources.atlas import RECIPE_VERSION, build_atlas
from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.adapters.resources.geometry import default_uv
from design_workbench.adapters.resources.pack import ResourceManager
from design_workbench.adapters.resources.special import special_geometry
from design_workbench.application.contracts import EditRequest, HistoryRequest
from design_workbench.application.scenes import SceneService, fingerprint
from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.models import BlockState, Cell


def test_asymmetric_face_uv_bounds() -> None:
    low, high = [1.0, 2.0, 3.0], [5.0, 7.0, 11.0]
    assert default_uv(low, high, "north") == [11, 9, 15, 14]
    assert default_uv(low, high, "east") == [5, 9, 13, 14]
    assert default_uv(low, high, "down") == [1, 5, 5, 13]


def test_all_bed_parts_have_correct_extent_and_entity_texture(catalog: Catalog) -> None:
    for name in catalog.blocks:
        if not name.endswith("_bed"):
            continue
        for state in catalog.states(name):
            model = special_geometry(state)
            assert model is not None and len(model["faces"]) == 18
            points = [f["vertices"] for f in model["faces"]]
            for axis in range(3):
                values = [v for p in points for v in p[axis::3]]
                assert min(values) == 0
                assert max(values) == (0.5625 if axis == 1 else 1)
            assert model["faces"][0]["texture"] == name.replace(
                "minecraft:", "minecraft:entity/bed/"
            ).removesuffix("_bed")


def test_every_sign_variant_and_fluid_level_has_geometry(catalog: Catalog) -> None:
    for name in catalog.blocks:
        if not (name.endswith("_sign") or name in {"minecraft:water", "minecraft:lava"}):
            continue
        for state in catalog.states(name):
            model = special_geometry(state)
            assert model is not None and model["faces"]
            assert model["opaque_cube"] is False
            assert all(
                len(face["vertices"]) == 12 and len(face["uv"]) == 8 for face in model["faces"]
            )
    for level in range(16):
        model = special_geometry(catalog.normalize(BlockState.make("water", {"level": str(level)})))
        assert model is not None
        maximum = max(v for f in model["faces"] for v in f["vertices"][1::3])
        assert maximum == pytest.approx((8 - level % 8) / 9 if level < 8 else 8 / 9)


def test_fluid_corner_continuity_and_stack(service: SceneService, catalog: Catalog) -> None:
    scene = service.repository.load()
    source = catalog.default("water")
    flowing = catalog.normalize(BlockState.make("water", {"level": "5"}))
    scene.cells = {
        (0, 0, 0): Cell(source, "main", "design"),
        (1, 0, 0): Cell(flowing, "main", "design"),
    }
    a, b = [fluid_model(scene, point, scene.cells[point].state, catalog) for point in scene.cells]
    # Shared top-edge corners coincide, despite different liquid levels.
    av = a["faces"][0]["vertices"]
    bv = b["faces"][0]["vertices"]
    assert av[4] == bv[1] and av[7] == bv[10]
    scene.cells[(0, 1, 0)] = Cell(source, "main", "design")
    assert all(
        v == 1 for v in fluid_model(scene, (0, 0, 0), source, catalog)["faces"][0]["vertices"][1::3]
    )


def test_atlas_rectangular_entity_and_declared_first_animation_frame(tmp_path: Path) -> None:
    root = tmp_path / "assets/minecraft/textures"
    (root / "block").mkdir(parents=True)
    (root / "entity/signs").mkdir(parents=True)
    Image.new("RGBA", (64, 32), (30, 60, 90, 255)).save(root / "entity/signs/oak.png")
    strip = Image.new("RGBA", (16, 32), (255, 0, 0, 255))
    strip.paste((0, 0, 255, 255), (0, 16, 16, 32))
    strip.save(root / "block/water_still.png")
    (root / "block/water_still.png.mcmeta").write_text('{"animation":{"frames":[1,0]}}')
    data = build_atlas(tmp_path)
    assert data["uv"]["minecraft:entity/signs/oak"][2:] == [64, 32]
    assert data["uv"]["minecraft:block/water_still"][2:] == [16, 16]
    with Image.open(tmp_path / "atlas.png") as atlas:
        x, y, _, _ = data["uv"]["minecraft:block/water_still"]
        assert atlas.getpixel((x, y)) == (0, 0, 255, 255)
    (tmp_path / "zh_cn.json").write_text("{}")
    manifest = {
        "sha256": "jar",
        "language_sha256": "lang",
        "bundle_hash": "old",
        "recipe_version": 1,
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    cache = tmp_path / "cache"
    (cache / "1.20.1").mkdir(parents=True)
    # A portable old pack is upgraded from extracted assets, without the original JAR.
    import shutil

    shutil.copytree(tmp_path / "assets", cache / "1.20.1/old/assets")
    for name in ("zh_cn.json", "manifest.json", "atlas.png", "atlas.json"):
        shutil.copy2(tmp_path / name, cache / "1.20.1/old" / name)
    pointer = cache / "1.20.1/current.json"
    pointer.write_text('{"directory":"old"}')
    before = (cache / "1.20.1/old/manifest.json").read_bytes()
    manager = ResourceManager(cache)
    pack = manager.active("1.20.1")
    assert pack is not None and pack.manifest["recipe_version"] == RECIPE_VERSION
    assert pack.directory.name != "old"
    assert manager.active("1.20.1").directory == pack.directory  # type: ignore[union-attr]
    assert (cache / "1.20.1/old/manifest.json").read_bytes() == before


def test_atomic_bed_placement_collision_undo_and_bounds(service: SceneService) -> None:
    def request(position: list[int], revision: int, request_id: str) -> EditRequest:
        return EditRequest.model_validate(
            {
                "expected_revision": revision,
                "request_id": request_id,
                "operations": [
                    {
                        "op": "set",
                        "complete_beds": True,
                        "blocks": [
                            {
                                "position": position,
                                "state": {
                                    "name": "red_bed",
                                    "properties": {"part": "foot", "facing": "north"},
                                },
                            }
                        ],
                    }
                ],
            }
        )

    result = service.edit(request([0, 0, 0], 0, "bed"))
    assert result["changed"] == 2
    scene = service.repository.load()
    assert dict(scene.cells[(0, 0, -1)].state.properties)["part"] == "head"
    with pytest.raises(WorkbenchError, match="两格位置必须为空"):
        service.edit(request([0, 0, 1], 1, "overlap"))
    assert service.repository.load().revision == 1
    service.history("undo", HistoryRequest(expected_revision=1, request_id="undo-bed"))
    assert service.summary()["blocks"] == 0
    with pytest.raises(WorkbenchError, match="超出工作区"):
        service.edit(request([0, 0, -128], 2, "out"))
    assert service.summary()["blocks"] == 0


def test_imported_sign_text_projection_preserves_source() -> None:
    import io

    root = nbtlib.File(
        {
            "Version": nbtlib.Int(6),
            "MinecraftDataVersion": nbtlib.Int(3465),
            "Regions": nbtlib.Compound(
                {
                    "negative": nbtlib.Compound(
                        {
                            "Position": nbtlib.Compound(
                                {"x": nbtlib.Int(10), "y": nbtlib.Int(0), "z": nbtlib.Int(0)}
                            ),
                            "Size": nbtlib.Compound(
                                {"x": nbtlib.Int(-3), "y": nbtlib.Int(1), "z": nbtlib.Int(1)}
                            ),
                            "TileEntities": nbtlib.List[nbtlib.Compound](
                                [
                                    nbtlib.Compound(
                                        {
                                            "id": nbtlib.String("minecraft:sign"),
                                            "x": nbtlib.Int(1),
                                            "y": nbtlib.Int(0),
                                            "z": nbtlib.Int(0),
                                            "front_text": nbtlib.Compound(
                                                {
                                                    "messages": nbtlib.List[nbtlib.String](
                                                        [
                                                            nbtlib.String(
                                                                '{"text":"你好","extra":[{"text":"世界"}]}'
                                                            )
                                                        ]
                                                    ),
                                                    "color": nbtlib.String("red"),
                                                }
                                            ),
                                            "back_text": nbtlib.Compound(
                                                {
                                                    "messages": nbtlib.List[nbtlib.String](
                                                        [nbtlib.String('"Back"')]
                                                    )
                                                }
                                            ),
                                        }
                                    )
                                ]
                            ),
                        }
                    )
                }
            ),
        }
    )
    stream = io.BytesIO()
    root.write(stream)
    payload = stream.getvalue()
    text = sign_texts(payload)[(9, 0, 0)]
    assert text[0]["lines"] == ["你好世界"] and text[1]["lines"] == ["Back"]
    assert text[0]["color"] == "red"
    assert stream.getvalue() == payload


def test_legacy_set_request_remains_replayable(service: SceneService) -> None:
    request = EditRequest.model_validate(
        {
            "expected_revision": 0,
            "request_id": "legacy",
            "operations": [
                {"op": "set", "blocks": [{"position": [0, 0, 0], "state": {"name": "stone"}}]}
            ],
        }
    )
    legacy_body = request.model_dump(mode="json", exclude_none=True, by_alias=True)
    legacy_body["operations"][0].pop("complete_beds")
    scene = service.repository.load()
    plan = service.editor.plan(scene, legacy_body["operations"])
    scene.cells = plan.cells
    result = service.repository.commit(
        scene, plan.changes, 0, "legacy", fingerprint("edit", legacy_body)
    )
    assert service.edit(request) == result
    assert service.summary()["revision"] == 1
