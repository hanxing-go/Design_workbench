import gzip
import io
from pathlib import Path

import nbtlib
import pytest
from litemapy import BlockState as ReferenceState
from litemapy import Region, Schematic

from design_workbench.adapters.formats.litematic import Litematic
from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.domain.editing import EditLimits, Editor
from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.models import BlockState, Bounds, Cell, Scene


def test_independently_authored_multiregion_negative_size_and_air(
    tmp_path: Path, catalog: Catalog
) -> None:
    region = Region(4, 0, 6, -5, 3, -7)
    names = list(catalog.blocks)[1:80]
    for index in range(70):
        x, y, z = -(index % 5), index // 35, -(index // 5 % 7)
        region[x, y, z] = ReferenceState(names[index])
    second = Region(-9, 4, -9, 3, 1, 1)
    second[0, 0, 0] = ReferenceState(
        "minecraft:oak_stairs", facing="east", half="top", shape="inner_left", waterlogged="false"
    )
    second[1, 0, 0] = ReferenceState("minecraft:cave_air")
    schematic = Schematic(
        name="独立样例", regions={"negative": region, "second": second}, mc_version=3465
    )
    path = tmp_path / "reference.litematic"
    schematic.save(str(path))
    adapter = Litematic(catalog)
    scene, report = adapter.read(path.read_bytes())
    assert report["regions"] == 2
    assert scene.cells[(-9, 4, -9)].state == catalog.normalize(
        BlockState.make("oak_stairs", {"facing": "east", "half": "top", "shape": "inner_left"})
    )
    assert scene.cells[(-8, 4, -9)].state.name == "minecraft:cave_air"
    export, _ = adapter.write(scene, path.read_bytes())
    out = tmp_path / "out.litematic"
    out.write_bytes(export)
    reread = Schematic.load(str(out))
    for name, original in schematic.regions.items():
        result = reread.regions[name]
        for position in original.block_positions():
            assert dict(result[position].properties()) == dict(original[position].properties())
            assert result[position].id == original[position].id


def test_unknown_nbt_and_long_types_preserved(tmp_path: Path, catalog: Catalog) -> None:
    adapter = Litematic(catalog)
    state = catalog.default("oak_sign")
    scene = Scene(
        "id", "测试", "1.20.1", 3465, 0, Bounds((0, 0, 0), (3, 3, 3)), {(0, 0, 0): Cell(state)}
    )
    payload, _ = adapter.write(scene)
    root = nbtlib.File.parse(io.BytesIO(gzip.decompress(payload)))
    region = next(iter(root["Regions"].values()))
    region["CustomTag"] = nbtlib.Compound(
        {"very_large": nbtlib.Long((1 << 62) + 123), "bytes": nbtlib.ByteArray([1, 2, -3])}
    )
    sign = nbtlib.Compound(
        {
            "x": nbtlib.Int(0),
            "y": nbtlib.Int(0),
            "z": nbtlib.Int(0),
            "id": nbtlib.String("minecraft:sign"),
            "front_text": nbtlib.Compound({"messages": nbtlib.List[nbtlib.String](["测试文字"])}),
        }
    )
    region["TileEntities"].append(sign)
    root["UnknownRoot"] = nbtlib.Short(17)
    stream = io.BytesIO()
    root.write(stream)
    source = gzip.compress(stream.getvalue())
    imported, report = adapter.read(source)
    assert imported.protected == {(0, 0, 0)}
    assert report["unknown_region_tags"] == {"Design": ["CustomTag"]}
    export, report = adapter.write(imported, source)
    final = nbtlib.File.parse(io.BytesIO(gzip.decompress(export)))
    final_region = next(iter(final["Regions"].values()))
    assert final["UnknownRoot"] == root["UnknownRoot"]
    assert final_region["CustomTag"] == region["CustomTag"]
    assert final_region["TileEntities"] == region["TileEntities"]
    assert report["losses"] == []


def test_version_and_truncation_rejected(catalog: Catalog) -> None:
    adapter = Litematic(catalog)
    with pytest.raises(WorkbenchError):
        adapter.read(b"broken")
    scene = Scene("id", "empty", "1.20.1", 3465, 0, Bounds((0, 0, 0), (1, 1, 1)))
    payload, _ = adapter.write(scene)
    root = adapter.parse(payload)
    root["MinecraftDataVersion"] = nbtlib.Int(3955)
    stream = io.BytesIO()
    root.write(stream)
    with pytest.raises(WorkbenchError) as error:
        adapter.read(gzip.compress(stream.getvalue()))
    assert error.value.code == "VERSION_MISMATCH"


