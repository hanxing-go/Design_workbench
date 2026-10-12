from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from design_workbench.adapters.resources import ui_assets
from design_workbench.adapters.resources.ui_assets import ui_asset


def test_projection_keeps_original_faces_and_lighting(tmp_path: Path) -> None:
    root = tmp_path / "assets/minecraft/textures/block"
    root.mkdir(parents=True)
    for name, color in [
        ("crafting_table_top", "red"),
        ("crafting_table_front", "lime"),
        ("crafting_table_side", "blue"),
    ]:
        Image.new("RGBA", (16, 16), color).save(root / f"{name}.png")
    image = Image.open(BytesIO(ui_asset(tmp_path, "crafting_table")))
    assert image.size == (64, 72)
    assert image.getpixel((32, 16)) == (255, 0, 0, 255)
    assert image.getpixel((18, 36)) == (0, 216, 0, 255)
    assert image.getpixel((46, 36)) == (0, 0, 165, 255)
    assert image.getpixel((0, 0))[3] == 0


def test_animated_texture_uses_first_frame(tmp_path: Path) -> None:
    root = tmp_path / "assets/minecraft/textures/block"
    root.mkdir(parents=True)
    strip = Image.new("RGBA", (16, 32), "red")
    strip.paste(Image.new("RGBA", (16, 16), "blue"), (0, 16))
    strip.save(root / "water_still.png")
    image = Image.open(BytesIO(ui_asset(tmp_path, "water_still")))
    assert image.size == (16, 16)
    assert image.getpixel((8, 15)) == (255, 0, 0, 255)


def test_grass_inventory_tint_preserves_untinted_dirt(tmp_path: Path) -> None:
    root = tmp_path / "assets/minecraft/textures/block"
    root.mkdir(parents=True)
    Image.new("RGBA", (16, 16), "white").save(root / "grass_block_top.png")
    Image.new("RGBA", (16, 16), "#804020").save(root / "grass_block_side.png")
    overlay = Image.new("RGBA", (16, 16))
    overlay.paste("white", (0, 0, 16, 4))
    overlay.save(root / "grass_block_side_overlay.png")
    top = Image.open(BytesIO(ui_asset(tmp_path, "grass_block_top")))
    side = Image.open(BytesIO(ui_asset(tmp_path, "grass_block_side")))
    assert top.getpixel((8, 8)) == (124, 189, 107, 255)
    assert side.getpixel((8, 2)) == (124, 189, 107, 255)
    assert side.getpixel((8, 12)) == (128, 64, 32, 255)


def _write_chest_atlas(directory: Path) -> Image.Image:
    root = directory / "assets/minecraft/textures/entity/chest"
    root.mkdir(parents=True)
    atlas = Image.new("RGBA", (64, 64))
    for y in range(64):
        for x in range(64):
            atlas.putpixel((x, y), (x * 3, y * 3, 90, 255))
    atlas.save(root / "normal.png")
    return atlas


@pytest.mark.parametrize(
    ("name", "size", "top_left", "bottom_right"),
    [
        ("chest_top", (14, 14), (28, 13), (41, 0)),
        ("chest_lid_under", (14, 14), (14, 0), (27, 13)),
        ("chest_front", (14, 10), (55, 42), (42, 33)),
        ("chest_side", (14, 10), (41, 42), (28, 33)),
        ("chest_lid_front", (14, 5), (55, 18), (42, 14)),
        ("chest_lid_side", (14, 5), (41, 18), (28, 14)),
        ("chest_lock", (2, 4), (5, 4), (4, 1)),
    ],
)
def test_chest_uses_outside_quads_in_upright_orientation(
    tmp_path: Path,
    name: str,
    size: tuple[int, int],
    top_left: tuple[int, int],
    bottom_right: tuple[int, int],
) -> None:
    atlas = _write_chest_atlas(tmp_path)
    image = Image.open(BytesIO(ui_asset(tmp_path, name)))
    assert image.size == size
    assert image.getpixel((0, 0)) == atlas.getpixel(top_left)
    assert image.getpixel((size[0] - 1, size[1] - 1)) == atlas.getpixel(bottom_right)


def test_closed_chest_preserves_lid_overlap_and_centered_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    atlas = _write_chest_atlas(tmp_path)
    faces: list[Image.Image] = []

    def capture_faces(top: Image.Image, front: Image.Image, side: Image.Image) -> Image.Image:
        faces.extend([top, front, side])
        return front

    monkeypatch.setattr(ui_assets, "_isometric", capture_faces)
    ui_asset(tmp_path, "chest")
    top, front, side = faces
    assert top.size == front.size == side.size == (14, 14)
    assert top.getpixel((0, 0)) == atlas.getpixel((28, 13))
    # The fifth lid row covers the first body row; the body keeps nine rows.
    assert front.getpixel((2, 4)) == atlas.getpixel((53, 14))
    assert front.getpixel((2, 5)) == atlas.getpixel((53, 41))
    assert front.getpixel((2, 13)) == atlas.getpixel((53, 33))
    assert side.getpixel((2, 4)) == atlas.getpixel((39, 14))
    assert side.getpixel((2, 5)) == atlas.getpixel((39, 41))
    assert side.getpixel((2, 13)) == atlas.getpixel((39, 33))
    # The four-high lock starts three texels below the lid top and crosses
    # the seam; it is a separate lid child on the animated chest.
    assert front.getpixel((6, 3)) == atlas.getpixel((5, 4))
    assert front.getpixel((7, 6)) == atlas.getpixel((4, 1))
    assert front.getpixel((6, 7)) == atlas.getpixel((49, 39))
