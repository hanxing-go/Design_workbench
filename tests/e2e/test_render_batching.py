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
                channel=os.environ.get("DW_BROWSER_CHANNEL"), headless=True
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


@pytest.mark.e2e
def test_leaf_instance_picking_keeps_group_protection_and_layer_visibility(
    batching_page: tuple[Page, list[str]],
) -> None:
    page, _ = batching_page
    result = page.evaluate("""async () => {
      const v=window.workbench.viewer;
      const leaves=await (await fetch('/api/material/oak_leaves')).json();
      const cells=[[15,15,2,'leaf','lower',false],[16,16,2,'leaf','upper',true]];
      v.update({revision:0,resource_hash:v.resourceHash,summary:{occupied_bounds:null},
        chunks:{'0,0,0':[cells[0]],'1,1,0':[cells[1]]},
        removed_chunks:[...v.chunks.keys()].filter(k=>!['0,0,0','1,1,0'].includes(k)),
        chunk_versions:{},models:{leaf:leaves},atlas:leaves.atlas});
      await v.whenReady();
      const pick=cell=>{
        const center=v.camera.position.clone().set(cell[0]+.5,cell[1]+.5,cell[2]+.5);
        v.controls.target.copy(center);v.camera.position.copy(center);v.camera.position.z+=5;
        v.controls.update();v.camera.updateMatrixWorld();v.drawNow();
        const rect=v.renderer.domElement.getBoundingClientRect();
        return v.pick(new PointerEvent('pointerup',{
          clientX:rect.x+rect.width/2,clientY:rect.y+rect.height/2}));
      };
      const original=cells.map(pick);
      const upper=v.meshes.get('1,1,0').children.find(object=>object.isInstancedMesh);
      let instanceDisposed=0,geometryDisposed=0;
      upper.addEventListener('dispose',()=>instanceDisposed++);
      upper.geometry.addEventListener('dispose',()=>geometryDisposed++);
      v.setLayer(15);await v.whenReady();
      const hidden=pick(cells[1]);
      v.setLayer(Infinity);await v.whenReady();
      return {original,hidden,restored:cells.map(pick),
        instanceDisposed,geometryDisposed};
    }""")
    for hits in (result["original"], result["restored"]):
        assert [hit["position"] for hit in hits] == [[15, 15, 2], [16, 16, 2]]
        assert [hit["group"] for hit in hits] == ["lower", "upper"]
        assert [hit["protected"] for hit in hits] == [False, True]
        assert all(hit["normal"] == [0, 0, 1] for hit in hits)
    assert result["hidden"] is None
    assert result["instanceDisposed"] == result["geometryDisposed"] == 1


