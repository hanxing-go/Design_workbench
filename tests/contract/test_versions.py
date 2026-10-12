"""Version isolation, real format round trips, and first-import resource lifecycle."""

import gzip
import io
import json
import math
import zipfile
from pathlib import Path

import nbtlib
import pytest
from fastapi.testclient import TestClient
from litemapy import Schematic
from PIL import Image

from design_workbench.adapters.formats.litematic import Litematic
from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.bootstrap import Workbench
from design_workbench.config import Settings
from design_workbench.interfaces.http import create_app
from design_workbench.interfaces.tools import Tools


def settings_at(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data", cache_dir=tmp_path / "cache", log_dir=tmp_path / "log"
    )


@pytest.mark.parametrize("version", Catalog.versions())
def test_each_registry_and_project_roundtrip(tmp_path: Path, version: str) -> None:
    catalog = Catalog(version)
    for block in catalog.blocks.values():
        properties = catalog.describe(block["name"])["properties"]
        assert (
            math.prod(map(len, properties.values()))
            == block["maxStateId"] - block["minStateId"] + 1
        )
        assert catalog.default(block["name"]) in catalog.states(block["name"])
    settings = settings_at(tmp_path)
    with TestClient(create_app(settings)) as client:
        created = client.post("/api/projects", json={"name": version, "minecraft_version": version})
        assert created.status_code == 201
        project = created.json()["project_id"]
        path = f"/api/projects/{project}"
        name = list(catalog.blocks)[-1]
        response = client.post(
            path + "/edit",
            json={
                "expected_revision": 0,
                "request_id": "place",
                "operations": [
                    {"op": "set", "blocks": [{"position": [-1, 2, 3], "state": {"name": name}}]}
                ],
            },
        )
        assert response.status_code == 200, response.text
        exported = client.post(path + "/export", json={"expected_revision": 1})
        assert exported.status_code == 200
        output = tmp_path / "export.litematic"
        output.write_bytes(exported.content)
        reference = Schematic.load(str(output))
        assert reference.mc_version == catalog.data_version
        states = [
            region[x, y, z].id
            for region in reference.regions.values()
            for x, y, z in region.block_positions()
        ]
        assert name in states
        # v5 uses the same continuous bit array; preserve the actual source version on re-export.
        root = Litematic.parse(exported.content)
        root["Version"] = nbtlib.Int(5)
        raw = io.BytesIO()
        root.write(raw)
        payload = gzip.compress(raw.getvalue())
        probe = client.post("/api/blueprints/info", files={"file": ("test.litematic", payload)})
        assert probe.json()["minecraft_version"] == version
        imported = client.post(
            path + "/import",
            data={"expected_revision": 1, "request_id": "import"},
            files={"file": ("test.litematic", payload)},
        )
        assert imported.status_code == 200, imported.text
        assert (
            int(
                Litematic.parse(
                    client.post(path + "/export", json={"expected_revision": 2}).content
                )["Version"]
            )
            == 5
        )
        for direction, revision in [("undo", 2), ("redo", 3)]:
            assert (
                client.post(
                    path + f"/history/{direction}",
                    json={"expected_revision": revision, "request_id": direction},
                ).status_code
                == 200
            )
    reopened = Workbench(settings).service(settings.data_dir / "projects" / f"{project}.dwbench")
    assert reopened.summary()["minecraft_version"] == version
    assert reopened.editor.registry.default(name) == catalog.default(name)


