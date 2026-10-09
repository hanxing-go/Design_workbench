"""Prepare explicit, reproducible benchmark projections of public MCBlock previews.

This script never rewrites the downloaded source or changes production import
compatibility. The 1.20.2 villa is a *render state projection*, not a successful
Litematica import. Castle fixtures retain exact 1.20.1 states and coordinates.

Run ``python scripts/prepare_performance_assets.py --fetch-preview`` to obtain
the same publicly served preview bytes and build the 46k/105k fixtures. Add
``--full-castle`` for the separate 1,156,099-cell stress fixture. Import tests
of the original full castle require an explicitly isolated max_blocks=1500000
and max_selection_volume=12000000; normal application budgets stay unchanged.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import time
import urllib.request
from collections import Counter
from pathlib import Path

import nbtlib
import numpy as np

from design_workbench.adapters.formats.litematic import region_bounds, vector
from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.adapters.storage.sqlite import SqliteStore
from design_workbench.domain.models import BlockState, Bounds, Cell

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / ".local/performance/data/projects"
CATALOG = Catalog("1.20.1")
MANIFEST = ROOT / "artifacts/performance/asset-manifest.json"
SOURCE_HASHES = {
    "650421b0-f128-4f82-b28a-f684ede518a9": "fb057ff168d9703d5ba098d389c2807ad4d7521a94b7aa3478208c63fa87b8e4",
    "c57ddadd-24ab-4fcb-9236-ed705b6270fa": "be7fb40ae21cdff3fabc53ef8130b006debae1e9ed1a01507deac90c2949df87",
}


def decoded(region: nbtlib.Compound) -> np.ndarray:
    """Decode continuous bit packing independently with vectorized uint64 ops."""
    bounds = region_bounds(region)
    sx, sy, sz = (high - low + 1 for low, high in zip(bounds.low, bounds.high, strict=False))
    size = len(region["BlockStatePalette"])
    bits = max(2, (size - 1).bit_length())
    words = np.asarray(region["BlockStates"], dtype=np.int64).view(np.uint64)
    index = np.arange(bounds.volume, dtype=np.uint64)
    word = index * bits // 64
    offset = index * bits % 64
    values = words[word] >> offset
    overflow = offset + bits > 64
    values[overflow] |= words[word[overflow] + 1] << (64 - offset[overflow])
    values &= (1 << bits) - 1
    assert np.max(values) < size, "Invalid palette reference"
    return values.reshape(sy, sz, sx)


def prepare(
    identifier: str,
    title: str,
    source: Path,
    building_id: str,
    author: str,
    crop_y: int | None,
    expected: int,
) -> dict:
    started = time.perf_counter()
    payload = source.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    assert digest == SOURCE_HASHES[building_id], (
        "Source bytes changed; report and re-audit explicitly"
    )
    # This generic NBT parse is intentionally separate from production import.
    document = nbtlib.File.parse(io.BytesIO(gzip.decompress(payload)))
    source_version = int(document["Version"])
    source_data_version = int(document["MinecraftDataVersion"])
    cells = {}
    protected = set()
    boxes = []
    original_blocks = 0
    original_palette_states = 0
    original_tile_entities = 0
    additions = []
    replacements = []
    for region_name, region in document["Regions"].items():
        region_box = region_bounds(region)
        palette = []
        for entry in region["BlockStatePalette"]:
            state = BlockState.make(
                str(entry["Name"]), {str(k): str(v) for k, v in entry.get("Properties", {}).items()}
            )
            normalized = CATALOG.normalize(state)
            if state != normalized:
                additions.append({"source": state.as_dict(), "normalized": normalized.as_dict()})
            assert state == normalized, "Benchmark never adds defaults or substitutes states"
            palette.append(state)
        original_palette_states += len(palette)
        original_tile_entities += len(region.get("TileEntities", []))
        values = decoded(region)
        air = [index for index, state in enumerate(palette) if state.is_air]
        occupied = ~np.isin(values, air)
        original_blocks += int(occupied.sum())
        y_start = 0 if crop_y is None else max(0, crop_y - region_box.low[1])
        clipped_values = values[y_start:]
        clipped_occupied = occupied[y_start:]
        low = (region_box.low[0], region_box.low[1] + y_start, region_box.low[2])
        boxes.append(Bounds(low, region_box.high))
        # Preserve original world positions, states, group and region name.
        cell_palette = [Cell(state, str(region_name), str(region_name)) for state in palette]
        ys, zs, xs = np.nonzero(clipped_occupied)
        indices = clipped_values[ys, zs, xs]
        for y, z, x, index in zip(
            ys.tolist(), zs.tolist(), xs.tolist(), indices.tolist(), strict=False
        ):
            point = (region_box.low[0] + x, low[1] + y, region_box.low[2] + z)
            assert point not in cells
            cells[point] = cell_palette[index]
        for entry in region.get("TileEntities", []):
            relative = vector(entry)
            point = tuple(region_box.low[axis] + relative[axis] for axis in range(3))
            if point in cells:
                protected.add(point)
    assert len(cells) == expected, (len(cells), expected)
    bounds = Bounds(
        tuple(min(box.low[i] for box in boxes) for i in range(3)),
        tuple(max(box.high[i] for box in boxes) for i in range(3)),
    )
    path = PROJECTS / f"{identifier}.dwbench"
    if path.exists():
        store = SqliteStore(path)
        loaded = store.load()
        assert loaded.cells == cells and loaded.protected == protected
        scene = loaded
    else:
        store = SqliteStore.create(path, title, CATALOG.version, CATALOG.data_version, bounds)
        scene = store.load()
        scene.cells = cells
        scene.protected = protected
        # The v5 villa would fail sign_texts' strict production parse. Retain its
        # byte-exact source as separate provenance, without claiming sign text fidelity.
        attachment = payload if source_version == 6 and source_data_version == 3465 else None
        store.commit(
            scene,
            [(point, None, cell) for point, cell in cells.items()],
            0,
            f"fixture-{identifier}",
            digest,
            attachment=attachment,
        )
        with store.connection() as connection:
            connection.execute(
                "INSERT INTO attachments VALUES('benchmark_original_litematic', ?)", (payload,)
            )
        scene = store.load()
        assert scene.cells == cells and scene.protected == protected
    materials = Counter(cell.state.name for cell in cells.values())
    summary = scene.summary()
    result = {
        "project_id": identifier,
        "project_path": str(path.relative_to(ROOT)),
        "name": title,
        "website_name": "西班牙陶顶别墅" if "villa" in identifier else "象牙城堡",
        "author": author,
        "website_url": f"https://mcblock.top/buildings/{building_id}",
        "public_preview_url": f"https://mcblock.top/api/buildings/{building_id}/projection?v=55c1kg",
        "acquisition": "Anonymous public 3D preview request; no login/download gate bypass",
        "source_file": str(source.relative_to(ROOT)),
        "source_sha256": digest,
        "source_litematic_version": source_version,
        "source_minecraft_data_version": source_data_version,
        "source_minecraft_version": "1.20.2" if source_data_version == 3578 else "1.20.1",
        "source_verified_nonair_blocks": original_blocks,
        "source_palette_states": original_palette_states,
        "source_tile_entities": original_tile_entities,
        "fixture_minecraft_version": CATALOG.version,
        "fixture_minecraft_data_version": CATALOG.data_version,
        "fixture_nonair_blocks": len(cells),
        "fixture_unique_states": len({cell.state for cell in cells.values()}),
        "fixture_unique_block_types": len(materials),
        "fixture_protected_blocks": len(protected),
        "fixture_bounds": bounds.as_dict(),
        "fixture_occupied_bounds": summary["occupied_bounds"],
        "crop": None
        if crop_y is None
        else {
            "original_world_bounds": bounds.as_dict(),
            "rule": f"Retain every nonair source cell at original y >= {crop_y}; no coordinate translation",
            "reason": "Continuous upper architecture crop keeps towers, roofs, walls, foliage and terrain contours; excludes most solid underground terrain",
        },
        "state_projection_checks": {
            "all_source_palette_states_valid_in_1_20_1": True,
            "normalization_default_additions": additions,
            "substituted_states": replacements,
            "coordinates_changed": False,
            "source_file_rewritten": False,
        },
        "limitations": (
            [
                "Original v5/DataVersion3578 cannot pass strict production import; fixture verifies rendering of exact compatible states only",
                "Original block entity NBT retained as provenance; sign text not attached to production renderer, so complete visual identity is not claimed",
            ]
            if source_version != 6 or source_data_version != 3465
            else [
                "Benchmark project is a direct scene fixture, not evidence of importing a source beyond normal production budgets",
            ]
        )
        + (
            ["Fixture is a continuous source crop; not the complete 1,156,099-block castle"]
            if crop_y is not None
            else []
        ),
        "top_materials": materials.most_common(20),
        "preparation_seconds": round(time.perf_counter() - started, 3),
    }
    print(
        json.dumps(
            {
                key: result[key]
                for key in [
                    "project_id",
                    "fixture_nonair_blocks",
                    "fixture_unique_states",
                    "fixture_unique_block_types",
                    "preparation_seconds",
                ]
            },
            ensure_ascii=False,
        )
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-castle", action="store_true")
    parser.add_argument(
        "--fetch-preview",
        action="store_true",
        help="Fetch missing public anonymous 3D preview bytes, verifying pinned SHA256; never uses the gated download endpoint",
    )
    options = parser.parse_args()
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    rows = json.loads(MANIFEST.read_text("utf-8")) if MANIFEST.exists() else []
    tasks = [
        (
            "asset_villa_46281",
            "性能专用：西班牙陶顶别墅 46,281 格状态投影",
            ROOT / ".local/imports/mcblock-spanish-roof-villa-preview.litematic",
            "650421b0-f128-4f82-b28a-f684ede518a9",
            "未知作者（网站及原NBT均未署名）",
            None,
            46281,
        ),
        (
            "asset_ivory_castle_upper_105102",
            "性能专用：象牙城堡上部连续裁片 105,102 格",
            ROOT / ".local/imports/mcblock-c57ddadd-24ab-4fcb-9236-ed705b6270fa-preview.litematic",
            "c57ddadd-24ab-4fcb-9236-ed705b6270fa",
            "GraySun8151",
            51,
            105102,
        ),
    ]
    if options.full_castle:
        tasks = [
            (
                "asset_ivory_castle_full_1156099",
                "性能专用：象牙城堡完整 1,156,099 格",
                ROOT
                / ".local/imports/mcblock-c57ddadd-24ab-4fcb-9236-ed705b6270fa-preview.litematic",
                "c57ddadd-24ab-4fcb-9236-ed705b6270fa",
                "GraySun8151",
                None,
                1156099,
            )
        ]
    for task in tasks:
        source, building_id = task[2], task[3]
        if not source.exists() and options.fetch_preview:
            url = f"https://mcblock.top/api/buildings/{building_id}/projection?v=55c1kg"
            with urllib.request.urlopen(url, timeout=60) as response:
                payload = response.read(32_000_001)
            assert len(payload) <= 32_000_000
            assert hashlib.sha256(payload).hexdigest() == SOURCE_HASHES[building_id], (
                "Public preview changed; no fixture written until source is re-audited"
            )
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(payload)
        result = prepare(*task)
        rows = [row for row in rows if row["project_id"] != result["project_id"]] + [result]
        MANIFEST.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", "utf-8")


if __name__ == "__main__":
    main()