@pytest.mark.e2e
def test_opaque_edits_reuse_transparency_but_state_owners_and_culling_invalidate_it(
    batching_page: tuple[Page, list[str]],
) -> None:
    page, _ = batching_page
    result = page.evaluate("""async () => {
      const v=window.workbench.viewer;
      const names=['blue_stained_glass','red_stained_glass','stone','bricks'];
      const models=Object.fromEntries(await Promise.all(names.map(async name=>
        [name,await (await fetch('/api/material/'+name)).json()])));
      let glass=[15,0,2,'blue_stained_glass','original',false];
      let opaque=[[17,0,2,'stone','opaque',false]];
      const update=async()=>{
        const chunks={'1,0,0':opaque};if(glass)chunks['0,0,0']=[glass];
        v.update({revision:0,resource_hash:v.resourceHash,summary:{occupied_bounds:null},
          chunks,removed_chunks:[...v.chunks.keys()].filter(k=>!(k in chunks)),
          chunk_versions:{},models,atlas:models.stone.atlas});
        await v.whenReady();v.drawNow();return v.transparency;
      };
      const first=await update(),full=first.mesh.geometry.attributes.position.count;
      opaque=[[17,0,2,'bricks','edited',false]];
      const reused=await update()===first;
      glass=[15,0,2,'blue_stained_glass','updated',true];
      const changedOwner=await update(),ownerRebuilt=changedOwner!==first;
      const center=v.camera.position.clone().set(15.5,.5,2.5);
      v.controls.target.copy(center);v.camera.position.copy(center);v.camera.position.z+=5;
      v.controls.update();v.camera.updateMatrixWorld();v.drawNow();
      const rect=v.renderer.domElement.getBoundingClientRect();
      const hit=v.pick(new PointerEvent('pointerup',{
        clientX:rect.x+rect.width/2,clientY:rect.y+rect.height/2}));
      glass=[15,0,2,'red_stained_glass','updated',true];
      const changedState=await update(),stateRebuilt=changedState!==changedOwner;
      opaque=[...opaque,[16,0,2,'stone','occluder',false]];
      const hidden=await update(),hiddenCount=hidden.mesh.geometry.attributes.position.count;
      opaque=opaque.slice(0,-1);
      const revealed=await update(),revealedCount=revealed.mesh.geometry.attributes.position.count;
      glass=null;await update();
      return {reused,ownerRebuilt,stateRebuilt,hit,full,hiddenCount,revealedCount,
        neighbourRebuilt:hidden!==changedState&&revealed!==hidden,
        removed:v.transparency===null};
    }""")
    assert result["reused"] and result["ownerRebuilt"] and result["stateRebuilt"]
    assert result["hit"]["position"] == [15, 0, 2]
    assert result["hit"]["group"] == "updated" and result["hit"]["protected"]
    assert result["neighbourRebuilt"]
    assert result["hiddenCount"] == result["full"] - 6
    assert result["revealedCount"] == result["full"]
    assert result["removed"]
    assert page.evaluate(OWNER_POINTS) == ["17,0,2"]


@pytest.mark.e2e
def test_rebuilt_sign_text_replaces_merged_texture_even_when_glass_is_unchanged(
    batching_page: tuple[Page, list[str]],
) -> None:
    page, _ = batching_page
    result = page.evaluate("""async () => {
      const v=window.workbench.viewer;
      const [glass,sign,stone,bricks]=await Promise.all(
        ['blue_stained_glass','oak_sign','stone','bricks'].map(async name=>
          await (await fetch('/api/material/'+name)).json()));
      let text='before',opaque='stone';
      const update=async()=>{
        const models={glass,stone,bricks,sign:{...sign,
          texts:[{lines:[text,'','',''],color:'black',glowing:false}]}};
        v.update({revision:0,resource_hash:v.resourceHash,summary:{occupied_bounds:null},
          chunks:{'0,0,0':[[0,0,2,'glass','glass',false],[2,0,2,'sign','sign',false],
            [4,0,2,opaque,'opaque',false]]},
          removed_chunks:[...v.chunks.keys()].filter(k=>k!=='0,0,0'),
          chunk_versions:{},models,atlas:glass.atlas});
        await v.whenReady();v.drawNow();return v.transparency;
      };
      const first=await update();
      const oldText=v.meshes.get('0,0,0').children.find(o=>o.userData.signText);
      let textureDisposed=0;oldText.material.map.addEventListener('dispose',()=>textureDisposed++);
      opaque='bricks';const second=await update();
      const currentText=v.meshes.get('0,0,0').children.find(o=>o.userData.signText);
      const textureInMerged=second.mesh.material.some(m=>m.map===currentText.material.map);
      const before=currentText.material.map.image.toDataURL();
      text='after';const third=await update();
      const nextText=v.meshes.get('0,0,0').children.find(o=>o.userData.signText);
      const after=nextText.material.map.image.toDataURL();
      v.update({revision:0,resource_hash:v.resourceHash,summary:{occupied_bounds:null},
        chunks:{'0,0,0':[[0,0,2,'glass','glass',false]]},removed_chunks:[],
        chunk_versions:{},models:{glass},atlas:glass.atlas});
      await v.whenReady();v.drawNow();
      return {rebuilt:first!==second&&second!==third,textureDisposed,textureInMerged,
        textChanged:before!==after,onlyGlass:v.transparency.mesh.material.length===1};
    }""")
    assert result["rebuilt"] and result["textureDisposed"] == 1
    assert result["textureInMerged"] and result["textChanged"] and result["onlyGlass"]
    assert page.evaluate(OWNER_POINTS) == ["0,0,2"]
