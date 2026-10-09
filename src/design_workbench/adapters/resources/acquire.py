import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any

from design_workbench.domain.errors import WorkbenchError

MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"


def download(url: str, output: Path, sha1: str | None = None, max_bytes: int = 100_000_000) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".part")
    digest = hashlib.sha1()  # Game manifests identify files with SHA-1.
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "DesignWorkbench/0.1"})
        with (
            urllib.request.urlopen(request, timeout=60) as response,
            temporary.open("wb") as handle,
        ):
            size = 0
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise WorkbenchError("RESOURCE_LIMIT", "资源超过下载大小上限。")
                digest.update(chunk)
                handle.write(chunk)
        if sha1 and digest.hexdigest() != sha1:
            raise WorkbenchError("RESOURCE_HASH", "资源哈希与官方清单不一致。")
        temporary.replace(output)
        return digest.hexdigest()
    finally:
        temporary.unlink(missing_ok=True)


def read_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "DesignWorkbench/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)  # type: ignore[no-any-return]


def fetch_official(version: str, directory: Path) -> tuple[Path, dict[str, Any]]:
    manifest = read_json(MANIFEST_URL)
    entry = next((item for item in manifest["versions"] if item["id"] == version), None)
    if entry is None:
        raise WorkbenchError("UNSUPPORTED_VERSION", f"官方清单没有 {version}。")
    metadata = read_json(entry["url"])
    client = metadata["downloads"]["client"]
    jar = directory / f"minecraft-{version}.jar"
    if not jar.is_file() or hashlib.sha1(jar.read_bytes()).hexdigest() != client["sha1"]:
        download(client["url"], jar, client["sha1"])
    language_path = directory / f"zh_cn-{version}.json"
    index = read_json(metadata["assetIndex"]["url"])
    language = index["objects"].get("minecraft/lang/zh_cn.json")
    if language:
        language_hash = language["hash"]
        language_url = (
            f"https://resources.download.minecraft.net/{language_hash[:2]}/{language_hash}"
        )
        if (
            not language_path.is_file()
            or hashlib.sha1(language_path.read_bytes()).hexdigest() != language_hash
        ):
            download(language_url, language_path, language_hash, max_bytes=5_000_000)
    provenance = {
        "source": client["url"],
        "sha1": client["sha1"],
        "metadata_url": entry["url"],
        "minecraft_version": version,
    }
    return jar, {**provenance, "language_path": str(language_path)}
