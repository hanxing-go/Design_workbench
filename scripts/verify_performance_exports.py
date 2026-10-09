"""Independently verify every exported benchmark block and preserved NBT.

Uses the separately implemented litemapy 0.11.0b0 decoder from the project's
existing dev dependencies. NumPy is already pinned by uv.lock through nbtlib;
no extra runtime dependency is introduced. The villa is explicitly a pure
state projection: its original v5/1.20.2 NBT is retained byte-for-byte and is
still rejected by production import. A newly authored state-only export does
not claim to preserve its 188 block entities or native import compatibility.
"""

from __future__ import annotations

import copy
import gzip
import hashlib
import io
import json
import time
from pathlib import Path

import nbtlib
import numpy as np
from litemapy import Region

from design_workbench.adapters.formats.litematic import Litematic
from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.adapters.storage.sqlite import SqliteStore
from design_workbench.domain.errors import WorkbenchError

ROOT = Path(__file__).resolve().parents[1]
CATALOG = Catalog()
ADAPTER = Litematic(CATALOG, max_volume=12_000_000)


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def independent_cells(path: Path) -> tuple[dict, int]:
    document = nbtlib.File.parse(io.BytesIO(gzip.decompress(path.read_bytes())))
    result = {}
    volume = 0
    # Region.from_nbt does not require unrelated optional document metadata
    # fields (e.g. Description) that Schematic.load insists on. No tag is added
    # to or removed from the file to satisfy the independent reader.
    for region_nbt in document["Regions"].values():
        # The generated town omits empty tick tags. The independent reader's
        # stricter schema needs them; add empty lists only to an in-memory copy,
        # recording that normalization, without changing export/source bytes.
        reader_input = copy.deepcopy(region_nbt)
        for key in ("PendingBlockTicks", "PendingFluidTicks"):
            if key not in reader_input:
                reader_input[key] = nbtlib.List[nbtlib.Compound]()
        region = Region.from_nbt(reader_input)
        # Read litemapy's independently unpacked grid directly to skip millions
        # of empty cells, then check *every* occupied coordinate and full state.
        # These private member names are pinned by litemapy==0.11.0b0 in uv.lock.
        palette = region._Region__palette
        grid = region._Region__blocks
        air = [
            index
            for index, state in enumerate(palette)
            if state.id in {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
        ]
        xs, ys, zs = np.nonzero(~np.isin(grid, air))
        indices = grid[xs, ys, zs]
        origin = (region.x + region.min_x(), region.y + region.min_y(), region.z + region.min_z())
        states = [(state.id, tuple(sorted(dict(state.properties()).items()))) for state in palette]
        for x, y, z, index in zip(
            xs.tolist(), ys.tolist(), zs.tolist(), indices.tolist(), strict=True
        ):
            point = (origin[0] + x, origin[1] + y, origin[2] + z)
            assert point not in result, "Overlapping regions are not an unambiguous export"
            result[point] = states[index]
        volume += int(grid.size)
    return result, volume


def preserve_nbt(source: bytes, exported: bytes) -> dict:
    before = nbtlib.File.parse(io.BytesIO(gzip.decompress(source)))
    after = nbtlib.File.parse(io.BytesIO(gzip.decompress(exported)))
    assert set(before) == set(after)
    for key in set(before) - {"Regions", "Metadata"}:
        assert before[key] == after[key], f"Root tag {key} changed"
    assert set(before["Regions"]) == set(after["Regions"])
    entities = 0
    preserved = []
    for name, region in before["Regions"].items():
        result = after["Regions"][name]
        assert set(region) == set(result)
        for key in set(region) - {"BlockStates", "BlockStatePalette"}:
            assert region[key] == result[key], (name, key)
            preserved.append(f"{name}.{key}")
        entities += len(region.get("TileEntities", []))
    # Palette storage and these metadata values are intentionally regenerated.
    ignored_metadata = {
        "Name",
        "TimeModified",
        "RegionCount",
        "TotalBlocks",
        "TotalVolume",
        "EnclosingSize",
    }
    for key in set(before["Metadata"]) - ignored_metadata:
        assert before["Metadata"][key] == after["Metadata"][key], f"Metadata tag {key} changed"
    return {
        "preserved_block_entities": entities,
        "preserved_region_tags": preserved,
        "root_unknown_tags_preserved": True,
        "unrelated_metadata_preserved": True,
    }


def main() -> None:
    output = ROOT / ".local/performance/exports"
    output.mkdir(parents=True, exist_ok=True)
    results = []
    inputs = [
        (
            "mixed_town_100000",
            ROOT / ".local/performance/fixtures/mixed-town-100000-v1.litematic",
            None,
        ),
        (
            "ivory_castle_upper_105102",
            ROOT / ".local/imports/mcblock-ivory-castle-upper-y51-105102.litematic",
            None,
        ),
        (
            "villa_46281_state_projection",
            ROOT / ".local/imports/mcblock-spanish-roof-villa-preview.litematic",
            ROOT / ".local/performance/data/projects/asset_villa_46281.dwbench",
        ),
    ]
    for label, source, project in inputs:
        started = time.perf_counter()
        payload = source.read_bytes()
        before_digest = digest(payload)
        native = project is None
        if native:
            scene, import_report = ADAPTER.read(payload)
            attached = payload
        else:
            try:
                ADAPTER.read(payload)
            except WorkbenchError as error:
                assert error.code == "UNSUPPORTED_FORMAT"
            else:
                raise AssertionError("Original v5 villa unexpectedly accepted as a native import")
            store = SqliteStore(project)
            scene = store.load()
            with store.connection() as connection:
                original_attachment = connection.execute(
                    "SELECT payload FROM attachments WHERE key='benchmark_original_litematic'"
                ).fetchone()[0]
            assert original_attachment == payload
            import_report = None
            attached = None
        expected = {
            point: (cell.state.name, cell.state.properties)
            for point, cell in scene.cells.items()
            if not cell.state.is_air
        }
        exported, export_report = ADAPTER.write(scene, source=attached)
        destination = output / f"{label}-roundtrip.litematic"
        destination.write_bytes(exported)
        actual, volume = independent_cells(destination)
        assert actual == expected, f"Independent all-block comparison failed: {label}"
        assert source.read_bytes() == payload, "Original source file was changed"
        exported_nbt = Litematic.parse(exported)
        result = {
            "name": label,
            "source": str(source.relative_to(ROOT)),
            "source_sha256_before": before_digest,
            "source_sha256_after": digest(source.read_bytes()),
            "export": str(destination.relative_to(ROOT)),
            "export_sha256": digest(exported),
            "all_nonair_cells_compared": len(actual),
            "export_volume": volume,
            "state_and_world_coordinates_all_equal": True,
            "independent_reader": "litemapy==0.11.0b0 (entire decoded grid; every occupied cell)",
            "independent_reader_empty_tick_tags_added_in_memory_only": label == "mixed_town_100000",
            "native_original_import_verified": native,
            "import_report": import_report,
            "export_report": export_report,
        }
        if native:
            result["nbt_preservation"] = preserve_nbt(payload, exported)
            result["full_source_scope_passed"] = True
        else:
            original_nbt = nbtlib.File.parse(io.BytesIO(gzip.decompress(payload)))
            original_entities = sum(
                len(region.get("TileEntities", [])) for region in original_nbt["Regions"].values()
            )
            final_entities = sum(
                len(region.get("TileEntities", [])) for region in exported_nbt["Regions"].values()
            )
            assert int(original_nbt["Version"]) == 5
            assert int(original_nbt["MinecraftDataVersion"]) == 3578
            assert int(exported_nbt["Version"]) == 6
            assert int(exported_nbt["MinecraftDataVersion"]) == 3465
            assert original_entities == 188 and final_entities == 0
            assert scene.protected == {
                tuple(int(entry[axis]) for axis in "xyz")
                for region in original_nbt["Regions"].values()
                for entry in region.get("TileEntities", [])
            }
            result["nbt_preservation"] = {
                "original_bytes_and_provenance_attachment_preserved": True,
                "original_v5_data_version_3578_still_rejected": True,
                "original_block_entities": original_entities,
                "new_state_only_export_block_entities": final_entities,
                "original_protected_positions_retained_in_render_project": len(scene.protected),
                "source_special_nbt_preserved_in_new_state_only_export": False,
            }
            result["full_source_scope_passed"] = False
            result["explicit_limitations"] = [
                "This export is a separately authored 1.20.1 state projection, not a native import or version rewrite of the source",
                "188 source block entities, their NBT and sign text are absent in this state-only export; original NBT remains byte-identical in provenance storage",
            ]
        result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        results.append(result)
        print(
            json.dumps(
                {
                    key: result[key]
                    for key in [
                        "name",
                        "all_nonair_cells_compared",
                        "state_and_world_coordinates_all_equal",
                        "full_source_scope_passed",
                        "elapsed_seconds",
                    ]
                }
            )
        )
    report = {
        "all_state_projection_exports_verified": True,
        "all_original_sources_native_import_compatible": False,
        "tests": results,
    }
    report_path = ROOT / "artifacts/performance/asset-export-crosscheck.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")


if __name__ == "__main__":
    main()
