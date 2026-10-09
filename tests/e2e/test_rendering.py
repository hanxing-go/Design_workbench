import io
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import nbtlib
import pytest
from PIL import Image
from playwright.sync_api import sync_playwright

from design_workbench.adapters.formats.litematic import Litematic


@pytest.mark.e2e
def test_special_block_scene_transparency_and_thumbnails(tmp_path: Path) -> None:
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
        with httpx.Client(base_url=url, timeout=30) as client:
            identifier = client.post("/api/projects", json={"name": "特殊方块验收"}).json()[
                "project_id"
            ]
            path = f"/api/projects/{identifier}"
            names = [
                "water",
                "lava",
                "oak_sign",
                "oak_wall_sign",
                "oak_hanging_sign",
                "oak_wall_hanging_sign",
                "red_bed",
                "blue_stained_glass",
                "blue_stained_glass_pane",
                "piston",
            ]
            blocks = [
                {"position": [i * 3, 0, 0], "state": {"name": name}} for i, name in enumerate(names)
            ]
            response = client.post(
                path + "/edit",
                json={
                    "expected_revision": 0,
                    "request_id": "sample",
                    "operations": [{"op": "set", "blocks": blocks}],
                },
            )
            assert response.status_code == 200
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    channel=os.environ.get("DW_BROWSER_CHANNEL"), headless=True
                )
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(url + f"/?project={identifier}")
                page.wait_for_function(
                    "window.workbench && !window.workbench.busy && window.workbench.viewer.models.size >= 10"
                )
                # Drawing batches are independent of the number of blocks. Every
                # sample must still own actual render geometry after batching.
                assert page.evaluate("""() => {
                  const v=window.workbench.viewer, rendered=new Set();
                  const collect=o=>{for(const c of o.userData.cells??[])rendered.add(c.slice(0,3).join(','));};
                  for(const group of v.meshes.values())group.traverse(collect);
                  if(v.transparency)collect(v.transparency.mesh);
                  return [...Array(10)].every((_,i)=>rendered.has(`${i*3},0,0`));
                }""")
                assert page.evaluate(
                    "window.workbench.viewer.translucent.transparent && !window.workbench.viewer.translucent.depthWrite"
                )
                assert page.evaluate(
                    "[...window.workbench.viewer.models.values()].every(m=>m.status==='static')"
                )
                screenshot = root / "artifacts/render-fixes"
                screenshot.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(screenshot / "special-blocks.png"))
                # Render one pane, then an opaque marker behind it: alpha blending must
                # reveal that marker. Using the same geometry avoids camera/lighting noise.
                pixel_data = page.evaluate("""async () => {
                  const v=window.workbench.viewer;
                  const model=await (await fetch('/api/material/blue_stained_glass')).json();
                  const packet=(id,m,cells) => ({revision:0,summary:{occupied_bounds:null},
                    chunks:{'0,0,0':cells},removed_chunks:[...v.chunks.keys()].filter(k=>k!=='0,0,0'),
                    chunk_versions:{},models:{[id]:m},atlas:model.atlas});
                  v.update(packet('test',model,[[0,0,0,'test','main',false]]));
                  await v.whenReady();
                  v.camera.position.set(.5,.5,4); v.controls.target.set(.5,.5,.5); v.controls.update();
                  v.drawNow();
                  const before=v.renderer.domElement.toDataURL();
                  const marked={...model,render_layer:'opaque',faces:model.faces.map(f=>({...f,color:'#ff3030'}))};
                  const p=packet('test',model,[[0,0,0,'test','main',false],[0,0,-1,'marker','main',false]]);
                  p.models.marker=marked; v.update(p); await v.whenReady(); v.drawNow();
                  return {before,after:v.renderer.domElement.toDataURL(),thumbnail:v.thumbnail(model)};
                }""")
                import base64

                def center(data: str) -> tuple[int, ...]:
                    image = Image.open(io.BytesIO(base64.b64decode(data.split(",")[1]))).convert(
                        "RGB"
                    )
                    return image.getpixel((image.width // 2, image.height // 2))

                assert (
                    sum(
                        abs(a - b)
                        for a, b in zip(
                            center(pixel_data["before"]), center(pixel_data["after"]), strict=True
                        )
                    )
                    > 10
                )
                for name, data in pixel_data.items():
                    (screenshot / f"glass-{name}.png").write_bytes(
                        base64.b64decode(data.split(",")[1])
                    )
                # Sorting uses translated objects rather than all instances at the origin.
                assert page.evaluate(
                    "[...window.workbench.viewer.meshes.values()][0].children.filter(m=>m.material.transparent).every(m=>m.count===1)"
                )
                page.reload()
                page.wait_for_function(
                    "window.workbench && !window.workbench.busy && window.workbench.summary?.blocks===10"
                )
                page.locator("#search").fill("blue_bed")
                page.locator('.material-card[data-name="minecraft:blue_bed"]').click()
                page.locator('select[data-property="part"]').select_option("foot")
                page.locator('select[data-property="facing"]').select_option("north")
                page.locator('[data-tool="place"]').click()
                click = page.evaluate("""() => {
                  const v=window.workbench.viewer;
                  v.camera.position.set(4,15,15); v.controls.target.set(4,0,4); v.controls.update(); v.drawNow();
                  const p=v.camera.position.clone().set(4.5,0,4.5).project(v.camera);
                  const r=v.renderer.domElement.getBoundingClientRect();
                  return [r.x+(p.x+1)*r.width/2,r.y+(1-p.y)*r.height/2];
                }""")
                page.mouse.click(*click)
                page.wait_for_function(
                    "!window.workbench.busy && window.workbench.summary.blocks===12"
                )
                rendered = client.post(path + "/render").json()
                beds = [m for m in rendered["models"].values() if m["name"] == "minecraft:blue_bed"]
                assert {b["properties"]["part"] for b in beds} == {"head", "foot"}
                page.evaluate(
                    """() => {const v=window.workbench.viewer; v.camera.position.set(7,3,7); v.controls.target.set(4.5,.2,4); v.controls.update();v.drawNow();}"""
                )
                page.locator("#stage canvas").screenshot(path=str(screenshot / "paired-bed.png"))
                # Import actual NBT sign content through the public API, then verify its
                # read-only front/back text meshes and preserved export content.
                exported = client.post(path + "/export", json={"expected_revision": 2}).content
                document = Litematic.parse(exported)
                region = next(iter(document["Regions"].values()))
                entry = nbtlib.Compound(
                    {
                        "id": nbtlib.String("minecraft:sign"),
                        "x": nbtlib.Int(6),
                        "y": nbtlib.Int(0),
                        "z": nbtlib.Int(0),
                    }
                )
                for side, text in (("front_text", "正面文字"), ("back_text", "Back")):
                    entry[side] = nbtlib.Compound(
                        {
                            "messages": nbtlib.List[nbtlib.String](
                                [nbtlib.String('"' + text + '"')]
                            ),
                            "color": nbtlib.String("black"),
                        }
                    )
                region["TileEntities"] = nbtlib.List[nbtlib.Compound]([entry])
                stream = io.BytesIO()
                document.write(stream)
                imported = client.post(
                    path + "/import",
                    data={"expected_revision": 2, "request_id": "sign-text"},
                    files={"file": ("sign.litematic", stream.getvalue())},
                )
                assert imported.status_code == 200
                page.reload()
                page.wait_for_function(
                    "window.workbench && !window.workbench.busy && [...window.workbench.viewer.meshes.values()].some(g=>g.children.some(m=>m.userData.signText))"
                )
                assert page.evaluate(
                    "[...window.workbench.viewer.models.values()].some(m=>m.texts?.[0].lines[0]==='正面文字' && m.texts?.[1].lines[0]==='Back')"
                )
                for name, z in (("front", 3), ("back", -2)):
                    page.evaluate(
                        """(z) => {const v=window.workbench.viewer;v.camera.position.set(6.5,.82,z);v.controls.target.set(6.5,.82,.5);v.controls.update();v.drawNow();}""",
                        z,
                    )
                    page.locator("#stage canvas").screenshot(
                        path=str(screenshot / f"sign-{name}.png")
                    )
                roundtrip = Litematic.parse(
                    client.post(path + "/export", json={"expected_revision": 3}).content
                )
                assert next(iter(roundtrip["Regions"].values()))["TileEntities"][0] == entry
                assert not errors
                browser.close()
    finally:
        process.terminate()
        process.wait(timeout=10)
