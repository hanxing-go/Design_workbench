"""Create an explicitly attributed, exact-state continuous castle crop.

This derivative keeps the original v6/3465 format. No source version conversion
or block substitution occurs. Original world coordinates are retained.
"""

import copy
import gzip
import hashlib
import io
import json

import nbtlib
from prepare_performance_assets import CATALOG, ROOT, decoded

from design_workbench.adapters.formats.litematic import (
    Litematic,
    nbt_vector,
    pack_states,
    region_bounds,
)
from design_workbench.adapters.storage.sqlite import SqliteStore

source = ROOT / ".local/imports/mcblock-c57ddadd-24ab-4fcb-9236-ed705b6270fa-preview.litematic"
payload = source.read_bytes()
document = copy.deepcopy(Litematic.parse(payload))
assert int(document["MinecraftDataVersion"]) == 3465
region = next(iter(document["Regions"].values()))
assert region_bounds(region).low == (0, 0, 0)
assert tuple(abs(int(region["Size"][axis])) for axis in "xyz") == (210, 160, 263)
grid = decoded(region)[51:]
region["Position"] = nbt_vector((0, 51, 0))
region["Size"] = nbt_vector((210, 109, 263))
region["BlockStates"] = pack_states(grid.ravel().tolist(), len(region["BlockStatePalette"]))
for key in ("TileEntities", "PendingBlockTicks", "PendingFluidTicks"):
    entries = []
    for entry in region.get(key, []):
        assert all(axis in entry for axis in "xyz")
        if int(entry["y"]) < 51:
            continue
        entry["y"] = nbtlib.Int(int(entry["y"]) - 51)
        entries.append(entry)
    region[key] = nbtlib.List[nbtlib.Compound](entries)
assert len(region.get("Entities", [])) == 0
metadata = document["Metadata"]
metadata["Name"] = nbtlib.String("Ivory Castle - upper architecture crop y>=51 - benchmark")
metadata["Description"] = nbtlib.String(
    "Benchmark derivative of Ivory Castle by GraySun8151. Source: "
    "https://mcblock.top/buildings/c57ddadd-24ab-4fcb-9236-ed705b6270fa . "
    "Retains all 105102 nonair cells at original world y>=51; drops lower terrain. "
    "Coordinates and exact block states unchanged; source v6/DataVersion3465 retained. "
    "Original source SHA256 be7fb40ae21cdff3fabc53ef8130b006debae1e9ed1a01507deac90c2949df87."
)
metadata["TotalBlocks"] = nbtlib.Int(105102)
metadata["TotalVolume"] = nbtlib.Int(210 * 109 * 263)
metadata["EnclosingSize"] = nbt_vector((210, 109, 263))
stream = io.BytesIO()
document.write(stream)
crop = gzip.compress(stream.getvalue(), mtime=0)
destination = ROOT / ".local/imports/mcblock-ivory-castle-upper-y51-105102.litematic"
destination.write_bytes(crop)
scene, report = Litematic(CATALOG, max_volume=12_000_000).read(crop)
fixture = SqliteStore(
    ROOT / ".local/performance/data/projects/asset_ivory_castle_upper_105102.dwbench"
).load()
assert scene.cells == fixture.cells
assert scene.protected == fixture.protected
result = {
    "file": str(destination.relative_to(ROOT)),
    "sha256": hashlib.sha256(crop).hexdigest(),
    "source_sha256": hashlib.sha256(payload).hexdigest(),
    "source_url": "https://mcblock.top/buildings/c57ddadd-24ab-4fcb-9236-ed705b6270fa",
    "author": "GraySun8151",
    "derivative": "Exact-state, unchanged world-coordinate continuous crop y>=51",
    "minecraft_data_version": 3465,
    "litematic_version": 6,
    "nonair_blocks": report["blocks"],
    "volume": report["volume"],
    "retained_tile_entities": report["block_entities"],
    "all_cells_and_protected_positions_equal_sqlite_fixture": True,
    "source_rewritten": False,
    "requires_explicit_selection_budget": 12_000_000,
}
(ROOT / "artifacts/performance/asset-crop-export.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8"
)
print(json.dumps(result, ensure_ascii=False))