def test_deleted_special_air_and_move_between_regions(tmp_path: Path, catalog: Catalog) -> None:
    left, right = Region(0, 0, 0, 3, 1, 1), Region(5, 0, 0, 3, 1, 1)
    left[0, 0, 0] = ReferenceState("minecraft:stone")
    left[1, 0, 0] = ReferenceState("minecraft:cave_air")
    left[2, 0, 0] = ReferenceState("minecraft:void_air")
    path = tmp_path / "source.litematic"
    Schematic(regions={"left": left, "right": right}, mc_version=3465).save(str(path))
    source = path.read_bytes()
    adapter = Litematic(catalog)
    scene, _ = adapter.read(source)
    plan = Editor(catalog, EditLimits()).plan(
        scene,
        [
            {"op": "delete", "selector": {"name": "cave_air"}},
            {"op": "transform", "selector": {"name": "stone"}, "offset": [5, 0, 0]},
        ],
    )
    scene.cells = plan.cells
    exported, report = adapter.write(scene, source)
    path.write_bytes(exported)
    reference = Schematic.load(str(path))
    assert report["regions"] == 2
    assert reference.regions["left"][0, 0, 0].id == "minecraft:air"
    assert reference.regions["left"][1, 0, 0].id == "minecraft:air"
    assert reference.regions["left"][2, 0, 0].id == "minecraft:void_air"
    assert reference.regions["right"][0, 0, 0].id == "minecraft:stone"


def test_ambiguous_region_air_and_extension_overlap_rejected(
    tmp_path: Path, catalog: Catalog
) -> None:
    adapter = Litematic(catalog)
    path = tmp_path / "overlap.litematic"
    Schematic(
        regions={"first": Region(0, 0, 0, 3, 1, 1), "second": Region(2, 0, 0, 3, 1, 1)},
        mc_version=3465,
    ).save(str(path))
    with pytest.raises(WorkbenchError) as error:
        adapter.read(path.read_bytes())
    assert error.value.code == "REGION_OVERLAP"
    Schematic(regions={"first": Region(0, 0, 0, 3, 1, 1)}, mc_version=3465).save(str(path))
    source = path.read_bytes()
    scene, _ = adapter.read(source)
    scene.cells.update(
        {(-1, 0, 0): Cell(catalog.default("stone")), (3, 0, 0): Cell(catalog.default("stone"))}
    )
    with pytest.raises(WorkbenchError) as error:
        adapter.write(scene, source)
    assert error.value.code == "EXPORT_REGION_OVERLAP"


def test_entity_links_and_unknown_region_protect_edits(tmp_path: Path, catalog: Catalog) -> None:
    path = tmp_path / "entities.litematic"
    region = Region(7, 3, -5, 3, 2, 2)
    region[0, 0, 0] = ReferenceState("minecraft:oak_sign", rotation="0", waterlogged="false")
    Schematic(regions={"main": region}, mc_version=3465).save(str(path))
    adapter = Litematic(catalog)
    root = adapter.parse(path.read_bytes())
    region_nbt = root["Regions"]["main"]
    region_nbt["TileEntities"].append(
        nbtlib.Compound(
            {
                "x": nbtlib.Int(0),
                "y": nbtlib.Int(0),
                "z": nbtlib.Int(0),
                "id": nbtlib.String("minecraft:sign"),
            }
        )
    )
    region_nbt["Entities"].append(
        nbtlib.Compound(
            {
                "id": nbtlib.String("minecraft:armor_stand"),
                "Pos": nbtlib.List[nbtlib.Double]([1.5, 0, 0.5]),
            }
        )
    )
    stream = io.BytesIO()
    root.write(stream)
    source = gzip.compress(stream.getvalue())
    scene, _ = adapter.read(source)
    assert scene.protected == {(7, 3, -5), (8, 3, -5)}
    editor = Editor(catalog, EditLimits())
    for operations in (
        [{"op": "replace", "selector": {}, "state": {"name": "stone"}}],
        [{"op": "transform", "selector": {}, "offset": [1, 0, 0]}],
        [{"op": "set", "blocks": [{"position": [8, 3, -5], "state": {"name": "stone"}}]}],
    ):
        with pytest.raises(WorkbenchError) as error:
            editor.plan(scene, operations)
        assert error.value.code == "PROTECTED_CONTENT"
    payload, _ = adapter.write(scene, source)
    final = adapter.parse(payload)["Regions"]["main"]
    assert final["TileEntities"] == region_nbt["TileEntities"]
    assert final["Entities"] == region_nbt["Entities"]
    region_nbt["UnknownCoordinates"] = nbtlib.IntArray([0, 1, 2])
    stream = io.BytesIO()
    root.write(stream)
    scene, _ = adapter.read(gzip.compress(stream.getvalue()))
    assert len(scene.protected) == 12
