import hashlib
import json
import math
import os
import shutil
import stat
import time
import uuid
import zipfile
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any

from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.models import BlockState

from .atlas import RECIPE_VERSION, build_atlas
from .catalog import Catalog
from .geometry import DIRECTIONS, default_uv, face_uv, projected_uv, quads, rotate
from .special import special_geometry


def publish_directory(temporary: Path, destination: Path) -> None:
    """Windows scanners can briefly hold newly extracted resource directories."""
    for attempt in range(10):
        try:
            temporary.rename(destination)
            return
        except PermissionError as error:
            if os.name != "nt" or error.winerror not in {5, 32, 33} or attempt == 9:
                raise
            time.sleep(0.1 * (attempt + 1))


def resource_name(value: str) -> tuple[str, str]:
    namespace, _, path = value.partition(":")
    return (namespace, path) if path else ("minecraft", namespace)


def matches(condition: dict[str, Any], properties: dict[str, str]) -> bool:
    if "OR" in condition:
        return any(matches(item, properties) for item in condition["OR"])
    if "AND" in condition:
        return all(matches(item, properties) for item in condition["AND"])
    return all(
        str(properties.get(key, "")) in str(value).split("|") for key, value in condition.items()
    )


class ResourcePack:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.manifest: dict[str, Any] = json.loads(
            (directory / "manifest.json").read_text(encoding="utf-8")
        )
        self.language: dict[str, str] = json.loads(
            (directory / "zh_cn.json").read_text(encoding="utf-8")
        )
        self.atlas: dict[str, Any] = json.loads(
            (directory / "atlas.json").read_text(encoding="utf-8")
        )
        self.read = lru_cache(maxsize=4096)(self._read)
        self.model = lru_cache(maxsize=4096)(self._model)
        self.geometry = lru_cache(maxsize=2048)(self._geometry)
        self.support = lru_cache(maxsize=32768)(self._support)

    def _read(self, namespace: str, kind: str, name: str) -> dict[str, Any]:
        file = self.directory / "assets" / namespace / kind / f"{name}.json"
        if not file.is_file():
            raise WorkbenchError(
                "MISSING_RESOURCE", f"缺少 {namespace}:{kind}/{name}。", "resources"
            )
        return json.loads(file.read_text(encoding="utf-8"))  # type: ignore[no-any-return]

    def _model(self, name: str, depth: int = 0) -> dict[str, Any]:
        if depth > 32:
            raise WorkbenchError("MODEL_CYCLE", f"模型继承过深：{name}。")
        namespace, path = resource_name(name)
        if path.startswith("builtin/"):
            return {"special": True, "textures": {}, "elements": []}
        current = self.read(namespace, "models", path)
        parent = self.model(current["parent"], depth + 1) if current.get("parent") else {}
        return {
            **parent,
            **current,
            "textures": {**parent.get("textures", {}), **current.get("textures", {})},
            "elements": current.get("elements", parent.get("elements", [])),
        }

    def applications(self, state: BlockState) -> list[dict[str, Any]]:
        namespace, path = resource_name(state.name)
        definition = self.read(namespace, "blockstates", path)
        properties = dict(state.properties)
        if "multipart" in definition:
            applications = [
                item["apply"]
                for item in definition["multipart"]
                if matches(item.get("when", {}), properties)
            ]
            if not applications:
                return []
        else:
            applications = [
                value
                for key, value in definition.get("variants", {}).items()
                if not key
                or all(
                    properties.get(k) == v
                    for k, v in (pair.split("=", 1) for pair in key.split(","))
                )
            ]
        if not applications:
            raise WorkbenchError(
                "MISSING_VARIANT", f"没有对应显示状态：{state.name} {properties}。"
            )
        return [item[0] if isinstance(item, list) else item for item in applications]

    def texture(self, reference: str, model: dict[str, Any]) -> str:
        # Some official models (e.g. 1.21 heavy_core) use a bare texture variable.
        if reference in model.get("textures", {}):
            reference = "#" + reference
        for _ in range(32):
            if not reference.startswith("#"):
                namespace, path = resource_name(reference)
                key = f"{namespace}:{path}"
                if key not in self.atlas["uv"]:
                    raise WorkbenchError("MISSING_TEXTURE", f"图集缺少 {key}。")
                return key
            value = model.get("textures", {}).get(reference[1:])
            if isinstance(value, dict):
                value = value.get("sprite")
            if not isinstance(value, str):
                raise WorkbenchError("MISSING_TEXTURE", f"无法解析贴图 {reference}。")
            reference = value
        raise WorkbenchError("TEXTURE_CYCLE", "贴图引用循环。")

    def _support(self, state: BlockState) -> dict[str, Any]:
        if state.name in {
            "minecraft:air",
            "minecraft:cave_air",
            "minecraft:void_air",
            "minecraft:barrier",
            "minecraft:light",
            "minecraft:structure_void",
        }:
            return {"status": "invisible", "reason": "游戏中默认不可见"}
        try:
            special = special_geometry(state)
            if special is not None:
                for face in special["faces"]:
                    self.texture(face["texture"], {})
                return {"status": "static", "reason": "专用静态预览；不执行游戏物理"}
            applications = self.applications(state)
            if not applications:
                return {"status": "invisible", "reason": "当前状态的组合模型为空"}
            models = [self.model(item["model"]) for item in applications]
            if any(model.get("special") for model in models) or not any(
                model.get("elements") for model in models
            ):
                return {"status": "special", "reason": "需要专用渲染；数据保留"}
            for model in models:
                for element in model.get("elements", []):
                    for face in element.get("faces", {}).values():
                        self.texture(face["texture"], model)
            return {"status": "static", "reason": "静态模型与纹理已解析"}
        except WorkbenchError as error:
            return {"status": "missing", "reason": str(error), "code": error.code}

    def _geometry(self, state: BlockState) -> dict[str, Any]:
        support = self.support(state)
        if support["status"] != "static":
            return {**support, "faces": [], "opaque_cube": False}
        special = special_geometry(state)
        if special is not None:
            return {**support, **special}
        faces: list[dict[str, Any]] = []
        forced_translucent = False
        applications = self.applications(state)
        cube = False
        for application in applications:
            model = self.model(application["model"])
            forced_translucent |= any(
                isinstance(value, dict) and bool(value.get("force_translucent"))
                for value in model.get("textures", {}).values()
            )
            for element in model.get("elements", []):
                vertices = quads(element["from"], element["to"])
                cube = cube or (
                    element["from"] == [0, 0, 0]
                    and element["to"] == [16, 16, 16]
                    and len(element.get("faces", {})) == 6
                    and not element.get("rotation")
                )
                for direction, face in element.get("faces", {}).items():
                    uv = face.get("uv") or default_uv(element["from"], element["to"], direction)
                    corners = []
                    for corner in vertices[direction]:
                        point = [float(v) for v in corner]
                        rotation = element.get("rotation")
                        if rotation:
                            if rotation.get("rescale") and rotation["angle"]:
                                scale = 1 / math.cos(math.radians(rotation["angle"]))
                                axis = "xyz".index(rotation["axis"])
                                point = [
                                    value
                                    if i == axis
                                    else rotation["origin"][i]
                                    + (value - rotation["origin"][i]) * scale
                                    for i, value in enumerate(point)
                                ]
                            point = rotate(
                                point, rotation["axis"], rotation["angle"], rotation["origin"]
                            )
                        point = rotate(point, "x", -application.get("x", 0), [8, 8, 8])
                        point = rotate(point, "y", -application.get("y", 0), [8, 8, 8])
                        corners.append([round(value / 16, 6) for value in point])
                    uvs = face_uv(uv, turns=int(face.get("rotation", 0) / 90))
                    normal = rotate(
                        [float(v) for v in DIRECTIONS[direction]],
                        "x",
                        -application.get("x", 0),
                        [0, 0, 0],
                    )
                    normal = rotate(normal, "y", -application.get("y", 0), [0, 0, 0])
                    rotated_direction = next(
                        name
                        for name, vector in DIRECTIONS.items()
                        if all(round(normal[i]) == vector[i] for i in range(3))
                    )
                    if application.get("uvlock"):
                        basis = []
                        for vertex in quads([0, 0, 0], [16, 16, 16])[direction]:
                            vertex = rotate(vertex, "x", -application.get("x", 0), [8, 8, 8])
                            vertex = rotate(vertex, "y", -application.get("y", 0), [8, 8, 8])
                            basis.append(projected_uv(vertex, rotated_direction))
                        a = [(basis[1][i] - basis[0][i]) / 16 for i in range(2)]
                        b = [(basis[0][i] - basis[3][i]) / 16 for i in range(2)]
                        uvs = [
                            [round(0.5 + a[i] * (u - 0.5) + b[i] * (v - 0.5), 6) for i in range(2)]
                            for u, v in uvs
                        ]
                    cull = None
                    if face.get("cullface"):
                        vector = rotate(
                            [float(v) for v in DIRECTIONS[face["cullface"]]],
                            "x",
                            -application.get("x", 0),
                            [0, 0, 0],
                        )
                        vector = rotate(vector, "y", -application.get("y", 0), [0, 0, 0])
                        cull = [round(v) for v in vector]
                    faces.append(
                        {
                            "vertices": [v for corner in corners for v in corner],
                            "uv": [v for point in uvs for v in point],
                            "texture": self.texture(face["texture"], model),
                            "tint": "tintindex" in face,
                            "cull": cull,
                        }
                    )
        return {
            **support,
            "faces": faces,
            "opaque_cube": cube and len(applications) == 1,
            "render_layer": "translucent"
            if forced_translucent
            or "stained_glass" in state.name
            or state.name in {"minecraft:ice", "minecraft:slime_block", "minecraft:honey_block"}
            else "cutout",
        }


