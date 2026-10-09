"""Cross-check UI exports using litemapy's independent coordinate/packing implementation."""

import gzip
import hashlib
import io
import json
from pathlib import Path

import nbtlib
from litemapy import Schematic

from design_workbench.bootstrap import Workbench
from design_workbench.config import Settings

ROOT = Path(__file__).parents[1]


def main() -> None:
    workbench = Workbench(Settings.load(ROOT / "config.example.toml"))
    browser = json.loads(
        (ROOT / "artifacts/p5-browser-verification.json").read_text(encoding="utf-8")
    )
    results = []
    for name in ("cabin", "church"):
        record = browser[name]
        scene = workbench.service(
            ROOT / f".local/data/projects/{record['project_id']}.dwbench"
        ).repository.load()
        path = ROOT / "artifacts" / record["export"]
        reference = Schematic.load(str(path))
        reference_cells = {}
        selection_cells = 0
        for region in reference.regions.values():
            for position in region.block_positions():
                selection_cells += 1
                state = region[position]
                if state.id == "minecraft:air":
                    continue
                global_position = tuple(
                    position[i] + (region.x, region.y, region.z)[i] for i in range(3)
                )
                reference_cells[global_position] = {
                    "name": state.id,
                    "properties": dict(state.properties()),
                }
        expected = {point: cell.state.as_dict() for point, cell in scene.cells.items()}
        assert reference_cells == expected, f"{name} 的独立逐格比较失败"
        result = {
            "fixture": name,
            "blocks": scene.summary()["blocks"],
            "selection_cells": selection_cells,
            "coordinate_and_complete_state_comparison": "PASS",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        if name == "church":
            before = nbtlib.File.parse(
                io.BytesIO(
                    gzip.decompress((ROOT / ".local/imports/azalea-church.litematic").read_bytes())
                )
            )
            after = nbtlib.File.parse(io.BytesIO(gzip.decompress(path.read_bytes())))
            assert set(before["Regions"]) == set(after["Regions"])
            protected_count = 0
            for region_name, region in before["Regions"].items():
                for key in (
                    "TileEntities",
                    "Entities",
                    "PendingBlockTicks",
                    "PendingFluidTicks",
                    "Position",
                    "Size",
                ):
                    assert region[key] == after["Regions"][region_name][key], (region_name, key)
                protected_count += len(region["TileEntities"])
            result["preserved_block_entities"] = protected_count
            result["nbt_and_region_preservation"] = "PASS"
        results.append(result)
    report = {"independent_reader": "litemapy 0.11.0b0", "tests": results, "passed": True}
    (ROOT / "artifacts/export-crosscheck.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
