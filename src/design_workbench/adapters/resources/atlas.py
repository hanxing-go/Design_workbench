"""Build a padded atlas without treating rectangular entity sheets as animations."""

import json
import math
from pathlib import Path
from typing import Any

RECIPE_VERSION = 5


def build_atlas(directory: Path) -> dict[str, Any]:
    from PIL import Image

    textures: list[tuple[str, Any]] = []
    assets = directory / "assets"
    files = sorted(
        {
            p
            for pattern in (
                "*/textures/block/**/*.png",
                "*/textures/entity/bed/*.png",
                "*/textures/entity/signs/**/*.png",
                "*/textures/entity/chest/*.png",
                "*/textures/entity/shulker/*.png",
                "*/textures/entity/banner_base.png",
                "*/textures/entity/banner/base.png",
                "*/textures/entity/banner/banner_base.png",
                "*/textures/entity/skeleton/skeleton.png",
                "*/textures/entity/skeleton/wither_skeleton.png",
                "*/textures/entity/zombie/zombie.png",
                "*/textures/entity/creeper/creeper.png",
                "*/textures/entity/piglin/piglin.png",
                "*/textures/entity/enderdragon/dragon.png",
                "*/textures/entity/player/wide/steve.png",
                "*/textures/entity/conduit/base.png",
                "*/textures/entity/decorated_pot/decorated_pot_base.png",
                "*/textures/entity/decorated_pot/decorated_pot_side.png",
                "*/textures/painting/*.png",
            )
            for p in assets.glob(pattern)
        }
    )
    for file in files:
        relative = file.relative_to(assets)
        key = f"{relative.parts[0]}:{Path(*relative.parts[2:]).with_suffix('').as_posix()}"
        with Image.open(file) as image:
            frame = image.convert("RGBA")
        meta_file = file.with_suffix(".png.mcmeta")
        meta = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.is_file() else {}
        if "animation" in meta:
            animation = meta["animation"]
            width = animation.get(
                "width", frame.width if "height" in animation else min(frame.size)
            )
            height = animation.get(
                "height", frame.height if "width" in animation else min(frame.size)
            )
            first = animation.get("frames", [0])[0]
            index = first.get("index", 0) if isinstance(first, dict) else first
            x, y = index % (frame.width // width) * width, index // (frame.width // width) * height
            frame = frame.crop((x, y, x + width, y + height))
        textures.append((key, frame))
    if not textures:
        from design_workbench.domain.errors import WorkbenchError

        raise WorkbenchError("MISSING_TEXTURE", "客户端没有方块纹理。")
    width = max(
        256,
        2
        ** math.ceil(
            math.log2(math.sqrt(sum((im.width + 4) * (im.height + 4) for _, im in textures)))
        ),
    )
    width = max(width, max(im.width + 4 for _, im in textures))
    uv: dict[str, list[int]] = {}
    x = y = row_height = 0
    for key, im in sorted(textures, key=lambda entry: -entry[1].height):
        if x + im.width + 4 > width:
            x, y, row_height = 0, y + row_height, 0
        uv[key] = [x + 2, y + 2, im.width, im.height]
        x += im.width + 4
        row_height = max(row_height, im.height + 4)
    height = y + row_height
    atlas = Image.new("RGBA", (width, height))
    for key, im in textures:
        x, y, w, h = uv[key]
        atlas.paste(im, (x, y))
        atlas.paste(im.crop((0, 0, 1, h)).resize((2, h)), (x - 2, y))
        atlas.paste(im.crop((w - 1, 0, w, h)).resize((2, h)), (x + w, y))
        atlas.paste(im.crop((0, 0, w, 1)).resize((w, 2)), (x, y - 2))
        atlas.paste(im.crop((0, h - 1, w, h)).resize((w, 2)), (x, y + h))
        for dx, dy, px, py in (
            (-2, -2, 0, 0),
            (w, -2, w - 1, 0),
            (-2, h, 0, h - 1),
            (w, h, w - 1, h - 1),
        ):
            atlas.paste(im.getpixel((px, py)), (x + dx, y + dy, x + dx + 2, y + dy + 2))
    atlas.save(directory / "atlas.png")
    data = {"width": width, "height": height, "uv": uv}
    (directory / "atlas.json").write_text(json.dumps(data), encoding="utf-8")
    return data