class ResourceManager:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def active(self, version: str) -> ResourcePack | None:
        pointer = self.directory / version / "current.json"
        if not pointer.is_file():
            return None
        data = json.loads(pointer.read_text(encoding="utf-8"))
        path = (pointer.parent / data["directory"]).resolve()
        if not path.is_relative_to(pointer.parent.resolve()):
            raise WorkbenchError("RESOURCE_PATH", "资源目录超出配置范围。")
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        catalog = Catalog(version)
        if (
            manifest.get("minecraft_version") != version
            or manifest.get("data_version") != catalog.data_version
        ):
            raise WorkbenchError("VERSION_MISMATCH", "资源包版本与注册表不一致。", "resources")
        if manifest.get("recipe_version", 1) < RECIPE_VERSION:
            # Upgrade only derived resources. The user's projects and source assets stay intact.
            bundle_hash = hashlib.sha256(
                (
                    manifest["sha256"] + manifest["language_sha256"] + f":atlas-{RECIPE_VERSION}"
                ).encode()
            ).hexdigest()
            destination = pointer.parent / bundle_hash[:20]
            temporary = pointer.parent / f".upgrade-{uuid.uuid4().hex}"
            try:
                if not destination.is_dir():
                    temporary.mkdir()
                    shutil.copytree(path / "assets", temporary / "assets")
                    shutil.copy2(path / "zh_cn.json", temporary / "zh_cn.json")
                    atlas = build_atlas(temporary)
                    manifest.update(
                        bundle_hash=bundle_hash,
                        recipe_version=RECIPE_VERSION,
                        texture_count=len(atlas["uv"]),
                    )
                    (temporary / "manifest.json").write_text(
                        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    try:
                        publish_directory(temporary, destination)
                    except FileExistsError:
                        if not (destination / "manifest.json").is_file():
                            raise
                new_pointer = pointer.with_name(f"current-{uuid.uuid4().hex}.tmp")
                new_pointer.write_text(
                    json.dumps({"directory": destination.name}), encoding="utf-8"
                )
                new_pointer.replace(pointer)
            finally:
                if temporary.exists() and temporary.resolve().is_relative_to(
                    pointer.parent.resolve()
                ):
                    shutil.rmtree(temporary)
            path = destination
        return ResourcePack(path)

    def import_jar(
        self,
        jar: Path,
        version: str,
        language: Path | None = None,
        source: dict[str, Any] | None = None,
    ) -> ResourcePack:
        catalog = Catalog(version)
        jar_hash = hashlib.sha256(jar.read_bytes()).hexdigest()
        language_data = language.read_bytes() if language and language.is_file() else b"{}"
        bundle_hash = hashlib.sha256(
            (
                jar_hash + hashlib.sha256(language_data).hexdigest() + f":atlas-{RECIPE_VERSION}"
            ).encode()
        ).hexdigest()
        root = self.directory / version
        root.mkdir(parents=True, exist_ok=True)
        destination = root / bundle_hash[:20]
        temporary = root / f".import-{uuid.uuid4().hex}"
        if not destination.is_dir():
            temporary.mkdir()
            try:
                with zipfile.ZipFile(jar) as archive:
                    jar_version = json.loads(archive.read("version.json"))
                    if (
                        jar_version["id"] != version
                        or jar_version["world_version"] != catalog.data_version
                    ):
                        raise WorkbenchError(
                            "VERSION_MISMATCH", f"客户端是 {jar_version['id']}，目标为 {version}。"
                        )
                    total = 0
                    for member in archive.infolist():
                        if not member.filename.startswith(
                            "assets/"
                        ) or not member.filename.endswith((".json", ".png", ".mcmeta")):
                            continue
                        path = PurePosixPath(member.filename)
                        if (
                            ".." in path.parts
                            or path.is_absolute()
                            or stat.S_ISLNK(member.external_attr >> 16)
                        ):
                            raise WorkbenchError("RESOURCE_PATH", "资源含不安全路径。")
                        total += member.file_size
                        if member.file_size > 10_000_000 or total > 500_000_000:
                            raise WorkbenchError("RESOURCE_LIMIT", "资源展开超过大小上限。")
                        output = temporary.joinpath(*path.parts)
                        output.parent.mkdir(parents=True, exist_ok=True)
                        output.write_bytes(archive.read(member))
                (temporary / "zh_cn.json").write_bytes(language_data)
                atlas = build_atlas(temporary)
                manifest = {
                    "schema_version": 1,
                    "recipe_version": RECIPE_VERSION,
                    "minecraft_version": version,
                    "data_version": jar_version["world_version"],
                    "sha256": jar_hash,
                    "bundle_hash": bundle_hash,
                    "source": source or {"source": "user-provided-client"},
                    "texture_count": len(atlas["uv"]),
                    "language_sha256": hashlib.sha256(language_data).hexdigest(),
                }
                (temporary / "manifest.json").write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                try:
                    publish_directory(temporary, destination)
                except FileExistsError:
                    if not (destination / "manifest.json").is_file():
                        raise
            finally:
                if temporary.exists() and temporary.resolve().is_relative_to(root.resolve()):
                    shutil.rmtree(temporary)
        pointer = root / f"current-{uuid.uuid4().hex}.tmp"
        pointer.write_text(json.dumps({"directory": destination.name}), encoding="utf-8")
        pointer.replace(root / "current.json")
        return ResourcePack(destination)
