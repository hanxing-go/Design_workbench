import gzip
import io
import uuid
from pathlib import Path

import nbtlib
import pytest
from litemapy import Schematic

from design_workbench.adapters.formats.litematic import Litematic, region_bounds
from design_workbench.adapters.formats.painting_entities import read_painting_entity
from design_workbench.adapters.rendering.paintings import imported_paintings, painting_packet
from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.domain.models import BlockState, Bounds, Cell, Point, Scene
from design_workbench.domain.paintings import Painting
from design_workbench.domain.placement import FACES

VERSIONS = [
    ("1.20.1", 3465, False),
    ("1.21.4", 4189, False),
    ("1.21.5", 4325, True),
    ("26.1", 4786, True),
]
FACING = {"south": 0, "west": 1, "north": 2, "east": 3}


@pytest.mark.parametrize(("version", "data_version", "modern"), VERSIONS)
@pytest.mark.parametrize("face", FACING)
def test_painting_export_uses_selected_version_attachment_format(
    tmp_path: Path, version: str, data_version: int, modern: bool, face: str
) -> None:
    catalog = Catalog(version)
    stone = catalog.normalize(BlockState.make("stone"))
    normal = FACES[face]
    anchor: Point = (-10 + 3 * normal[0], -5, -10 + 3 * normal[2])
    painting = Painting(str(uuid.uuid4()), anchor, face, "match")
    scene = Scene(
        "test",
        "Painting NBT",
        version,
        data_version,
        0,
        Bounds((-32, -32, -32), (32, 32, 32)),
        {
            (x, y, z): Cell(stone)
            for x in range(-12, -7)
            for y in range(-7, -2)
            for z in range(-12, -7)
        },
        paintings=[painting],
    )
    formats = Litematic(catalog, version, data_version)
    payload, _ = formats.write(scene)
    # Inspect the serialized NBT independently of the workbench parser.
    document = nbtlib.File.parse(io.BytesIO(gzip.decompress(payload)))
    assert int(document["MinecraftDataVersion"]) == data_version
    region = next(iter(document["Regions"].values()))
    origin = tuple(int(region["Position"][axis]) for axis in "xyz")
    entity = region["Entities"][0]
    if modern:
        assert isinstance(entity["block_pos"], nbtlib.IntArray)
        assert len(entity["block_pos"]) == 3
        assert all("Tile" + axis not in entity for axis in "XYZ")
        local = [int(value) for value in entity["block_pos"]]
    else:
        assert "block_pos" not in entity
        assert all(isinstance(entity["Tile" + axis], nbtlib.Int) for axis in "XYZ")
        local = [int(entity["Tile" + axis]) for axis in "XYZ"]
    assert tuple(local[i] + origin[i] for i in range(3)) == anchor
    assert int(entity["facing"]) == FACING[face]
    target = tmp_path / "painting.litematic"
    target.write_bytes(payload)
    reference = next(iter(Schematic.load(str(target)).regions.values())).entities[0].data
    assert str(reference["variant"]) == "minecraft:match"
    assert ("block_pos" if modern else "TileX") in reference
    imported = imported_paintings(payload)[0]
    assert imported.anchor == anchor and imported.facing == face
    restored, _ = formats.read(payload)
    assert set(painting.positions()) <= restored.protected
    assert {
        tuple(point[i] - normal[i] for i in range(3)) for point in painting.positions()
    } <= restored.protected


def fixture_payload(data_version: int, entity: nbtlib.Compound) -> bytes:
    # A negative-size region verifies attachment coordinates are interpreted
    # relative to its normalized low corner, not its stored Position.
    region = nbtlib.Compound(
        {
            "Position": nbtlib.Compound(
                {"x": nbtlib.Int(-8), "y": nbtlib.Int(-3), "z": nbtlib.Int(-8)}
            ),
            "Size": nbtlib.Compound(
                {"x": nbtlib.Int(-5), "y": nbtlib.Int(-5), "z": nbtlib.Int(-5)}
            ),
            "BlockStatePalette": nbtlib.List[nbtlib.Compound](
                [nbtlib.Compound({"Name": nbtlib.String("minecraft:air")})]
            ),
            "BlockStates": nbtlib.LongArray([0, 0, 0, 0]),
            "Entities": nbtlib.List[nbtlib.Compound]([entity]),
            "TileEntities": nbtlib.List[nbtlib.Compound](),
        }
    )
    document = nbtlib.File(
        {
            "Version": nbtlib.Int(6),
            "MinecraftDataVersion": nbtlib.Int(data_version),
            "Metadata": nbtlib.Compound({"Name": nbtlib.String("Independent painting fixture")}),
            "Regions": nbtlib.Compound({"negative": region}),
        }
    )
    stream = io.BytesIO()
    document.write(stream)
    return gzip.compress(stream.getvalue())


