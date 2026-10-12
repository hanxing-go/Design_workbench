import itertools
import json
from importlib.resources import files
from typing import Any

from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.models import BlockState


class Catalog:
    @staticmethod
    def versions() -> list[str]:
        return sorted(
            (
                path.name.removeprefix("registry-").removesuffix(".json")
                for path in files("design_workbench").joinpath("data").iterdir()
                if path.name.startswith("registry-") and path.name.endswith(".json")
            ),
            key=lambda version: tuple(int(part) for part in version.split(".")),
        )

    @classmethod
    def for_data_version(cls, data_version: int) -> "Catalog":
        for version in cls.versions():
            catalog = cls(version)
            if catalog.data_version == data_version:
                return catalog
        raise WorkbenchError("UNSUPPORTED_VERSION", f"尚未支持 DataVersion={data_version}。")

    def __init__(self, version: str = "1.20.1") -> None:
        if version not in self.versions():
            raise WorkbenchError(
                "UNSUPPORTED_VERSION", f"尚未支持 MC {version}。", "minecraft_version"
            )
        path = files("design_workbench").joinpath(f"data/registry-{version}.json")
        if not path.is_file():
            raise WorkbenchError(
                "UNSUPPORTED_VERSION", f"尚未支持 MC {version}。", "minecraft_version"
            )
        self.document: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        self.version: str = self.document["minecraft_version"]
        self.data_version: int = self.document["data_version"]
        self.blocks: dict[str, dict[str, Any]] = {}
        self.language: dict[str, str] = {}
        self._defaults: dict[str, BlockState] = {}
        self._allowed: dict[str, dict[str, list[str]]] = {}
        for block in self.document["blocks"]:
            name = f"minecraft:{block['name']}"
            self.blocks[name] = block
            allowed = {
                prop["name"]: (
                    ["true", "false"]
                    if prop["type"] == "bool"
                    else [str(v) for v in prop.get("values", range(prop["num_values"]))]
                )
                for prop in block.get("states", [])
            }
            self._allowed[name] = allowed
            offset = block["defaultState"] - block["minStateId"]
            properties: dict[str, str] = {}
            for key, values in reversed(list(allowed.items())):
                properties[key] = values[offset % len(values)]
                offset //= len(values)
            self._defaults[name] = BlockState.make(name, properties)

    def normalize(self, state: BlockState) -> BlockState:
        name = state.name
        if name not in self.blocks:
            raise WorkbenchError("UNKNOWN_BLOCK", f"{self.version} 没有方块 {name}。", "state.name")
        allowed = self._allowed[name]
        properties = dict(self._defaults[name].properties)
        for key, value in state.properties:
            if key not in allowed or value not in allowed[key]:
                raise WorkbenchError(
                    "INVALID_STATE", f"{name} 的 {key}={value} 非法。", f"state.properties.{key}"
                )
            properties[key] = value
        return BlockState.make(name, properties)

    def supports_attachment(self, state: BlockState) -> bool:
        block = self.blocks[state.name]
        name = state.name.split(":", 1)[1]
        if block.get("boundingBox") != "block":
            return False
        # Conservative offline support: never infer a sturdy face on partial models.
        if name.endswith(
            (
                "_stairs",
                "_slab",
                "_fence",
                "_wall",
                "_door",
                "_trapdoor",
                "_pane",
                "_bed",
                "_sign",
                "chest",
                "anvil",
                "hopper",
                "campfire",
                "cauldron",
            )
        ):
            return False
        return (
            not block.get("transparent", False)
            or name in {"glass", "ice", "packed_ice", "blue_ice"}
            or name.endswith("_stained_glass")
        )

    def default(self, name: str) -> BlockState:
        return self.normalize(BlockState.make(name))

    def states(self, name: str) -> list[BlockState]:
        name = self.default(name).name
        allowed = self._allowed[name]
        return [
            BlockState.make(name, dict(zip(allowed, values, strict=True)))
            for values in itertools.product(*allowed.values())
        ]

    def describe(self, name: str) -> dict[str, Any]:
        name = self.default(name).name
        block = self.blocks[name]
        short = name.split(":", 1)[1]
        return {
            "name": name,
            "display_name": block["displayName"],
            "chinese_name": self.language.get(
                f"block.minecraft.{short}",
                self.language.get(f"item.minecraft.{short}", block["displayName"]),
            ),
            "default_state": self._defaults[name].as_dict(),
            "properties": self._allowed[name],
            "state_count": block["maxStateId"] - block["minStateId"] + 1,
            "transparent": block.get("transparent", False),
            "category": self.category(short),
        }

    @staticmethod
    def category(name: str) -> str:
        if any(word in name for word in ("stairs", "slab", "wall", "fence")):
            return "构造"
        if any(word in name for word in ("door", "glass", "bars")):
            return "门窗"
        if any(word in name for word in ("leaves", "flower", "grass", "sapling", "azalea", "vine")):
            return "植物"
        if any(word in name for word in ("log", "wood", "planks", "bamboo")):
            return "木材"
        if any(word in name for word in ("wool", "concrete", "terracotta")):
            return "色彩"
        return "其他"

    def search(
        self, query: str = "", offset: int = 0, limit: int = 32, category: str = ""
    ) -> dict[str, Any]:
        if offset < 0 or not 1 <= limit <= 128:
            raise WorkbenchError("INVALID_PAGE", "offset >= 0，limit 为 1..128。", "pagination")
        words = query.strip().lower().split()
        items = []
        for name in self.blocks:
            item = self.describe(name)
            text = (
                f"{name} {item['display_name']} {item['chinese_name']} {item['category']}".lower()
            )
            if all(word in text for word in words) and (
                not category or item["category"] == category
            ):
                items.append(item)
        return {
            "minecraft_version": self.version,
            "total": len(items),
            "offset": offset,
            "limit": limit,
            "items": items[offset : offset + limit],
        }
