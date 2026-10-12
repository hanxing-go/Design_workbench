"""Build a provenance-bearing registry snapshot from pinned minecraft-data sources."""

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "DesignWorkbench/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", default="33a0f3e7323e124a81960a6d6c62df797d69cd85")
    parser.add_argument("--version", default="1.20.1")
    args = parser.parse_args()
    commit = args.commit
    prefix = f"https://raw.githubusercontent.com/PrismarineJS/minecraft-data/{commit}/data"
    paths = json.loads(get(f"{prefix}/dataPaths.json"))["pc"]
    if args.version not in paths:
        parser.error(f"No registry for Java {args.version} at commit {commit}")
    url = f"{prefix}/{paths[args.version]['blocks']}/blocks.json"
    raw = get(url)
    versions = json.loads(get(f"{prefix}/pc/common/protocolVersions.json"))
    version = next(item for item in versions if item["minecraftVersion"] == args.version)
    blocks = json.loads(raw)
    document = {
        "schema_version": 1,
        "minecraft_version": args.version,
        "data_version": version["dataVersion"],
        "provenance": {
            "source": url,
            "commit": commit,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "license": "MIT",
            "license_url": f"https://raw.githubusercontent.com/PrismarineJS/minecraft-data/{commit}/README.md#license",
        },
        "blocks": blocks,
    }
    directory = ROOT / "src/design_workbench/data"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"registry-{args.version}.json").write_text(
        json.dumps(document, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    (directory / "minecraft-data-SOURCE.md").write_bytes(
        get(document["provenance"]["license_url"].split("#", 1)[0])
    )
    print(
        json.dumps(
            {"blocks": len(blocks), "data_version": document["data_version"], "commit": commit}
        )
    )


if __name__ == "__main__":
    main()
