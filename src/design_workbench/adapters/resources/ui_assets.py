"""Small UI projections made from the locally installed vanilla textures."""

from functools import lru_cache
from io import BytesIO
from math import sqrt
from pathlib import Path

from PIL import Image, ImageEnhance


@lru_cache(maxsize=128)
def ui_asset(directory: Path, name: str) -> bytes:
    root = directory / "assets/minecraft/textures"

    def texture(path: str) -> Image.Image:
        with Image.open(root / f"{path}.png") as source:
            # Animated textures are vertical strips; the UI uses their first frame.
            return source.convert("RGBA").crop((0, 0, source.width, source.width))

    if name.startswith("chest_") or name == "chest":
        sheet = texture("entity/chest/normal")
        parts = {
            "chest_front": (42, 33, 56, 43),
            "chest_side": (28, 33, 42, 43),
            "chest_top": (28, 0, 42, 14),
            "chest_lid_under": (14, 0, 28, 14),
            "chest_lid_front": (42, 14, 56, 19),
            "chest_lid_side": (28, 14, 42, 19),
            "chest_lock": (4, 1, 6, 5),
        }

        def chest_part(part: str) -> Image.Image:
            face = sheet.crop(parts[part])
            # ChestModel uses +Y up. Its UP quad is the second horizontal
            # square, and its front/lock are the SOUTH quads, not NORTH.
            if part == "chest_lid_under":
                # The downward-facing CSS quad rotates the opposite way.
                return face
            if part == "chest_top":
                return face.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            return face.transpose(Image.Transpose.ROTATE_180)

        if name in parts:
            image = chest_part(name)
        else:
            top = chest_part("chest_top")
            front = Image.new("RGBA", (14, 14))
            side = Image.new("RGBA", (14, 14))
            # Vanilla's 10-high body and 5-high lid overlap by one texel:
            # body y=0..10, lid y=9..14. Draw the lid over that shared row.
            front.paste(chest_part("chest_front"), (0, 4))
            front.paste(chest_part("chest_lid_front"), (0, 0))
            front.paste(chest_part("chest_lock"), (6, 3))
            side.paste(chest_part("chest_side"), (0, 4))
            side.paste(chest_part("chest_lid_side"), (0, 0))
            image = _isometric(top, front, side)
    elif name in {"grass_block", "crafting_table"}:
        if name == "grass_block":
            gray = texture("block/grass_block_top")
            # Vanilla's inventory tint: grass colormap at temperature=.5,
            # downfall=1.0 (127,127), independent of a world's biome.
            top = Image.new("RGBA", gray.size, "#7cbd6b")
            from PIL import ImageChops

            top = ImageChops.multiply(gray, top)
            front = texture("block/grass_block_side")
            overlay = texture("block/grass_block_side_overlay")
            tint = ImageChops.multiply(overlay, Image.new("RGBA", overlay.size, "#7cbd6b"))
            front.alpha_composite(tint)
            side = front
        else:
            top = texture("block/crafting_table_top")
            front = texture("block/crafting_table_front")
            side = texture("block/crafting_table_side")
        image = _isometric(top, front, side)
    else:
        image = texture(f"block/{name}")
        if name == "grass_block_side":
            from PIL import ImageChops

            overlay = texture("block/grass_block_side_overlay")
            tint = ImageChops.multiply(overlay, Image.new("RGBA", overlay.size, "#7cbd6b"))
            image.alpha_composite(tint)
        elif name in {"grass_block_top", "oak_leaves"}:
            from PIL import ImageChops

            tint_color = "#7cbd6b" if name == "grass_block_top" else "#91bd59"
            image = ImageChops.multiply(image, Image.new("RGBA", image.size, tint_color))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _isometric(top: Image.Image, front: Image.Image, side: Image.Image) -> Image.Image:
    canvas = Image.new("RGBA", (64, 72))
    # Vanilla block/block's GUI rotation is [30, 225, 0]. A cube at that
    # angle is taller than it is wide. Keep the original face texels;
    # shrinking 16px textures to 14px dropped crafting-grid/grass detail.
    half_width, half_top, edge_height = 30, 15, 30 * sqrt(1.5)
    for index, (source, brightness) in enumerate(((top, 1.0), (front, 0.85), (side, 0.65))):
        width, height = source.size
        if index == 0:
            matrix = (
                width / (2 * half_width),
                height / (2 * half_top),
                -32 * width / (2 * half_width) - 2 * height / (2 * half_top),
                -width / (2 * half_width),
                height / (2 * half_top),
                32 * width / (2 * half_width) - 2 * height / (2 * half_top),
            )
        else:
            left = 2 if index == 1 else 32
            upper = 17 if index == 1 else 32
            slope = -0.5 if index == 1 else 0.5
            matrix = (
                width / half_width,
                0,
                -left * width / half_width,
                slope * height / edge_height,
                height / edge_height,
                (-upper - slope * left) * height / edge_height,
            )
        source = ImageEnhance.Brightness(source).enhance(brightness)
        projected = source.transform(
            canvas.size, Image.Transform.AFFINE, matrix, Image.Resampling.NEAREST
        )
        canvas.alpha_composite(projected)
    return canvas
