"""Audit every registered state against version-matched official client resources."""

import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from design_workbench.adapters.resources.acquire import fetch_official
from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.adapters.resources.pack import ResourceManager
from design_workbench.config import Settings


def audit(version: str, settings: Settings, download: bool) -> dict[str, Any]:
    catalog = Catalog(version)
    manager = ResourceManager(settings.cache_dir / "resources")
    pack = manager.active(version)
    if pack is None and download:
        jar, provenance = fetch_official(version, settings.cache_dir / "downloads")
        pack = manager.import_jar(jar, version, Path(provenance["language_path"]), provenance)
    if pack is None:
        raise RuntimeError(f"Java {version}: resources not installed (use --download)")
    assert pack.manifest["data_version"] == catalog.data_version
    counts: Counter[str] = Counter()
    missing = []
    for name in catalog.blocks:
        for state in catalog.states(name):
            support = pack.support(state)
            counts[support["status"]] += 1
            if support["status"] == "missing":
                missing.append({"state": state.as_dict(), **support})
        # Also exercise geometry construction, including the newest blocks.
        geometry = pack.geometry(catalog.default(name))
        if geometry["status"] == "static":
            assert geometry["faces"], name
    result = {
        "minecraft_version": version,
        "data_version": catalog.data_version,
        "blocks": len(catalog.blocks),
        "states": sum(counts.values()),
        "counts": dict(counts),
        "missing": missing,
        "resource_hash": pack.manifest["bundle_hash"],
        "registry_provenance": catalog.document["provenance"],
    }
    print(
        json.dumps(
            {key: result[key] for key in ("minecraft_version", "blocks", "states", "counts")}
        ),
        flush=True,
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("config.example.toml"))
    parser.add_argument("--versions", nargs="+", default=Catalog.versions())
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("artifacts/version-audit.json"))
    args = parser.parse_args()
    settings = Settings.load(args.config)

    def checked(version: str) -> dict[str, Any]:
        try:
            return audit(version, settings, args.download)
        except Exception as error:
            result = {"minecraft_version": version, "error": str(error)}
            print(json.dumps(result), flush=True)
            return result

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(checked, args.versions))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    if any(item.get("error") or item.get("missing") for item in results):
        raise SystemExit("Resource audit failed; see audit output")


if __name__ == "__main__":
    main()
