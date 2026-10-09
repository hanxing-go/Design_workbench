import hashlib
import json
import math
import shutil
import stat
import uuid
import zipfile
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any

from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.models import BlockState


def resource_name(value: str) -> tuple[str, str]:
    namespace, _, path = value.partition(":")
    return (namespace, path) if path else ("minecraft", namespace)


def rotate(vector: list[float], axis: str, angle: float, origin: list[float]) -> list[float]:
    values = [v - o for v, o in zip(vector, origin, strict=True)]
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    x, y, z = values
    if axis == "x":
        values = [x, y * c - z * s, y * s + z * c]
    elif axis == "y":
        values = [x * c + z * s, y, -x * s + z * c]
    else:
        values = [x * c - y * s, x * s + y * c, z]
    return [v + o for v, o in zip(values, origin, strict=True)]


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
        for _ in range(32):
            if not reference.startswith("#"):
                namespace, path = resource_name(reference)
                key = f"{namespace}:{path}"
                if key not in self.atlas["uv"]:
                    raise WorkbenchError("MISSING_TEXTURE", f"图集缺少 {key}。")
                return key
            value = model.get("textures", {}).get(reference[1:])
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
        faces: list[dict[str, Any]] = []
        applications = self.applications(state)
        cube = False
        for application in applications:
            model = self.model(application["model"])
            for element in model.get("elements", []):
                x0, y0, z0 = element["from"]
                x1, y1, z1 = element["to"]
                quads = {
                    "up": [[x0, y1, z0], [x0, y1, z1], [x1, y1, z1], [x1, y1, z0]],
                    "down": [[x0, y0, z1], [x0, y0, z0], [x1, y0, z0], [x1, y0, z1]],
                    "north": [[x1, y0, z0], [x0, y0, z0], [x0, y1, z0], [x1, y1, z0]],
                    "south": [[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]],
                    "west": [[x0, y0, z0], [x0, y0, z1], [x0, y1, z1], [x0, y1, z0]],
                    "east": [[x1, y0, z1], [x1, y0, z0], [x1, y1, z0], [x1, y1, z1]],
                }
                cube = cube or (
                    element["from"] == [0, 0, 0]
                    and element["to"] == [16, 16, 16]
                    and len(element.get("faces", {})) == 6
                    and not element.get("rotation")
                )
                for direction, face in element.get("faces", {}).items():
                    uv = face.get("uv") or (
                        [x0, z0, x1, z1]
                        if direction in {"up", "down"}
                        else [z0, 16 - y1, z1, 16 - y0]
                        if direction in {"east", "west"}
                        else [x0, 16 - y1, x1, 16 - y0]
                    )
                    corners = []
                    for corner in quads[direction]:
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
                        point = rotate(point, "x", application.get("x", 0), [8, 8, 8])
                        point = rotate(point, "y", -application.get("y", 0), [8, 8, 8])
                        corners.append([round(value / 16, 6) for value in point])
                    uvs = [
                        [uv[0] / 16, uv[3] / 16],
                        [uv[2] / 16, uv[3] / 16],
                        [uv[2] / 16, uv[1] / 16],
                        [uv[0] / 16, uv[1] / 16],
                    ]
                    turns = int(face.get("rotation", 0) / 90)
                    if application.get("uvlock") and direction in {"up", "down"}:
                        turns += int(application.get("y", 0) / 90) * (
                            1 if direction == "up" else -1
                        )
                    for _ in range(turns % 4):
                        uvs.append(uvs.pop(0))
                    p0, p1, p2 = corners[:3]
                    a = [p1[i] - p0[i] for i in range(3)]
                    b = [p2[i] - p0[i] for i in range(3)]
                    normal = [
                        a[1] * b[2] - a[2] * b[1],
                        a[2] * b[0] - a[0] * b[2],
                        a[0] * b[1] - a[1] * b[0],
                    ]
                    cull = None
                    if face.get("cullface"):
                        cull = [int(round(v / (max(abs(n) for n in normal) or 1))) for v in normal]
                    faces.append(
                        {
                            "vertices": [v for corner in corners for v in corner],
                            "uv": [v for point in uvs for v in point],
                            "texture": self.texture(face["texture"], model),
                            "tint": "tintindex" in face,
                            "cull": cull,
                        }
                    )
        return {**support, "faces": faces, "opaque_cube": cube and len(applications) == 1}


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
        return ResourcePack(path)

    def import_jar(
        self,
        jar: Path,
        version: str,
        language: Path | None = None,
        source: dict[str, Any] | None = None,
    ) -> ResourcePack:
        from PIL import Image

        jar_hash = hashlib.sha256(jar.read_bytes()).hexdigest()
        language_data = language.read_bytes() if language and language.is_file() else b"{}"
        bundle_hash = hashlib.sha256(
            (jar_hash + hashlib.sha256(language_data).hexdigest()).encode()
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
                    if jar_version["id"] != version:
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
                textures: list[tuple[str, Any]] = []
                for file in sorted((temporary / "assets").glob("*/textures/block/**/*.png")):
                    relative = file.relative_to(temporary / "assets")
                    namespace = relative.parts[0]
                    key = f"{namespace}:{PurePosixPath(*relative.parts[2:]).with_suffix('')}"
                    with Image.open(file) as image:
                        frame = image.convert("RGBA")
                    if frame.height > frame.width:
                        frame = frame.crop((0, 0, frame.width, frame.width))
                    textures.append((key, frame))
                if not textures:
                    raise WorkbenchError("MISSING_TEXTURE", "客户端没有方块纹理。")
                tile = max(max(image.size) for _, image in textures) + 4
                columns = math.ceil(math.sqrt(len(textures)))
                width, height = columns * tile, math.ceil(len(textures) / columns) * tile
                atlas = Image.new("RGBA", (width, height))
                uv: dict[str, list[int]] = {}
                for i, (key, image) in enumerate(textures):
                    x, y = (i % columns) * tile + 2, (i // columns) * tile + 2
                    atlas.paste(image, (x, y))
                    uv[key] = [x, y, image.width, image.height]
                    atlas.paste(
                        image.crop((0, 0, 1, image.height)).resize((2, image.height)), (x - 2, y)
                    )
                    atlas.paste(
                        image.crop((image.width - 1, 0, image.width, image.height)).resize(
                            (2, image.height)
                        ),
                        (x + image.width, y),
                    )
                    atlas.paste(
                        image.crop((0, 0, image.width, 1)).resize((image.width, 2)), (x, y - 2)
                    )
                    atlas.paste(
                        image.crop((0, image.height - 1, image.width, image.height)).resize(
                            (image.width, 2)
                        ),
                        (x, y + image.height),
                    )
                atlas.save(temporary / "atlas.png")
                (temporary / "atlas.json").write_text(
                    json.dumps({"width": width, "height": height, "uv": uv}), encoding="utf-8"
                )
                manifest = {
                    "schema_version": 1,
                    "minecraft_version": version,
                    "data_version": jar_version["world_version"],
                    "sha256": jar_hash,
                    "bundle_hash": bundle_hash,
                    "source": source or {"source": "user-provided-client"},
                    "texture_count": len(textures),
                    "language_sha256": hashlib.sha256(language_data).hexdigest(),
                }
                (temporary / "manifest.json").write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                temporary.rename(destination)
            finally:
                if temporary.exists() and temporary.resolve().is_relative_to(root.resolve()):
                    shutil.rmtree(temporary)
        pointer = root / f"current-{uuid.uuid4().hex}.tmp"
        pointer.write_text(json.dumps({"directory": destination.name}), encoding="utf-8")
        pointer.replace(root / "current.json")
        return ResourcePack(destination)
