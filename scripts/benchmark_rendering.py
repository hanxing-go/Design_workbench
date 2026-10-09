"""Reproducible Chrome rendering benchmark, with isolated disposable projects.

Run with the project's Python environment. Example::

    python scripts/benchmark_rendering.py --label baseline --quick \
        --static-dir artifacts/performance/baseline-static/ui
    python scripts/benchmark_rendering.py --label optimized --dpr 1 2 \
        --asset .local/imports/azalea-church.litematic

No production project is modified. The 100,000-cell fixture includes opaque,
cutout, translucent and complex stateful blocks; the entire fixture is loaded.
CPU submission is separate from observed requestAnimationFrame intervals.
There is no gl.finish(), FPS cap, hidden-cell limit or resolution reduction.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import platform
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import nbtlib
from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from design_workbench.adapters.formats.litematic import (  # noqa: E402
    Litematic,
    nbt_vector,
    pack_states,
)
from design_workbench.adapters.resources.catalog import Catalog  # noqa: E402
from design_workbench.adapters.storage.sqlite import SqliteStore  # noqa: E402
from design_workbench.domain.models import BlockState  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def distribution(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"samples": 0, "p50_ms": None, "p95_ms": None, "p99_ms": None}
    ordered = sorted(values)

    def percentile(p: float) -> float:
        position = (len(ordered) - 1) * p
        lo, hi = math.floor(position), math.ceil(position)
        return round(ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo), 3)

    return {
        "samples": len(values),
        "p50_ms": percentile(0.50),
        "p95_ms": percentile(0.95),
        "p99_ms": percentile(0.99),
        "max_ms": round(max(values), 3),
        "over_33_4ms": sum(v > 33.4 for v in values),
        "over_50ms": sum(v > 50 for v in values),
        "over_100ms": sum(v > 100 for v in values),
    }


def fixture(path: Path) -> dict[str, Any]:
    """Deterministic town of hollow buildings, floors, windows, roofs and vegetation."""
    registry = Catalog("1.20.1")
    states: dict[str, BlockState] = {}
    cells: dict[tuple[int, int, int], BlockState] = {}

    def state(name: str, **properties: str) -> BlockState:
        value = registry.normalize(BlockState.make(name, properties))
        states[repr(value)] = value
        return value

    stone = state("stone_bricks")
    wood = state("oak_planks")
    brick = state("bricks")
    leaf = state("oak_leaves", persistent="true", distance="1")
    glass = [state(f"{color}_stained_glass") for color in ("blue", "orange", "white", "green")]
    slabs = [state("smooth_stone_slab", type=t) for t in ("top", "bottom", "double")]
    stairs = [
        state("spruce_stairs", facing=f, half=h, shape=s)
        for f in ("east", "west", "north", "south")
        for h in ("top", "bottom")
        for s in ("straight", "inner_left", "outer_right")
    ]
    fences = [
        state(
            "oak_fence",
            north="true",
            south="true",
            east=str(bool(i & 1)).lower(),
            west=str(bool(i & 2)).lower(),
        )
        for i in range(4)
    ]
    panes = [
        state(
            "blue_stained_glass_pane",
            north="true",
            south="true",
            east=str(bool(i & 1)).lower(),
            west=str(bool(i & 2)).lower(),
        )
        for i in range(4)
    ]
    trapdoors = [
        state("oak_trapdoor", facing=f, open="true", half="bottom")
        for f in ("north", "east", "south", "west")
    ]

    for building in range(64):
        bx, bz = (building % 8) * 22, (building // 8) * 22
        height = 24 + building % 3 * 4
        for y in range(height + 8):
            for z in range(16):
                for x in range(16):
                    value = None
                    boundary = x in (0, 15) or z in (0, 15)
                    if y < height and y % 6 == 0:
                        value = wood if y else stone
                    elif y < height and boundary:
                        if 1 <= y % 6 <= 3 and ((x + z) % 5 in (2, 3)):
                            value = (
                                panes[(x + z + building) % 4]
                                if building % 2
                                else glass[(x + z) % 4]
                            )
                        else:
                            value = stone if building % 2 else brick
                    elif y < height and x % 5 == 3 and z % 5 == 3:
                        value = fences[(x + y + z) % 4]
                    elif height <= y < height + 8 and min(x, 15 - x) == y - height:
                        value = stairs[(building + x + z) % len(stairs)]
                    elif y == height + 1 and x in (3, 12) and z in (3, 12):
                        value = leaf
                    elif y < height and y % 6 == 3 and (x + z) % 11 == 0:
                        value = trapdoors[(x + z + building) % 4]
                    elif y < height and y % 6 == 5 and (x + 2 * z) % 13 == 0:
                        value = slabs[(x + z) % 3]
                    if value:
                        cells[(bx + x, y, bz + z)] = value
                    if len(cells) == 100_000:
                        break
                if len(cells) == 100_000:
                    break
            if len(cells) == 100_000:
                break
        if len(cells) == 100_000:
            break
    assert len(cells) == 100_000
    high = tuple(max(point[i] for point in cells) for i in range(3))
    sx, sy, sz = (v + 1 for v in high)
    palette = [BlockState.make("air"), *sorted(set(cells.values()), key=repr)]
    indices = {value: i for i, value in enumerate(palette)}
    sequence = [
        indices.get(cells.get((x, y, z)), 0)
        for y in range(sy)
        for z in range(sz)
        for x in range(sx)
    ]
    entries = []
    for value in palette:
        entry = nbtlib.Compound({"Name": nbtlib.String(value.name)})
        if value.properties:
            entry["Properties"] = nbtlib.Compound(
                {k: nbtlib.String(v) for k, v in value.properties}
            )
        entries.append(entry)
    root = nbtlib.File(
        {
            "Version": nbtlib.Int(6),
            "SubVersion": nbtlib.Int(1),
            "MinecraftDataVersion": nbtlib.Int(3465),
            "Metadata": nbtlib.Compound(
                {
                    "Name": nbtlib.String("Benchmark mixed town 100000 v1"),
                    "Author": nbtlib.String("Design Workbench deterministic fixture"),
                    "TotalBlocks": nbtlib.Int(len(cells)),
                    "EnclosingSize": nbt_vector((sx, sy, sz)),
                }
            ),
            "Regions": nbtlib.Compound(
                {
                    "mixed-town": nbtlib.Compound(
                        {
                            "Position": nbt_vector((0, 0, 0)),
                            "Size": nbt_vector((sx, sy, sz)),
                            "BlockStatePalette": nbtlib.List[nbtlib.Compound](entries),
                            "BlockStates": pack_states(sequence, len(palette)),
                            "Entities": nbtlib.List[nbtlib.Compound]([]),
                            "TileEntities": nbtlib.List[nbtlib.Compound]([]),
                        }
                    )
                }
            ),
        },
        gzipped=True,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    # gzip's wall-clock header is removed from the reproducibility contract.
    raw = io.BytesIO()
    root.write(raw)
    import gzip

    path.write_bytes(gzip.compress(raw.getvalue(), mtime=0))
    return {
        "fixture_version": "mixed-town-v1",
        "non_air_cells": len(cells),
        "bounds": [[0, 0, 0], list(high)],
        "palette_states": len(palette) - 1,
        "materials": dict(sorted(Counter(v.name for v in cells.values()).items())),
        "sha256": digest(path),
    }


INIT = """(() => {
  window.__bench = {longTasks:[], resources:[], renders:[], drawTotals:[], rebuildCalls:[], transparencyFlushes:[], pickCalls:[], updateCalls:[], layerCalls:[],actions:[]};
  new PerformanceObserver(list => {
    for(const e of list.getEntries()) window.__bench.longTasks.push({start:e.startTime,duration:e.duration});
  }).observe({entryTypes:['longtask']});
})();"""

WRAP = """() => {
  const v=window.workbench.viewer,b=window.__bench;
  if(b.wrapped) return;
  b.wrapped=true;
  for(const [object,name,target] of [[v.renderer,'render',b.renders],[v,'drawNow',b.drawTotals],[v,'rebuild',b.rebuildCalls],[v,'flushTransparency',b.transparencyFlushes],[v,'pick',b.pickCalls],[v,'update',b.updateCalls],[v,'setLayer',b.layerCalls]]) {
    const original=object[name];
    object[name]=function(...args) {
      const start=performance.now();
      try{return original.apply(this,args);}finally{target.push({start,duration:performance.now()-start,...(name==='rebuild'?{chunk:args[0]}:{})});}
    };
  }
}"""

MEMORY = """() => {
  const v=window.workbench.viewer,info=v.renderer.info;
  const gl=v.renderer.getContext(),ext=gl.getExtension('WEBGL_debug_renderer_info');
  let geometryBytes=0,objects=0;
  const unique=new Set();
  v.scene.traverse(o=>{objects++;if(o.geometry)unique.add(o.geometry);});
  for(const g of unique){for(const a of Object.values(g.attributes))geometryBytes+=a.array?.byteLength||0;geometryBytes+=g.index?.array?.byteLength||0;}
  return {render:{...info.render},gpu_objects:{...info.memory},scene_objects:objects,
    geometry_cpu_bytes:geometryBytes,chunks:v.chunks.size,models:v.models.size,
    cell_count:[...v.chunks.values()].reduce((n,c)=>n+c.length,0),
    js_heap:performance.memory?{used:performance.memory.usedJSHeapSize,total:performance.memory.totalJSHeapSize,limit:performance.memory.jsHeapSizeLimit}:null,
    canvas:{width:v.renderer.domElement.width,height:v.renderer.domElement.height,dpr:devicePixelRatio},
    gl_renderer:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER),
    gl_vendor:ext?gl.getParameter(ext.UNMASKED_VENDOR_WEBGL):gl.getParameter(gl.VENDOR)};
}"""

FRAMES = (
    """async ({duration,mode}) => {
  const v=window.workbench.viewer,b=window.__bench,start=performance.now();
  const savedPosition=v.camera.position.clone(),savedTarget=v.controls.target.clone();
  const original=v.camera.position.clone().sub(v.controls.target);
  if(mode==='near')v.camera.position.copy(v.controls.target).addScaledVector(original,.32);
  const offset=v.camera.position.clone().sub(v.controls.target),radius=Math.hypot(offset.x,offset.z);
  const originAngle=Math.atan2(offset.z,offset.x),frames=[],renderStart=b.renders.length,drawStart=b.drawTotals.length;
  let previous=null;
  await new Promise(resolve=>{
    function step(now){
      if(previous!==null)frames.push(now-previous);previous=now;
      const elapsed=now-start,angle=originAngle+elapsed/1000*.32;
      v.camera.position.set(v.controls.target.x+Math.cos(angle)*radius,v.controls.target.y+offset.y,
        v.controls.target.z+Math.sin(angle)*radius);
      v.controls.update();v.requestDraw();
      if(elapsed>=duration)resolve();else requestAnimationFrame(step);
    }requestAnimationFrame(step);
  });
  await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
  const end=performance.now();
  const result={frames,cpu:b.renders.slice(renderStart).map(e=>e.duration),draw_total:b.drawTotals.slice(drawStart).map(e=>e.duration),start,end,
    camera_start:{position:savedPosition.toArray(),target:savedTarget.toArray(),mode},
    long_tasks:b.longTasks.filter(e=>e.start>=start&&e.start<=end),memory:("""
    + MEMORY
    + """ )()};
  v.camera.position.copy(savedPosition);v.controls.target.copy(savedTarget);v.controls.update();
  return result;
}"""
)

LAYER_SWEEP = """async ({duration,low,high})=>{
  const v=window.workbench.viewer,b=window.__bench,slider=document.querySelector('#layer');
  const start=performance.now(),frames=[],layers=[],calls=b.layerCalls.length,drawStart=b.drawTotals.length;
  let previous=null,last=high;
  await new Promise(resolve=>{function step(now){
    if(previous!==null)frames.push(now-previous);previous=now;
    const elapsed=now-start,phase=Math.min(1,elapsed/duration);
    const fraction=phase<.5?1-phase*2:(phase-.5)*2;
    const layer=Math.round(low+(high-low)*fraction);
    if(layer!==last){slider.value=String(layer);slider.dispatchEvent(new Event('input',{bubbles:true}));
      layers.push({requested:layer,actual:v.layer,at:performance.now()});last=layer;}
    if(elapsed>=duration)resolve();else requestAnimationFrame(step);
  }requestAnimationFrame(step);});
  const end=performance.now();
  return {frames,layers,start,end,set_layer_calls:b.layerCalls.length-calls,
    draw_total:b.drawTotals.slice(drawStart).map(e=>e.duration),
    long_tasks:b.longTasks.filter(e=>e.start>=start&&e.start<=end)};
}"""


def ready(page: Page, timeout: int = 180_000) -> None:
    page.wait_for_function("window.workbench && !window.workbench.busy", timeout=timeout)
    # New async mesh builders may expose pending work in addition to the rAF handle.
    page.wait_for_function(
        """() => {
      const v=window.workbench.viewer;
      return (!v.drawHandle || window.__interaction?.running) && !(v.pendingBuilds?.size) && !v.building;
    }""",
        timeout=timeout,
    )
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    status = page.locator("#status")
    assert "error" not in (status.get_attribute("class") or ""), status.inner_text()


def timed_click(page: Page, selector: str) -> float:
    browser_start = page.evaluate("performance.now()")
    start = time.perf_counter()
    page.locator(selector).click()
    ready(page)
    elapsed = round((time.perf_counter() - start) * 1000, 3)
    record_action(page, selector, browser_start, elapsed)
    return elapsed


def record_action(page: Page, name: str, start: float, elapsed: float) -> None:
    page.evaluate(
        """({name,start,elapsed})=>{
      const b=window.__bench,end=performance.now();
      b.actions.push({name,start,end,elapsed,
        long_tasks:b.longTasks.filter(e=>e.start>=start&&e.start<=end),
        updates:b.updateCalls.filter(e=>e.start>=start&&e.start<=end),
        layers:b.layerCalls.filter(e=>e.start>=start&&e.start<=end),
        rebuilds:b.rebuildCalls.filter(e=>e.start>=start&&e.start<=end),
        transparency_flushes:b.transparencyFlushes.filter(e=>e.start>=start&&e.start<=end),
        draws:b.drawTotals.filter(e=>e.start>=start&&e.start<=end)});
    }""",
        {"name": name, "start": start, "elapsed": elapsed},
    )


def set_layer(page: Page, layer: int) -> float:
    browser_start = page.evaluate("performance.now()")
    start = time.perf_counter()
    page.locator("#layer").fill(str(layer))
    page.locator("#layer").dispatch_event("input")
    ready(page)
    actual = page.evaluate("window.workbench.viewer.layer")
    assert actual == layer, f"UI slider ignored input: requested Y={layer}, actual Y={actual}"
    elapsed = round((time.perf_counter() - start) * 1000, 3)
    record_action(page, f"layer:{layer}", browser_start, elapsed)
    return elapsed


def correctness(page: Page, source: Path) -> dict[str, Any]:
    if source.suffix == ".dwbench":
        expected = SqliteStore(source).load()
    else:
        expected, _ = Litematic(Catalog("1.20.1"), max_volume=12_000_000).read(source.read_bytes())
    rows = page.evaluate("""() => {
      const v=window.workbench.viewer;
      return [...v.chunks.values()].flat().map(c=>{
        const m=v.models.get(c[3]);return [c[0],c[1],c[2],m?.name,m?.properties];
      });
    }""")
    actual = {tuple(row[:3]): [row[3], row[4]] for row in rows}
    expected_rows = {
        position: [cell.state.name, dict(cell.state.properties)]
        for position, cell in expected.cells.items()
        if not cell.state.is_air
    }
    missing = list(expected_rows.keys() - actual.keys())
    extra = list(actual.keys() - expected_rows.keys())
    wrong = [p for p in actual.keys() & expected_rows.keys() if actual[p] != expected_rows[p]]
    result = {
        "expected_non_air_cells": len(expected_rows),
        "browser_cells": len(rows),
        "unique_browser_positions": len(actual),
        "missing_cells": len(missing),
        "extra_cells": len(extra),
        "wrong_states": len(wrong),
        "sample_failures": [list(p) for p in (missing + extra + wrong)[:10]],
        "all_cell_data_match": not missing and not extra and not wrong and len(rows) == len(actual),
        "source_sha256": digest(source),
        "scope": "every position and complete state; rendering visibility separately sampled/screenshotted",
    }
    assert result["all_cell_data_match"], result
    return result


def geometry_coverage(page: Page) -> dict[str, Any]:
    """Audit that every supported exposed cell actually owns scene geometry.

    This is deliberately separate from the packet-state check: keeping cells
    in a Map while dropping their geometry must fail the benchmark.
    """
    result = page.evaluate("""()=>{
      const v=window.workbench.viewer,key=c=>c.slice(0,3).join(','),cells=[...v.chunks.values()].flat();
      const occupied=new Map(cells.filter(c=>c[1]<=v.layer).map(c=>[key(c),c]));
      const expected=new Set(),actual=new Set(),unsupported=new Map();
      for(const c of occupied.values()){
        const m=v.models.get(c[3]);
        if(!m||m.status!=='static'){const name=m?.name||c[3];unsupported.set(name,(unsupported.get(name)||0)+1);continue;}
        if(m.faces.some(f=>{
          if(!v.atlas.uv[f.texture])return false;
          if(!f.cull)return true;
          const next=occupied.get([c[0]+f.cull[0],c[1]+f.cull[1],c[2]+f.cull[2]].join(','));
          if(!next)return true;
          const n=v.models.get(next[3]);
          if(n?.opaque_cube)return false;
          return !((m.name.includes('glass')||m.name==='minecraft:water'||m.name==='minecraft:lava')&&n?.name===m.name);
        }))expected.add(key(c));
      }
      v.scene.traverse(o=>{if(o.geometry?.attributes.position?.count)
        for(const c of o.userData.cells||[])if(Array.isArray(c))actual.add(key(c));});
      const missing=[...expected].filter(k=>!actual.has(k)),extra=[...actual].filter(k=>!expected.has(k));
      return{layer:Number.isFinite(v.layer)?v.layer:'all',exposed_supported_cells:expected.size,
        geometry_owner_cells:actual.size,missing_geometry_cells:missing.length,unexpected_geometry_cells:extra.length,
        missing_samples:missing.slice(0,10),extra_samples:extra.slice(0,10),
        unsupported:[...unsupported].map(([name,count])=>({name,count})),passed:missing.length===0&&extra.length===0};
    }""")
    assert result["passed"], result
    return result


def raycast_samples(page: Page, limit: int) -> dict[str, Any]:
    # Top-facing model-face centroids also work for thin slabs and stairs.
    probes = page.evaluate(
        """limit => {
      const v=window.workbench.viewer,highest=new Map(),types=new Set(),result=[];
      for(const c of [...v.chunks.values()].flat()){
        const k=c[0]+','+c[2];if(!highest.has(k)||highest.get(k)[1]<c[1])highest.set(k,c);
      }
      for(const c of highest.values()){
        const m=v.models.get(c[3]);if(!m||m.status!=='static'||types.has(m.name))continue;
        const face=m.faces.filter(f=>{const a=f.vertices;return Math.max(a[1],a[4],a[7],a[10])-Math.min(a[1],a[4],a[7],a[10])<1e-5;})
          .sort((a,b)=>b.vertices[1]-a.vertices[1])[0];
        if(!face)continue;
        types.add(m.name);const a=face.vertices;
        result.push({position:c.slice(0,3),name:m.name,
          point:[c[0]+(a[0]+a[3]+a[6]+a[9])/4,c[1]+(a[1]+a[4]+a[7]+a[10])/4,c[2]+(a[2]+a[5]+a[8]+a[11])/4]});
        if(result.length>=limit)break;
      }return result;
    }""",
        limit,
    )
    timed_click(page, '[data-view="top"]')
    canvas = page.locator("#stage canvas")
    saved = page.evaluate("""()=>{const v=window.workbench.viewer;
      return{position:v.camera.position.toArray(),target:v.controls.target.toArray(),up:v.camera.up.toArray()};}""")
    results = []
    for probe in probes:
        point = page.evaluate(
            """point=>{
          const v=window.workbench.viewer;
          v.camera.position.set(point[0],point[1]+80,point[2]);
          v.camera.up.set(0,0,-1);v.controls.target.set(...point);v.controls.update();
          v.camera.updateMatrixWorld();v.requestDraw();
          const T=v.camera.position.constructor,p=new T(...point).project(v.camera);
          const r=v.renderer.domElement.getBoundingClientRect();return{x:(p.x+1)*r.width/2,y:(1-p.y)*r.height/2};
        }""",
            probe["point"],
        )
        box = canvas.bounding_box()
        if not box or not (
            1 < point["x"] < box["width"] - 1 and 1 < point["y"] < box["height"] - 1
        ):
            continue
        start = time.perf_counter()
        canvas.click(position=point)
        ready(page)
        selected = page.evaluate("window.workbench.selection?.low")
        results.append(
            {
                **probe,
                "selected": selected,
                "passed": selected == probe["position"],
                "click_to_ready_ms": round((time.perf_counter() - start) * 1000, 3),
            }
        )
    page.evaluate(
        """saved=>{const v=window.workbench.viewer;v.camera.position.fromArray(saved.position);
      v.controls.target.fromArray(saved.target);v.camera.up.fromArray(saved.up);v.controls.update();v.requestDraw();}""",
        saved,
    )
    ready(page)
    return {"probes": results, "passed": bool(results) and all(r["passed"] for r in results)}


def interaction_benchmark(page: Page, summary: dict[str, Any]) -> dict[str, Any]:
    """Keep the camera moving while exercising ordinary GUI work on 100k cells."""
    page.evaluate("""()=>{
      const v=window.workbench.viewer,t=v.controls.target.clone(),o=v.camera.position.clone().sub(t);
      const radius=Math.hypot(o.x,o.z),angle=Math.atan2(o.z,o.x),start=performance.now();
      const m=window.__interaction={running:true,frames:[],start,last:null};
      function step(now){
        if(!m.running)return;if(m.last!==null)m.frames.push(now-m.last);m.last=now;
        const a=angle+(now-start)/1000*.18;
        v.controls.target.copy(t);v.camera.position.set(t.x+Math.cos(a)*radius,t.y+o.y,t.z+Math.sin(a)*radius);
        v.controls.update();v.requestDraw();requestAnimationFrame(step);
      }requestAnimationFrame(step);
    }""")

    def search(query: str) -> None:
        browser_start = page.evaluate("performance.now()")
        start = time.perf_counter()
        with page.expect_response(
            lambda response: "/api/catalog?" in response.url and f"query={query}" in response.url
        ) as request:
            page.locator("#search").fill(query)
        assert request.value.ok
        ready(page)
        record_action(
            page, "material-search:" + query, browser_start, (time.perf_counter() - start) * 1000
        )

    search("stairs")
    if not page.locator("#next-page").is_disabled():
        timed_click(page, "#next-page")
        timed_click(page, "#prev-page")
    search("oak_stairs")
    timed_click(page, '[data-name="minecraft:oak_stairs"]')
    for name, value in (("facing", "east"), ("half", "top"), ("shape", "inner_left")):
        browser_start = page.evaluate("performance.now()")
        start = time.perf_counter()
        page.locator(f'[data-property="{name}"]').select_option(value)
        ready(page)
        record_action(
            page,
            f"material-property:{name}={value}",
            browser_start,
            (time.perf_counter() - start) * 1000,
        )
    changes = []
    high = summary["occupied_bounds"]["high"]
    low = summary["occupied_bounds"]["low"]
    for step in range(5):
        origin = [high[0] + 10 + step * 12, low[1], low[2]]
        target = [origin[0] + 9, origin[1], origin[2] + 9]
        page.locator("#low").fill(",".join(map(str, origin)))
        page.locator("#high").fill(",".join(map(str, target)))
        timed_click(page, "#select-bounds")
        page.locator("#operation").select_option("fill")
        page.locator("#result-group").fill("interaction-stairs")
        commit_ms = timed_click(page, "#commit")
        assert page.evaluate("window.workbench.summary.blocks") == summary["blocks"] + 100
        for mode, count in (("before", summary["blocks"]), ("current", summary["blocks"] + 100)):
            browser_start = page.evaluate("performance.now()")
            start = time.perf_counter()
            page.locator("#compare").select_option(mode)
            ready(page)
            assert (
                page.evaluate(
                    "[...window.workbench.viewer.chunks.values()].reduce((n,c)=>n+c.length,0)"
                )
                == count
            )
            record_action(
                page, "compare:" + mode, browser_start, (time.perf_counter() - start) * 1000
            )
        undo_ms = timed_click(page, "#undo")
        assert page.evaluate("window.workbench.summary.blocks") == summary["blocks"]
        changes.append(
            {
                "step": step,
                "changed_cells": 100,
                "commit_to_display_ms": commit_ms,
                "undo_to_display_ms": undo_ms,
            }
        )
    # Repeat 1,000-cell patches with extra build/flush timing to diagnose outliers.
    thousand_edits = []
    for step in range(3):
        origin = [high[0] + 10, low[1], low[2]]
        target = [origin[0] + 9, origin[1] + 9, origin[2] + 9]
        page.locator("#low").fill(",".join(map(str, origin)))
        page.locator("#high").fill(",".join(map(str, target)))
        timed_click(page, "#select-bounds")
        commit_ms = timed_click(page, "#commit")
        assert page.evaluate("window.workbench.summary.blocks") == summary["blocks"] + 1000
        undo_ms = timed_click(page, "#undo")
        assert page.evaluate("window.workbench.summary.blocks") == summary["blocks"]
        thousand_edits.append(
            {
                "step": step,
                "changed_cells": 1000,
                "commit_to_display_ms": commit_ms,
                "undo_to_display_ms": undo_ms,
            }
        )
    raw = page.evaluate("""()=>{const m=window.__interaction;m.running=false;const b=window.__bench,end=performance.now();
      return{frames:m.frames,start:m.start,end,long_tasks:b.longTasks.filter(e=>e.start>=m.start&&e.start<=end),
        draw_total:b.drawTotals.filter(e=>e.start>=m.start&&e.start<=end).map(e=>e.duration)};}""")
    raw["raf"] = distribution(raw["frames"])
    raw["draw_total_cpu"] = distribution(raw["draw_total"])
    raw["edits"] = changes
    raw["edits_1000_diagnostic"] = thousand_edits
    ready(page)
    # Repeated real clicks use independently constructed source-face probes.
    probes = [raycast_samples(page, 20) for _ in range(3)]
    assert all(probe["passed"] for probe in probes), probes
    raw["raycast"] = probes
    raw["pick_cpu"] = distribution(page.evaluate("window.__bench.pickCalls.map(e=>e.duration)"))
    raw["ui_actions"] = page.evaluate("window.__bench.actions")
    return raw


def benchmark_scene(
    page: Page, asset: Path, url: str, output: Path, args: argparse.Namespace
) -> dict[str, Any]:
    if asset.suffix == ".dwbench":
        identifier = "benchmark_" + asset.stem
        destination = args.data_dir / "projects" / (identifier + ".dwbench")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(asset) as source_db, sqlite3.connect(destination) as target_db:
            source_db.backup(target_db)
        # Editing measurements need empty margins; only the disposable workspace
        # bounds are expanded. Original cells, states and source metadata stay intact.
        with sqlite3.connect(destination) as target_db:
            metadata = json.loads(
                target_db.execute("SELECT value FROM meta WHERE key='scene'").fetchone()[0]
            )
            metadata["bounds"]["high"][0] += 32
            target_db.execute("UPDATE meta SET value=? WHERE key='scene'", (json.dumps(metadata),))
        start = time.perf_counter()
        page.goto(url + "/?project=" + identifier)
        ready(page)
        initial_ms = round((time.perf_counter() - start) * 1000, 3)
        initial_kind = "project_open_and_display_ms"
        page.evaluate(WRAP)
    else:
        response = page.request.post(
            url + "/api/projects", data={"name": "benchmark-" + asset.stem}
        )
        assert response.ok, response.text()
        identifier = response.json()["project_id"]
        page.goto(url + "/?project=" + identifier)
        ready(page)
        page.evaluate(WRAP)
        page.evaluate("window.__bench.longTasks.length=0;window.__bench.updateCalls.length=0")
        start = time.perf_counter()
        page.locator("#import-file").set_input_files(asset)
        ready(page)
        initial_ms = round((time.perf_counter() - start) * 1000, 3)
        initial_kind = "initial_import_and_display_ms"
    if (
        args.focus
        and page.locator("#focus-mode").count()
        and page.locator("#focus-mode").get_attribute("aria-pressed") != "true"
    ):
        timed_click(page, "#focus-mode")
    # UI changes must not silently change the resolution of a comparison.
    page.evaluate(
        """({width,height})=>{
      const v=window.workbench.viewer,c=v.container;
      c.style.setProperty('width',width+'px','important');
      for(const name of ['height','min-height','max-height'])c.style.setProperty(name,height+'px','important');
      v.resize();
    }""",
        {"width": args.canvas_width, "height": args.canvas_height},
    )
    ready(page)
    report: dict[str, Any] = {
        "asset": str(asset.relative_to(ROOT) if asset.is_relative_to(ROOT) else asset),
        "source_sha256": digest(asset),
        "project_id": identifier,
        "summary": page.evaluate("window.workbench.summary"),
        initial_kind: initial_ms,
        "initial_long_tasks": page.evaluate("window.__bench.longTasks"),
        "initial_update_calls": page.evaluate("window.__bench.updateCalls"),
        "initial_memory": page.evaluate(MEMORY),
        "warnings": page.locator("#warnings").inner_text(),
        "correctness": correctness(page, asset),
        "initial_geometry_coverage": geometry_coverage(page),
        "phases": {},
    }
    actual_renderer = report["initial_memory"]["gl_renderer"]
    assert not any(
        word in actual_renderer.lower() for word in ("swiftshader", "llvmpipe", "software")
    ), actual_renderer
    name = asset.stem + f"-dpr{args.current_dpr}"
    page.screenshot(path=str(output / f"{name}-full.png"))
    if args.interactions_only:
        report["interactions"] = interaction_benchmark(page, report["summary"])
        report["final_correctness"] = correctness(page, asset)
        report["final_geometry_coverage"] = geometry_coverage(page)
        report["post_cycles_memory"] = page.evaluate(MEMORY)
        return report
    duration = args.seconds * 1000
    # First run warms shader/geometry upload and is excluded from steady samples.
    report["warmup"] = page.evaluate(FRAMES, {"duration": 1000, "mode": "orbit"})
    for mode in ("orbit", "near"):
        runs = []
        for _ in range(args.repeats):
            raw = page.evaluate(FRAMES, {"duration": duration, "mode": mode})
            raw["raf"] = distribution(raw["frames"])
            raw["cpu_submission"] = distribution(raw["cpu"])
            raw["draw_total_cpu"] = distribution(raw["draw_total"])
            runs.append(raw)
        report["phases"][mode] = runs
    report["refresh_ms"] = [timed_click(page, "#save") for _ in range(args.repeats)]
    high = report["summary"]["occupied_bounds"]["high"]
    low = report["summary"]["occupied_bounds"]["low"]
    midpoint = (low[1] + high[1]) // 2
    report["cutaway_ms"] = set_layer(page, midpoint)
    report["cutaway_geometry_coverage"] = geometry_coverage(page)
    page.screenshot(path=str(output / f"{name}-cutaway.png"))
    raw = page.evaluate(FRAMES, {"duration": duration, "mode": "orbit"})
    raw["raf"] = distribution(raw["frames"])
    raw["cpu_submission"] = distribution(raw["cpu"])
    raw["draw_total_cpu"] = distribution(raw["draw_total"])
    report["phases"]["cutaway"] = [raw]
    report["restore_layer_ms"] = set_layer(page, high[1])
    sweep = page.evaluate(LAYER_SWEEP, {"duration": duration, "low": low[1], "high": high[1]})
    ready(page)
    assert all(sample["requested"] == sample["actual"] for sample in sweep["layers"])
    assert sweep["set_layer_calls"] >= 2, "continuous slider sweep did not change layer"
    assert page.evaluate("window.workbench.viewer.layer") == high[1]
    sweep["raf"] = distribution(sweep["frames"])
    sweep["draw_total_cpu"] = distribution(sweep["draw_total"])
    report["continuous_layer_sweep"] = sweep
    report["raycast"] = raycast_samples(page, 6 if args.quick else 20)
    assert report["raycast"]["passed"], report["raycast"]
    report["edits"] = {}
    for count in () if args.view_only else (100, 1000):
        # Empty detached region tests changed chunks and makes cell-count assertion exact.
        yspan = 1 if count == 100 else 10
        origin = [high[0] + 10, low[1], low[2]]
        target = [origin[0] + 9, origin[1] + yspan - 1, origin[2] + 9]
        page.locator("#low").fill(",".join(map(str, origin)))
        page.locator("#high").fill(",".join(map(str, target)))
        timed_click(page, "#select-bounds")
        page.locator("#operation").select_option("fill")
        page.locator("#result-group").fill("benchmark-edit")
        preview_ms = timed_click(page, "#preview")
        cancel_ms = timed_click(page, "#cancel-preview")
        assert page.evaluate("window.workbench.summary.blocks") == report["summary"]["blocks"]
        edit_ms = timed_click(page, "#commit")
        assert (
            page.evaluate("window.workbench.summary.blocks") == report["summary"]["blocks"] + count
        )
        memory = page.evaluate(MEMORY)
        undo_ms = timed_click(page, "#undo")
        assert page.evaluate("window.workbench.summary.blocks") == report["summary"]["blocks"]
        report["edits"][str(count)] = {
            "preview_ms": preview_ms,
            "cancel_ms": cancel_ms,
            "commit_to_display_ms": edit_ms,
            "undo_to_display_ms": undo_ms,
            "memory_after_commit": memory,
        }
    cycles = []
    for cycle in range(4 if args.quick else 12):
        browser_start = page.evaluate("performance.now()")
        calls_before = page.evaluate("window.__bench.layerCalls.length")
        start = time.perf_counter()
        # Rapid input tests coalescing and stale-task cancellation, then waits for final state.
        page.evaluate(
            """({low,mid,high})=>{
          const e=document.querySelector('#layer');
          for(const layer of [mid,low,high,mid,high]){e.value=String(layer);e.dispatchEvent(new Event('input',{bubbles:true}));}
        }""",
            {"low": low[1], "mid": midpoint, "high": high[1]},
        )
        ready(page)
        assert page.evaluate("window.workbench.viewer.layer") == high[1]
        calls_after = page.evaluate("window.__bench.layerCalls.length")
        assert calls_after - calls_before >= 5, "rapid UI layer inputs were not executed"
        elapsed = round((time.perf_counter() - start) * 1000, 3)
        record_action(page, f"rapid-layer:{cycle}", browser_start, elapsed)
        cycles.append(
            {
                "cycle": cycle,
                "elapsed_ms": elapsed,
                "set_layer_calls": calls_after - calls_before,
                "memory": page.evaluate(MEMORY),
            }
        )
    report["rapid_layer_cycles"] = cycles
    if args.view_only:
        report["editing_skipped_reason"] = (
            "Supplemental view/pressure test; normal workbench full run verifies edits separately"
        )
    cdp = page.context.new_cdp_session(page)
    report["heap_before_explicit_gc"] = cdp.send("Runtime.getHeapUsage")
    cdp.send("HeapProfiler.collectGarbage")
    report["heap_after_explicit_gc"] = cdp.send("Runtime.getHeapUsage")
    report["post_cycles_memory"] = page.evaluate(MEMORY)
    report["final_correctness"] = correctness(page, asset)
    report["final_geometry_coverage"] = geometry_coverage(page)
    report["instrumented_calls"] = page.evaluate(
        "({updates:window.__bench.updateCalls,layers:window.__bench.layerCalls})"
    )
    report["ui_actions"] = page.evaluate("window.__bench.actions")
    report["final_summary"] = page.evaluate("window.workbench.summary")
    return report


def serve(args: argparse.Namespace) -> None:
    import uvicorn
    from fastapi.staticfiles import StaticFiles

    from design_workbench.config import Settings
    from design_workbench.interfaces.http import create_app

    settings = Settings.load(
        data_dir=args.data_dir,
        cache_dir=args.cache_dir,
        log_dir=Path(args.data_dir) / "logs",
        max_selection_volume=12_000_000,
        max_blocks=args.max_blocks,
    )
    app = create_app(settings)
    if args.static_dir:
        app.router.routes = [
            route for route in app.router.routes if getattr(route, "name", "") != "ui"
        ]
        app.mount("/", StaticFiles(directory=args.static_dir, html=True), name="benchmark-ui")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="current")
    parser.add_argument("--asset", type=Path, action="append", default=[])
    parser.add_argument(
        "--project",
        type=Path,
        action="append",
        default=[],
        help="Copy an explicit pure-rendering benchmark .dwbench, retaining provenance",
    )
    parser.add_argument("--no-fixture", action="store_true")
    parser.add_argument(
        "--interactions-only",
        action="store_true",
        help="Additional ordinary GUI camera/search/edit/compare/pick benchmark",
    )
    parser.add_argument("--canvas-width", type=int, default=922)
    parser.add_argument("--canvas-height", type=int, default=751)
    parser.add_argument(
        "--view-only",
        action="store_true",
        help="Supplemental focus/pressure run without hidden inspector editing inputs",
    )
    parser.add_argument(
        "--focus",
        action="store_true",
        help="Use the product's focus view for a wider render canvas",
    )
    parser.add_argument(
        "--max-blocks",
        type=int,
        default=250_000,
        help="Isolated stress-test server budget; production defaults remain unchanged",
    )
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--seconds", type=float)
    parser.add_argument("--repeats", type=int)
    parser.add_argument("--dpr", type=float, nargs="+", default=[1])
    parser.add_argument("--channel", default="chrome")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument(
        "--url", help="Use an already isolated server; disposable projects are added"
    )
    parser.add_argument("--static-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".local/cache")
    args = parser.parse_args()
    if args.serve:
        serve(args)
        return
    args.seconds = args.seconds or (2 if args.quick else 6)
    args.repeats = args.repeats or (1 if args.quick else 3)
    if args.seconds < 1 or args.repeats < 1:
        parser.error("seconds/repeats must be positive")
    timestamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d-%H%M%S")
    output = (args.output or ROOT / "artifacts/performance" / f"{timestamp}-{args.label}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    args.static_dir = (
        args.static_dir.resolve() if args.static_dir else ROOT / "src/design_workbench/static"
    )
    # Immutable per-run UI snapshot protects against concurrent development builds.
    shutil.copytree(args.static_dir, output / "static", dirs_exist_ok=False)
    shutil.copy2(Path(__file__).resolve(), output / "benchmark-rendering-runner.py")
    args.static_dir = output / "static"
    test_fixture = ROOT / ".local/performance/fixtures/mixed-town-100000-v1.litematic"
    fixture_info = fixture(test_fixture)
    assets = ([] if args.no_fixture else [test_fixture]) + args.asset + args.project
    if not args.asset and not args.project:
        church = ROOT / ".local/imports/azalea-church.litematic"
        if church.exists():
            assets.append(church)
    args.data_dir = output / "data"
    process = None
    url = args.url
    if not url:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            args.port = sock.getsockname()[1]
        url = f"http://127.0.0.1:{args.port}"
        server_log = (output / "server.log").open("w", encoding="utf-8")
        process = subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--serve",
                "--port",
                str(args.port),
                "--data-dir",
                str(args.data_dir),
                "--cache-dir",
                str(args.cache_dir),
                "--static-dir",
                str(args.static_dir),
                "--max-blocks",
                str(args.max_blocks),
            ],
            cwd=ROOT,
            stdout=server_log,
            stderr=subprocess.STDOUT,
        )
        deadline = time.monotonic() + 30
        while True:
            if process.poll() is not None:
                raise RuntimeError(f"Benchmark server failed; inspect {output / 'server.log'}")
            try:
                if httpx.get(url + "/api/info", timeout=1).is_success:
                    break
            except httpx.TransportError:
                pass
            if time.monotonic() > deadline:
                raise TimeoutError("Benchmark server did not start")
            time.sleep(0.1)
    report: dict[str, Any] = {
        "label": args.label,
        "timestamp_asia_shanghai": timestamp,
        "url": url,
        "environment": {
            "os": platform.platform(),
            "python": sys.version,
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "git_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "git_status": subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True),
        "source_hashes": {
            str(p.relative_to(ROOT)): digest(p)
            for p in [
                *ROOT.glob("frontend/src/*.ts"),
                *ROOT.glob("src/design_workbench/adapters/rendering/*.py"),
                *ROOT.glob("src/design_workbench/adapters/storage/*.py"),
                *ROOT.glob("src/design_workbench/application/*.py"),
                ROOT / "src/design_workbench/interfaces/http.py",
                ROOT / "scripts/benchmark_rendering.py",
            ]
        },
        "static_hashes": {
            str(p.relative_to(args.static_dir)): digest(p)
            for p in args.static_dir.rglob("*")
            if p.is_file()
        },
        "resource_info": httpx.get(url + "/api/info", timeout=30).json(),
        "fixture": fixture_info,
        "viewport": {"width": 1440, "height": 1000},
        "canvas_css": {"width": args.canvas_width, "height": args.canvas_height},
        "focus_view": args.focus,
        "view_only": args.view_only,
        "interactions_only": args.interactions_only,
        "benchmark_max_selection_volume": 12_000_000,
        "benchmark_max_blocks": args.max_blocks,
        "mode": "quick" if args.quick else "full",
        "seconds_per_phase": args.seconds,
        "repeats": args.repeats,
        "scenes": [],
        "measurement_limits": [
            "rAF intervals measure browser scheduling and submission; they are not GPU timer-query timings",
            "CPU submission wrapper adds performance.now calls, with raw values retained",
            "longtask observer reports main-thread tasks >50ms; task causality is not implied",
            "renderer.info.memory counts GPU objects, not VRAM bytes; CPU attribute bytes are reported separately",
            "correctness checks all source positions/states plus real UI raycasts and screenshots; screenshots are manually reviewed",
            "explicit GC only follows memory-cycle tests and is excluded from frame measurements",
        ],
    }
    print(
        json.dumps(
            {"output": str(output), "url": url, "fixture": fixture_info}, ensure_ascii=False
        ),
        flush=True,
    )

    def save() -> None:
        (output / "results.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel=args.channel,
                headless=not args.headed,
                args=["--enable-webgl", "--ignore-gpu-blocklist", "--enable-precise-memory-info"],
            )
            report["environment"]["chrome"] = browser.version
            for dpr in args.dpr:
                args.current_dpr = dpr
                context = browser.new_context(
                    viewport=report["viewport"], device_scale_factor=dpr, accept_downloads=True
                )
                context.add_init_script(INIT)
                page = context.new_page()
                page.set_default_timeout(180_000)
                errors: list[str] = []
                page.on("pageerror", lambda error, target=errors: target.append(str(error)))
                for asset in assets:
                    print(f"Benchmarking {asset.name} at DPR {dpr}", flush=True)
                    try:
                        scene_report = benchmark_scene(page, asset.resolve(), url, output, args)
                    except BaseException as error:
                        failure = {"asset": str(asset), "dpr": dpr, "error": repr(error)}
                        try:
                            failure["browser_diagnostics"] = page.evaluate(
                                "({memory:window.workbench?("
                                + MEMORY
                                + ")():null,bench:window.__bench})"
                            )
                            page.screenshot(path=str(output / f"{asset.stem}-dpr{dpr}-failure.png"))
                        except Exception as inspection_error:
                            failure["inspection_error"] = repr(inspection_error)
                        report.setdefault("failed_scenes", []).append(failure)
                        save()
                        raise
                    scene_report["dpr"] = dpr
                    scene_report["page_errors"] = errors.copy()
                    report["scenes"].append(scene_report)
                    save()
                    assert not errors, errors
                    print(
                        json.dumps(
                            {
                                "asset": asset.name,
                                "dpr": dpr,
                                "blocks": scene_report["summary"]["blocks"],
                                "draw_calls": scene_report["initial_memory"]["render"]["calls"],
                                "orbit_raf": scene_report["phases"]
                                .get("orbit", [{}])[0]
                                .get("raf"),
                                "orbit_cpu": scene_report["phases"]
                                .get("orbit", [{}])[0]
                                .get("cpu_submission"),
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                context.close()
            browser.close()
        report["completed"] = True
    except BaseException as error:
        report["completed"] = False
        report["error"] = repr(error)
        raise
    finally:
        save()
        if process:
            process.terminate()
            process.wait(timeout=15)
            server_log.close()
    print(f"Results: {output / 'results.json'}", flush=True)


if __name__ == "__main__":
    main()
