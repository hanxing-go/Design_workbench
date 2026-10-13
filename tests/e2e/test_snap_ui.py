import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from PIL import Image
from playwright.sync_api import sync_playwright

from design_workbench.adapters.formats.litematic import Litematic


@pytest.mark.e2e
def test_wall_snap_manual_override_painting_history_and_export(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {
        **os.environ,
        "DW_DATA_DIR": str(tmp_path / "data"),
        "DW_CACHE_DIR": str(root / ".local/cache"),
        "DW_LOG_DIR": str(tmp_path / "logs"),
    }
    process = subprocess.Popen(
        [sys.executable, "-m", "design_workbench.interfaces.cli", "serve", "--port", str(port)],
        cwd=tmp_path,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 20
        while True:
            assert process.poll() is None
            try:
                if httpx.get(url + "/api/info", timeout=1).status_code == 200:
                    break
            except httpx.TransportError:
                pass
            assert time.monotonic() < deadline
            time.sleep(0.1)
        with httpx.Client(base_url=url, timeout=30) as client, sync_playwright() as pw:
            identifier = client.post("/api/projects", json={"name": "吸附验收"}).json()[
                "project_id"
            ]
            path = "/api/projects/" + identifier
            client.post(
                path + "/edit",
                json={
                    "expected_revision": 0,
                    "request_id": "wall",
                    "operations": [
                        {
                            "op": "fill",
                            "bounds": {"low": [0, 0, 0], "high": [8, 4, 0]},
                            "state": {"name": "stone"},
                        }
                    ],
                },
            ).raise_for_status()
            browser = pw.chromium.launch(
                channel=os.environ.get("DW_BROWSER_CHANNEL"), headless=True
            )
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url + f"/?project={identifier}")
            page.wait_for_function(
                "window.workbench && !window.workbench.busy && window.workbench.summary?.revision===1"
            )

            def wait(revision: int) -> None:
                page.wait_for_function(
                    "r => !window.workbench.busy && window.workbench.summary.revision===r",
                    arg=revision,
                )

            def material(name: str) -> None:
                page.locator("#search").fill(name)
                page.locator(f'.material-card[data-name="minecraft:{name}"]').click()
                page.wait_for_function(
                    "name => !window.workbench.busy && document.getElementById('material-id').textContent === 'minecraft:' + name",
                    arg=name,
                )
                page.locator('[data-tool="place"]').click()

            def click_wall(x: int, y: int) -> None:
                click = page.evaluate(
                    """([x,y])=>{
                  const v=window.workbench.viewer; v.camera.position.set(4.5,2.5,14);v.controls.target.set(4.5,2.5,.5);v.controls.update();v.drawNow();
                  const p=v.camera.position.clone().set(x+.5,y+.5,1).project(v.camera);
                  const r=v.renderer.domElement.getBoundingClientRect();
                  return [r.x+(p.x+1)*r.width/2,r.y+(1-p.y)*r.height/2];
                }""",
                    [x, y],
                )
                page.mouse.click(*click)

            def state(x: int, y: int) -> dict:
                result = client.post(
                    path + "/inspect", json={"bounds": {"low": [x, y, 1], "high": [x, y, 1]}}
                ).json()
                return result["blocks"][0]

            assert page.locator("#automatic-placement").is_checked()
            material("torch")
            click_wall(0, 1)
            wait(2)
            assert state(0, 1)["name"] == "minecraft:wall_torch"
            assert state(0, 1)["properties"]["facing"] == "south"
            material("ladder")
            click_wall(1, 1)
            wait(3)
            assert state(1, 1)["properties"]["facing"] == "south"
            # An explicit direction switches the shared inspector to manual mode.
            page.locator('[data-variant-property="facing"][data-variant-value="south"]').click()
            assert not page.locator("#automatic-placement").is_checked()
            click_wall(2, 1)
            wait(4)
            assert state(2, 1)["properties"]["facing"] == "south"
            material("oak_sign")
            page.locator("#automatic-placement").check()
            click_wall(3, 1)
            wait(5)
            assert state(3, 1)["name"] == "minecraft:oak_wall_sign"
            assert state(3, 1)["properties"]["facing"] == "south"
            page.locator("#painting-variant").select_option("match")
            page.locator("#choose-painting").click()
            click_wall(5, 1)
            wait(6)
            assert client.get(path).json()["paintings"] == 1
            assert page.evaluate("window.workbench.viewer.paintings.children.length") == 1
            screenshots = root / "artifacts/snap"
            screenshots.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshots / "wall-snap.png"))
            # Sample the actual canvas around the artwork's center. Missing vertex
            # colors on the shared Lambert material used to turn it solid black.
            pixel = page.evaluate(
                """()=>{
                  const v=window.workbench.viewer, p=v.camera.position.clone().set(6,2,1.04).project(v.camera);
                  const r=v.renderer.domElement.getBoundingClientRect();
                  return [r.x+(p.x+1)*r.width/2,r.y+(1-p.y)*r.height/2];
                }"""
            )
            with Image.open(screenshots / "wall-snap.png") as screenshot:
                x, y = map(round, pixel)
                crop = screenshot.convert("RGB").crop((x - 12, y - 12, x + 12, y + 12))
                assert sum(max(rgb) for rgb in crop.getdata()) / (24 * 24) > 30
            with page.expect_download() as download:
                page.locator("#export").click()
            exported = tmp_path / "snap.litematic"
            download.value.save_as(str(exported))
            document = Litematic.parse(exported.read_bytes())
            entities = [
                entry for region in document["Regions"].values() for entry in region["Entities"]
            ]
            assert len(entities) == 1 and str(entities[0]["variant"]) == "minecraft:match"
            page.locator("#undo").click()
            wait(7)
            assert client.get(path).json()["paintings"] == 0
            page.locator("#redo").click()
            wait(8)
            page.reload()
            page.wait_for_function(
                "window.workbench && !window.workbench.busy && window.workbench.viewer.paintings.children.length===1"
            )
            # Raycast into the painting and delete it without deleting its wall.
            page.locator('[data-tool="erase"]').click()
            click_wall(5, 1)
            wait(9)
            assert client.get(path).json()["paintings"] == 0
            assert client.get(path).json()["blocks"] == 49
            assert not errors
            browser.close()
    finally:
        process.terminate()
        process.wait(timeout=10)
