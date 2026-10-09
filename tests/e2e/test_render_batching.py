"""Exercise async rendering, state ownership and resource invalidation in real Chrome."""

import io
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from PIL import Image
from playwright.sync_api import Page, sync_playwright


@pytest.fixture
def batching_page(tmp_path: Path) -> Iterator[tuple[Page, list[str]]]:
    root = Path(__file__).resolve().parents[2]
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
        deadline = time.monotonic() + 25
        while True:
            assert process.poll() is None
            try:
                info = httpx.get(url + "/api/info", timeout=1)
                if info.is_success:
                    if not info.json()["resources_ready"]:
                        pytest.skip(
                            "Install official Minecraft resources before running browser tests"
                        )
                    break
            except httpx.TransportError:
                pass
            assert time.monotonic() < deadline
            time.sleep(0.1)
        with httpx.Client(base_url=url, timeout=30) as client:
            identifier = client.post("/api/projects", json={"name": "异步分块验收"}).json()[
                "project_id"
            ]
            blocks = [
                {"position": [x, y, 2], "state": {"name": name}}
                for y in range(19)
                for x, name in [
                    (14, "blue_stained_glass"),
                    (15, "red_stained_glass"),
                    (16, "glass"),
                    (17, "stone"),
                ]
            ]
            response = client.post(
                f"/api/projects/{identifier}/edit",
                json={
                    "expected_revision": 0,
                    "request_id": "cross-chunk-fixture",
                    "operations": [{"op": "set", "blocks": blocks}],
                },
            )
            assert response.is_success, response.text
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel=os.environ.get("DW_BROWSER_CHANNEL", "chrome"), headless=True
            )
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url + f"/?project={identifier}")
            settled(page)
            assert page.evaluate("window.workbench.summary.blocks") == 76
            yield page, errors
            assert not errors
            browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def settled(page: Page) -> None:
    page.wait_for_function("window.workbench && !window.workbench.busy", timeout=30_000)
    page.evaluate("window.workbench.viewer.whenReady()")
    page.wait_for_function(
        "!window.workbench.viewer.building && !window.workbench.viewer.pendingBuilds.size"
    )
    page.evaluate(
        "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
    )


OWNER_POINTS = """() => {
  const v=window.workbench.viewer, points=new Set();
  const collect=o=>{for(const cell of o.userData.cells??[])points.add(cell.slice(0,3).join(','));};
  for(const group of v.meshes.values())if(group.visible)group.traverse(collect);
  if(v.transparency)collect(v.transparency.mesh);
  return [...points].sort();
}"""


@pytest.mark.e2e
def test_layer_rebuild_coalesces_and_restores_cross_chunk_owners(
    batching_page: tuple[Page, list[str]],
) -> None:
    page, _ = batching_page
    expected = {f"{x},{y},2" for y in range(19) for x in (14, 15, 16, 17)}
    assert set(page.evaluate(OWNER_POINTS)) == expected
    # All inputs arrive before the first build rAF: the final cutoff must win.
    page.evaluate("""() => {
      const slider=document.querySelector('#layer');
      for(const y of [0,18,15,17,1,16]){
        slider.value=String(y);slider.dispatchEvent(new Event('input',{bubbles:true}));
      }
    }""")
    settled(page)
    assert page.evaluate("window.workbench.viewer.layer") == 16
    assert set(page.evaluate(OWNER_POINTS)) == {
        f"{x},{y},2" for y in range(17) for x in (14, 15, 16, 17)
    }
    page.locator("#layer-reset").click()
    settled(page)
    assert page.evaluate("window.workbench.viewer.layer===Infinity")
    assert set(page.evaluate(OWNER_POINTS)) == expected
    # Rotate and pick opaque / translucent faces across X and Y chunk boundaries.
    samples = page.evaluate("""() => {
      const v=window.workbench.viewer;
      return [[14,16,2],[15,15,2],[16,17,2],[17,18,2]].map(p=>{
        const center=v.camera.position.clone().set(p[0]+.5,p[1]+.5,p[2]+.5);
        v.controls.target.copy(center);v.camera.position.copy(center).addScalar(0);
        v.camera.position.z+=5;v.controls.update();v.camera.updateMatrixWorld();v.drawNow();
        const screen=center.clone().project(v.camera),rect=v.renderer.domElement.getBoundingClientRect();
        return v.pick(new PointerEvent('pointerup',{clientX:rect.x+(screen.x+1)*rect.width/2,
          clientY:rect.y+(1-screen.y)*rect.height/2}));
      });
    }""")
    for point, sample in zip(
        [(14, 16, 2), (15, 15, 2), (16, 17, 2), (17, 18, 2)], samples, strict=True
    ):
        assert sample["position"] == list(point)
        assert sample["normal"] == [0, 0, 1]