@pytest.mark.parametrize(("version", "data_version", "modern"), VERSIONS)
@pytest.mark.parametrize("face", FACING)
def test_independent_painting_fixture_import_preview_and_protection(
    version: str, data_version: int, modern: bool, face: str
) -> None:
    entity = nbtlib.Compound(
        {
            "id": nbtlib.String("minecraft:painting"),
            "variant": nbtlib.String("minecraft:match"),
            "facing": nbtlib.Byte(FACING[face]),
        }
    )
    if modern:
        entity["block_pos"] = nbtlib.IntArray([2, 2, 2])
    else:
        for axis in "XYZ":
            entity["Tile" + axis] = nbtlib.Int(2)
    payload = fixture_payload(data_version, entity)
    expected = Painting("expected", (-10, -5, -10), face, "match")
    imported = imported_paintings(payload)
    assert len(imported) == 1
    assert imported[0].anchor == expected.anchor and imported[0].facing == face
    formats = Litematic(Catalog(version), version, data_version)
    scene, _ = formats.read(payload)
    preserved, _ = formats.write(scene, payload)
    preserved_root = nbtlib.File.parse(io.BytesIO(gzip.decompress(preserved)))
    assert preserved_root["Regions"]["negative"]["Entities"][0] == entity
    assert set(expected.positions()) <= scene.protected
    normal = FACES[face]
    assert {
        tuple(point[i] - normal[i] for i in range(3)) for point in expected.positions()
    } <= scene.protected
    packet = painting_packet(scene, payload)
    assert len(packet) == 1
    assert packet[0]["anchor"] == expected.anchor and packet[0]["protected"] is True
    centers = {
        "south": (-9, -4, -9.96875),
        "north": (-10, -4, -9.03125),
        "east": (-9.96875, -4, -10),
        "west": (-9.03125, -4, -9),
    }
    vertices = packet[0]["vertices"]
    center = [sum(vertices[axis::3]) / 4 for axis in range(3)]
    assert center == pytest.approx(
        [centers[face][axis] + normal[axis] * 0.001 for axis in range(3)]
    )


def test_modern_attachment_coordinates_take_precedence_over_legacy_fields() -> None:
    entry = nbtlib.Compound(
        {
            "id": nbtlib.String("minecraft:painting"),
            "variant": nbtlib.String("minecraft:match"),
            "facing": nbtlib.Byte(0),
            "block_pos": nbtlib.IntArray([2, 2, 2]),
            "TileX": nbtlib.Int(20),
            "TileY": nbtlib.Int(20),
            "TileZ": nbtlib.Int(20),
        }
    )
    payload = fixture_payload(4786, entry)
    document = nbtlib.File.parse(io.BytesIO(gzip.decompress(payload)))
    region = document["Regions"]["negative"]
    assert region_bounds(region).low == (-12, -7, -12)
    parsed = imported_paintings(payload)[0]
    assert parsed.anchor == (-10, -5, -10)
    scene, _ = Litematic(Catalog("26.1"), "26.1", 4786).read(payload)
    assert set(parsed.positions()) <= scene.protected
    assert (8, 13, 8) not in scene.protected


@pytest.mark.parametrize(
    "block_pos", [nbtlib.IntArray([1, 2]), nbtlib.List[nbtlib.Double]([1.2, 2, 3])]
)
def test_malformed_modern_attachment_is_not_misread_as_a_known_painting(
    block_pos: object,
) -> None:
    entry = {
        "id": "minecraft:painting",
        "variant": "minecraft:match",
        "block_pos": block_pos,
    }
    assert read_painting_entity(entry, (0, 0, 0), "invalid") is None