def test_cross_version_catalog_edit_and_import_are_isolated(tmp_path: Path) -> None:
    settings = settings_at(tmp_path)
    app = create_app(settings)
    with TestClient(app) as client:
        old = client.post("/api/projects", json={"minecraft_version": "1.20.1"}).json()[
            "project_id"
        ]
        new = client.post("/api/projects", json={"minecraft_version": "1.21.4"}).json()[
            "project_id"
        ]
        for identifier, total in [(old, 0), (new, 1)]:
            result = client.get(
                "/api/catalog", params={"project": identifier, "query": "minecraft:pale_oak_planks"}
            )
            assert result.json()["total"] == total
        request = {
            "expected_revision": 0,
            "request_id": "new-block",
            "operations": [
                {
                    "op": "set",
                    "blocks": [{"position": [0, 0, 0], "state": {"name": "pale_oak_planks"}}],
                }
            ],
        }
        assert (
            client.post(f"/api/projects/{old}/edit", json=request).json()["error"]["code"]
            == "UNKNOWN_BLOCK"
        )
        assert client.post(f"/api/projects/{new}/edit", json=request).status_code == 200
        blueprint = client.post(
            f"/api/projects/{new}/export", json={"expected_revision": 1}
        ).content
        mismatched = client.post(
            f"/api/projects/{old}/import",
            data={"expected_revision": 0, "request_id": "wrong-version"},
            files={"file": ("new.litematic", blueprint)},
        )
        assert mismatched.json()["error"]["code"] == "VERSION_MISMATCH"
        assert client.get(f"/api/projects/{old}").json()["revision"] == 0
        assert (
            client.get("/api/info", params={"project": new, "minecraft_version": "1.20.1"}).json()[
                "error"
            ]["code"]
            == "VERSION_MISMATCH"
        )
        assert (
            client.post("/api/projects", json={"minecraft_version": "../unknown"}).json()["error"][
                "code"
            ]
            == "UNSUPPORTED_VERSION"
        )
    tools = Tools(Workbench(settings), isolated=False)
    try:
        for identifier, total in [(old, 0), (new, 1)]:
            assert (
                tools.call("catalog.search", {"project": identifier, "query": "pale_oak_planks"})[
                    "total"
                ]
                == total
            )
    finally:
        tools.close()


@pytest.mark.parametrize("version", ["1.21.4", "26.1"])
def test_resources_installed_after_startup_are_visible_without_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, version: str
) -> None:
    # Synthetic client archive; no game assets are distributed with the test.
    settings = settings_at(tmp_path)
    jar = tmp_path / "synthetic.jar"
    png = io.BytesIO()
    Image.new("RGBA", (16, 16), "green").save(png, format="PNG")
    with zipfile.ZipFile(jar, "w") as archive:
        archive.writestr(
            "version.json",
            json.dumps({"id": version, "world_version": Catalog(version).data_version}),
        )
        archive.writestr("assets/minecraft/textures/block/oak_planks.png", png.getvalue())
        archive.writestr(
            "assets/minecraft/blockstates/oak_planks.json",
            json.dumps({"variants": {"": {"model": "minecraft:block/oak_planks"}}}),
        )
        archive.writestr(
            "assets/minecraft/models/block/oak_planks.json",
            json.dumps(
                {
                    "textures": {
                        "all": "minecraft:block/oak_planks"
                        if version == "1.21.4"
                        else {"sprite": "minecraft:block/oak_planks", "force_translucent": True}
                    },
                    "elements": [
                        {
                            "from": [0, 0, 0],
                            "to": [16, 16, 16],
                            "faces": {"up": {"texture": "all"}},
                        }
                    ],
                }
            ),
        )
    language = tmp_path / "language.json"
    language.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        "design_workbench.interfaces.http.fetch_official",
        lambda *args: (jar, {"language_path": str(language)}),
    )
    with TestClient(create_app(settings)) as client:
        assert not client.get(f"/api/info?minecraft_version={version}").json()["resources_ready"]
        response = client.post("/api/resources/setup", json={"minecraft_version": version})
        assert response.status_code == 200, response.text
        assert response.json()["resources_ready"]
        assert not client.get("/api/info").json()["resources_ready"]
        geometry = client.get(f"/api/material/oak_planks?minecraft_version={version}").json()
        assert geometry["status"] == "static"
        assert geometry["render_layer"] == ("translucent" if version == "26.1" else "cutout")
        assert client.get(f"/api/atlas.png?minecraft_version={version}").status_code == 200
        assert client.get("/api/atlas.png").status_code == 422
        monkeypatch.setattr(
            "design_workbench.interfaces.http.fetch_official",
            lambda *args: pytest.fail("Already installed"),
        )
        assert (
            client.post("/api/resources/setup", json={"minecraft_version": version}).status_code
            == 200
        )