@pytest.mark.e2e
def test_queued_scene_replacement_and_resource_hash_discard_stale_geometry(
    batching_page: tuple[Page, list[str]],
) -> None:
    page, _ = batching_page
    result = page.evaluate("""async () => {
      const v=window.workbench.viewer;
      const models=await Promise.all(['blue_stained_glass','red_stained_glass','stone'].map(async n=>
        await (await fetch('/api/material/'+n)).json()));
      const [blue,red,stone]=models;
      const packet=(hash,model,chunk,point)=>({revision:0,resource_hash:hash,
        summary:{occupied_bounds:null},chunks:{[chunk]:[[...point,'shared-id','probe',false]]},
        removed_chunks:[...v.chunks.keys()].filter(k=>k!==chunk),chunk_versions:{},
        models:{'shared-id':model},atlas:blue.atlas});
      // Initial work is queued; resource replacement must not resurrect its old chunks.
      v.setLayer(16);
      v.update(packet('probe-resource-a',blue,'0,0,0',[0,0,0]));
      v.update(packet('probe-resource-b',red,'1,0,0',[16,0,0]));
      await v.whenReady();
      const modelName=v.models.get('shared-id').name;
      const firstGeometry=v.geometryCache.get('shared-id:'+ '1'.repeat(red.faces.length));
      const hashB=v.resourceHash;
      v.update(packet('probe-resource-c',stone,'2,0,0',[32,0,0]));
      await v.whenReady();v.drawNow();
      const secondGeometry=v.geometryCache.get('shared-id:'+ '1'.repeat(stone.faces.length));
      return {modelName,hashB,hashC:v.resourceHash,
        finalModel:v.models.get('shared-id').name,
        cachedGeometryChanged:firstGeometry!==secondGeometry,
        chunks:[...v.chunks.keys()],meshes:[...v.meshes.keys()],
        occupancy:[...v.occupied().keys()],building:v.building,pending:v.pendingBuilds.size};
    }""")
    settled(page)
    assert result["modelName"] == "minecraft:red_stained_glass"
    assert result["hashB"] == "probe-resource-b"
    assert result["hashC"] == "probe-resource-c"
    assert result["finalModel"] == "minecraft:stone"
    assert result["cachedGeometryChanged"]
    assert result["chunks"] == result["meshes"] == ["2,0,0"]
    assert result["occupancy"] == ["32,0,0"]
    assert not result["building"] and result["pending"] == 0
    assert page.evaluate("window.workbench.viewer.transparency===null")
    assert page.evaluate(OWNER_POINTS) == ["32,0,0"]


@pytest.mark.e2e
def test_resource_hash_refreshes_atlas_and_disposes_replaced_texture(
    batching_page: tuple[Page, list[str]],
) -> None:
    page, _ = batching_page
    colors = {"atlas-red": (220, 30, 20, 255), "atlas-blue": (20, 30, 220, 255)}
    pngs = {}
    for name, color in colors.items():
        buffer = io.BytesIO()
        Image.new("RGBA", (2, 2), color).save(buffer, format="PNG")
        pngs[name] = buffer.getvalue()
    page.route(
        "**/api/atlas.png?resource_hash=*",
        lambda route: route.fulfill(
            content_type="image/png", body=pngs[route.request.url.split("=")[-1]]
        ),
    )
    result = page.evaluate("""async () => {
      const v=window.workbench.viewer;
      const stone=await (await fetch('/api/material/stone')).json();
      const packet=hash=>({revision:0,resource_hash:hash,summary:{occupied_bounds:null},
        chunks:{'0,0,0':[[0,0,0,'stone','main',false]]},removed_chunks:[],
        chunk_versions:{},models:{stone},atlas:stone.atlas});
      const read=()=>{
        const canvas=document.createElement('canvas');canvas.width=canvas.height=2;
        const context=canvas.getContext('2d');context.drawImage(v.texture.image,0,0);
        return [...context.getImageData(0,0,1,1).data];
      };
      const original=v.texture;let originalDisposed=0;
      original.addEventListener('dispose',()=>originalDisposed++);
      v.update(packet('atlas-red'));await v.whenReady();v.drawNow();
      const red=read(),previous=v.texture;let previousDisposed=0;
      previous.addEventListener('dispose',()=>previousDisposed++);
      v.update(packet('atlas-blue'));await v.whenReady();v.drawNow();
      return {red,blue:read(),originalDisposed,previousDisposed,
        sameMap:[v.material,v.translucent,v.sortedMaterial,v.emissive]
          .every(material=>material.map===v.texture),
        hash:v.resourceHash,thumbnailCount:v.thumbnails.size};
    }""")
    assert result["red"] == list(colors["atlas-red"])
    assert result["blue"] == list(colors["atlas-blue"])
    assert result["originalDisposed"] == result["previousDisposed"] == 1
    assert result["sameMap"] and result["hash"] == "atlas-blue"
    assert result["thumbnailCount"] == 0
    assert page.evaluate(OWNER_POINTS) == ["0,0,0"]
