"""Pixel-level regression for renderer batching against an immutable old UI.

Same current backend, immutable database copies, Chrome, DPR=1, canvas 922x751,
exact camera matrices and fixed atlas. A full pixel comparison is reported;
only channel differences <=3 count as minor antialiasing tolerance.
The script never edits production projects or changes production budgets.

NumPy is the existing nbtlib runtime dependency, pinned to 2.5.3 in uv.lock;
``uv sync --locked --group dev --extra gui`` installs it without a new optional
dependency. Image comparison also uses Pillow and Playwright from existing gui
and dev groups. No dependency manifest change is needed for this verifier.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import json
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx
import nbtlib
import numpy as np
from PIL import Image
from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from benchmark_rendering import ready, serve  # noqa: E402

from design_workbench.adapters.formats.litematic import Litematic  # noqa: E402
from design_workbench.adapters.resources.catalog import Catalog  # noqa: E402
from design_workbench.adapters.storage.sqlite import SqliteStore  # noqa: E402
from design_workbench.domain.models import Bounds, Cell, Scene  # noqa: E402


def probe(path: Path, with_text: bool = True) -> None:
    catalog = Catalog()
    scene = Scene(
        "probe", "透明排序与文字像素回归", "1.20.1", 3465, 0, Bounds((8, 0, -3), (26, 12, 20))
    )

    def put(point: tuple[int, int, int], name: str, **properties: str) -> None:
        scene.cells[point] = Cell(
            catalog.normalize(catalog.default(name).__class__.make(name, properties))
        )

    for x in range(9, 25):
        for z in range(0, 19):
            put((x, 0, z), "smooth_stone")
    # Alternating differently colored touching glass, crossing X=16 chunk boundary.
    for z, color in [(2, "blue"), (4, "red"), (6, "lime"), (8, "orange")]:
        for x in range(12, 21):
            for y in range(1, 7):
                put((x, y, z), f"{color}_stained_glass")
    for x in range(13, 21):
        for y in range(1, 6):
            put(
                (x, y, 11),
                "cyan_stained_glass_pane",
                north="false",
                south="false",
                east="true",
                west="true",
                waterlogged="false",
            )
    # Half-height solids and panes interleaved with visible fluid surfaces.
    for x in range(13, 20):
        put((x, 1, 14), "smooth_stone_slab", type="bottom", waterlogged="false")
        put((x, 2, 14), "smooth_stone_slab", type="top", waterlogged="false")
        put((x, 1, 16), "water", level="0")
        put((x, 2, 16), "light_blue_stained_glass")
    for x in range(11, 23):
        put((x, 1, 18), "glass")
    # Two text-bearing signs: behind and in front of translucent layers.
    put((15, 3, 10), "oak_wall_sign", facing="south", waterlogged="false")
    put((21, 3, 17), "spruce_wall_sign", facing="south", waterlogged="false")
    payload, _ = Litematic(catalog).write(scene)
    root = Litematic.parse(payload)
    region = next(iter(root["Regions"].values()))
    # Newly authored region's minimum is x=9,y=0,z=0.
    text_entries = (
        [((15, 3, 10), "BEHIND GLASS", "blue"), ((21, 3, 17), "FRONT GLASS", "red")]
        if with_text
        else []
    )
    for point, text, color in text_entries:
        region["TileEntities"].append(
            nbtlib.Compound(
                {
                    "x": nbtlib.Int(point[0] - 9),
                    "y": nbtlib.Int(point[1]),
                    "z": nbtlib.Int(point[2]),
                    "id": nbtlib.String("minecraft:sign"),
                    "front_text": nbtlib.Compound(
                        {
                            "messages": nbtlib.List[nbtlib.String](
                                [
                                    json.dumps({"text": text}),
                                    '"CHUNK 16"',
                                    '"Minecraft"',
                                    '"ABCDEFG"',
                                ]
                            ),
                            "color": nbtlib.String(color),
                            "has_glowing_text": nbtlib.Byte(1),
                        }
                    ),
                    "back_text": nbtlib.Compound(
                        {
                            "messages": nbtlib.List[nbtlib.String](['"BACK"', '""', '""', '""']),
                            "color": nbtlib.String("black"),
                            "has_glowing_text": nbtlib.Byte(0),
                        }
                    ),
                }
            )
        )
    output = io.BytesIO()
    root.write(output)
    source = gzip.compress(output.getvalue(), mtime=0)
    imported, _ = Litematic(catalog).read(source)
    store = SqliteStore.create(path, imported.name, "1.20.1", 3465, imported.bounds)
    imported.id = store.load().id
    store.commit(
        imported,
        [(point, None, cell) for point, cell in imported.cells.items()],
        0,
        "visual-fixture",
        hashlib.sha256(source).hexdigest(),
        attachment=source,
    )


def copy_project(source: Path, destination: Path) -> None:
    with sqlite3.connect(source) as original, sqlite3.connect(destination) as copied:
        original.backup(copied)


def launch(
    static: Path, data: Path, output: Path, cache: Path
) -> tuple[subprocess.Popen, str, Any]:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    log = output.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--serve",
            "--static-dir",
            str(static),
            "--data-dir",
            str(data),
            "--cache-dir",
            str(cache),
            "--port",
            str(port),
        ],
        cwd=ROOT,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    started = time.monotonic()
    while time.monotonic() - started < 30:
        if process.poll() is not None:
            raise RuntimeError(f"Visual server failed: {output}")
        try:
            if httpx.get(url + "/api/info", timeout=1).is_success:
                return process, url, log
        except httpx.TransportError:
            pass
        time.sleep(0.1)
    process.terminate()
    raise TimeoutError("Visual server startup")


def capture(page: Page, url: str, identifier: str, target: Path) -> list[dict[str, Any]]:
    page.goto(url + "/?project=" + identifier)
    ready(page)
    page.evaluate("""() => {
      const v=window.workbench.viewer,c=v.container;
      // Product UI themes may change the default clear color. Geometry QA uses
      // the original fixed background in both renderers so that theme changes
      // do not masquerade as voxel regressions.
      v.renderer.setClearColor('#eef2f2');
      // Grid colors are likewise theme-specific UI defaults. Keep the original
      // two vertex colors exactly for geometry comparison, with the grid visible.
      const grid=v.scene.children.find(object=>object.type==='GridHelper');
      if(grid){
        const Color=v.scene.background?.constructor??v.material.color.constructor;
        const minor=new Color('#d6dfda'),major=new Color('#b1beb9');
        const colors=grid.geometry.attributes.color;
        for(let i=0;i<colors.count;i++)colors.setXYZ(i,minor.r,minor.g,minor.b);
        for(let i=64*4;i<64*4+4;i++)colors.setXYZ(i,major.r,major.g,major.b);
        colors.needsUpdate=true;
      }
      c.style.setProperty('width','922px','important');
      for(const name of ['height','min-height','max-height'])c.style.setProperty(name,'751px','important');
      v.resize();v.showSelection(null);v.clearGhosts();
    }""")
    ready(page)
    bounds = page.evaluate("window.workbench.summary.occupied_bounds")
    center = [(a + b + 1) / 2 for a, b in zip(bounds["low"], bounds["high"], strict=False)]
    extent = (
        sum((b - a + 1) ** 2 for a, b in zip(bounds["low"], bounds["high"], strict=False)) ** 0.5
    )
    factor = 0.8 if identifier.startswith("visual_probe") else 1.05
    distance = max(12, extent * factor)
    directions = [
        ("front", (0, 0.12, 1)),
        ("back", (0, 0.12, -1)),
        ("side", (1, 0.2, 0)),
        ("iso", (1.2, 0.9, 1.4)),
        ("reverse_iso", (-1.2, 0.6, -1.4)),
        ("top", (0, 1, 0.001)),
    ]
    result = []
    for name, direction in directions:
        scale = distance / sum(value * value for value in direction) ** 0.5
        position = [c + scale * d for c, d in zip(center, direction, strict=False)]
        params = {"position": position, "target": center, "far": max(4000, extent * 10)}
        page.evaluate(
            """p=>{
          const v=window.workbench.viewer;
          v.controls.target.set(...p.target);v.camera.position.set(...p.position);
          v.camera.far=p.far;v.camera.fov=40;v.camera.updateProjectionMatrix();
          v.controls.update();
          // Reapply exact values after OrbitControls' spherical arithmetic, so
          // two independent contexts do not differ by accumulated roundoff.
          v.camera.position.set(...p.position);v.camera.lookAt(...p.target);
          v.camera.updateMatrixWorld();v.requestDraw();
        }""",
            params,
        )
        ready(page)
        # Read the actual WebGL canvas, excluding DOM controls over the stage.
        data_url = page.evaluate("""() => {
          const v=window.workbench.viewer;v.drawNow();
          return v.renderer.domElement.toDataURL('image/png');
        }""")
        png = base64.b64decode(data_url.split(",", 1)[1])
        file = target / f"{identifier}-{name}.png"
        file.write_bytes(png)
        result.append(
            {
                "scene": identifier,
                "view": name,
                "file": str(file),
                "camera": params,
                "camera_matrices": page.evaluate("""() => {
                  const c=window.workbench.viewer.camera;
                  return {world:c.matrixWorld.toArray(),projection:c.projectionMatrix.toArray()};
                }"""),
                "draw_calls": page.evaluate("window.workbench.viewer.renderer.info.render.calls"),
            }
        )
    return result


def compare(before: Path, after: Path, destination: Path) -> dict[str, Any]:
    old = np.asarray(Image.open(before).convert("RGB"), dtype=np.int16)
    new = np.asarray(Image.open(after).convert("RGB"), dtype=np.int16)
    assert old.shape == new.shape == (751, 922, 3)
    diff = np.abs(new - old)
    maximum = diff.max(axis=2)
    changed = maximum > 3
    # Diagnostic only: identify one-pixel neighborhoods around image/color edges.
    # This never changes the strict gate or exempts a sign-text recoloring.
    edges = np.zeros(changed.shape, dtype=bool)
    for source in (old, new):
        horizontal = np.abs(source[:, 1:] - source[:, :-1]).max(axis=2) > 8
        vertical = np.abs(source[1:] - source[:-1]).max(axis=2) > 8
        edges[:, 1:] |= horizontal
        edges[:, :-1] |= horizontal
        edges[1:] |= vertical
        edges[:-1] |= vertical
    padded = np.pad(edges, 1)
    expanded = np.zeros(edges.shape, dtype=bool)
    for y in range(3):
        for x in range(3):
            expanded |= padded[y : y + edges.shape[0], x : x + edges.shape[1]]
    interior = changed & ~expanded
    visual = np.maximum(old // 3, new // 3).astype(np.uint8)
    visual[changed] = [255, 30, 70]
    Image.fromarray(visual).save(destination)
    return {
        "shape": list(old.shape),
        "exact_differing_pixels": int(np.count_nonzero(maximum)),
        "pixels_above_channel_tolerance_3": int(changed.sum()),
        "fraction_above_tolerance": round(float(changed.mean()), 8),
        "max_channel_difference": int(diff.max()),
        "mean_absolute_channel_difference": round(float(diff.mean()), 6),
        "changed_pixels_in_1px_edge_neighborhood": int((changed & expanded).sum()),
        "changed_pixels_outside_edge_neighborhood": int(interior.sum()),
        "max_interior_channel_difference": int(maximum[interior].max()) if interior.any() else 0,
        "edge_diagnostic_changes_strict_gate": False,
        "pass": not bool(changed.any()),
        "diff_image": str(destination),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline", type=Path, default=ROOT / "artifacts/performance/baseline-static/ui"
    )
    parser.add_argument("--current", type=Path, default=ROOT / "src/design_workbench/static")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/performance/visual")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".local/cache")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--static-dir", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--port", type=int)
    parser.add_argument("--probe-only", action="store_true")
    args = parser.parse_args()
    if args.serve:
        args.max_blocks = 1_500_000
        serve(args)
        return
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    data = output / "data"
    projects = data / "projects"
    projects.mkdir(parents=True, exist_ok=True)
    probe_file = projects / "visual_probe.dwbench"
    if not probe_file.exists():
        probe(probe_file)
    no_text_probe_file = projects / "visual_probe_no_text.dwbench"
    if not no_text_probe_file.exists():
        probe(no_text_probe_file, with_text=False)
    identifiers = ["visual_probe", "visual_probe_no_text"]
    if not args.probe_only:
        for identifier in ["asset_villa_46281", "asset_ivory_castle_upper_105102"]:
            source = ROOT / ".local/performance/data/projects" / f"{identifier}.dwbench"
            assert source.exists(), f"Run prepare_performance_assets.py first: {source}"
            destination = projects / source.name
            if not destination.exists():
                copy_project(source, destination)
            identifiers.append(identifier)
        church = ROOT / ".local/imports/azalea-church.litematic"
        if church.exists():
            path = projects / "visual_church.dwbench"
            if not path.exists():
                catalog = Catalog()
                scene, _ = Litematic(catalog).read(church.read_bytes())
                store = SqliteStore.create(path, scene.name, "1.20.1", 3465, scene.bounds)
                scene.id = store.load().id
                store.commit(
                    scene,
                    [(point, None, cell) for point, cell in scene.cells.items()],
                    0,
                    "church-fixture",
                    hashlib.sha256(church.read_bytes()).hexdigest(),
                    attachment=church.read_bytes(),
                )
            identifiers.append("visual_church")
    processes = []
    pages = {}
    errors = []
    report: dict[str, Any] = {
        "canvas": [922, 751],
        "dpr": 1,
        "channel": "chrome",
        "same_backend_and_database": True,
        "fixed_clear_color": "#eef2f2",
        "tolerance_per_channel": 3,
        "scenes": identifiers,
        "checks": [],
        "source_hashes": {},
    }
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            report["browser_version"] = browser.version
            for label, static in [("before", args.baseline), ("after", args.current)]:
                snapshot = output / f"{label}-static"
                if snapshot.exists():
                    raise FileExistsError(f"Use a new output directory: {snapshot}")
                shutil.copytree(static, snapshot)
                report["source_hashes"][label] = {
                    str(file.relative_to(snapshot)): hashlib.sha256(file.read_bytes()).hexdigest()
                    for file in snapshot.rglob("*")
                    if file.is_file()
                }
                process, url, log = launch(
                    snapshot, data, output / f"{label}-server.log", args.cache_dir
                )
                processes.append((process, log))
                page = browser.new_page(
                    viewport={"width": 1440, "height": 1000}, device_scale_factor=1
                )
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on(
                    "console",
                    lambda message: (
                        errors.append(message.text) if message.type == "error" else None
                    ),
                )
                directory = output / label
                directory.mkdir()
                pages[label] = {
                    identifier: capture(page, url, identifier, directory)
                    for identifier in identifiers
                }
                page.close()
            for identifier in identifiers:
                for old, new in zip(
                    pages["before"][identifier], pages["after"][identifier], strict=False
                ):
                    assert old["camera"] == new["camera"]
                    assert old["camera_matrices"] == new["camera_matrices"]
                    result = compare(
                        Path(old["file"]),
                        Path(new["file"]),
                        output / f"diff-{identifier}-{old['view']}.png",
                    )
                    result.update(
                        {
                            "scene": identifier,
                            "view": old["view"],
                            "camera": old["camera"],
                            "camera_matrices": old["camera_matrices"],
                            "before_draw_calls": old["draw_calls"],
                            "after_draw_calls": new["draw_calls"],
                        }
                    )
                    report["checks"].append(result)
                    print(
                        json.dumps(
                            {
                                key: result[key]
                                for key in [
                                    "scene",
                                    "view",
                                    "pixels_above_channel_tolerance_3",
                                    "max_channel_difference",
                                    "pass",
                                ]
                            }
                        )
                    )
            browser.close()
    finally:
        for process, log in processes:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            log.close()
        report["page_errors"] = errors
        report["passed"] = (
            bool(report["checks"])
            and all(check["pass"] for check in report["checks"])
            and not errors
        )
        (output / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8"
        )
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
