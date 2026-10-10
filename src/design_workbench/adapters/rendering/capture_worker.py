"""Owned, disposable browser process; serves only a frozen render packet."""

import base64
import hashlib
import json
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.models import BlockState, Bounds, Cell, Scene

from ..resources.catalog import Catalog
from ..resources.pack import ResourcePack
from .packets import render_packet


def write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def capture(directory: Path) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    request = json.loads((directory / "request.json").read_text(encoding="utf-8"))
    write_json(
        directory / "progress.json",
        {"stage": "preparing", "completed_views": 0, "total_views": len(request["views"])},
    )
    snapshot = json.loads((directory / "snapshot.json").read_text(encoding="utf-8"))
    scene = Scene(
        snapshot["id"],
        snapshot["name"],
        snapshot["minecraft_version"],
        snapshot["data_version"],
        snapshot["revision"],
        Bounds(tuple(snapshot["bounds"]["low"]), tuple(snapshot["bounds"]["high"])),
        {
            tuple(point): Cell(
                BlockState.make(cell["name"], cell["properties"]), cell["group"], cell["region"]
            )
            for point, cell in snapshot["cells"]
        },
        {tuple(point) for point in snapshot["protected"]},
    )
    pack = ResourcePack(Path(request["pack_directory"]))
    if pack.manifest["bundle_hash"] != request["resource_hash"]:
        raise WorkbenchError(
            "RESOURCE_CHANGED", "截图使用的资源包已变化，请重新提交。", "resources"
        )
    source = base64.b64decode(snapshot["source"], validate=True) if snapshot["source"] else None
    packet = json.dumps(
        render_packet(scene, Catalog(scene.minecraft_version), pack, source=source),
        ensure_ascii=False,
    ).encode()
    static = Path(__file__).parents[2] / "static"

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(static), **kwargs)

        def log_message(self, format: str, *args: Any) -> None:
            pass

        def do_GET(self) -> None:
            route = urlparse(self.path).path
            if route == "/api/snapshot":
                data, content_type = packet, "application/json"
            elif route == "/api/atlas.png":
                data, content_type = (directory / "atlas.png").read_bytes(), "image/png"
            else:
                super().do_GET()
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    images: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel=request.get("browser_channel"), headless=True
            )
            try:
                page = browser.new_page(
                    viewport={"width": request["width"], "height": request["height"]},
                    device_scale_factor=1,
                )
                page.set_default_timeout(request["timeout"] * 1000)
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}/capture.html", wait_until="load")
                page.wait_for_function("window.captureReady || window.captureError")
                page_error = page.evaluate("window.captureError")
                if page_error:
                    raise RuntimeError(page_error)
                total_bytes = 0
                for index, view in enumerate(request["views"]):
                    write_json(
                        directory / "progress.json",
                        {
                            "stage": "capturing",
                            "completed_views": index,
                            "total_views": len(request["views"]),
                        },
                    )
                    metadata = page.evaluate("view => window.captureView(view)", view)
                    filename = f"{index:02d}-{view['name']}.png"
                    data = page.locator("canvas").screenshot(
                        path=str(directory / filename), type="png"
                    )
                    total_bytes += len(data)
                    if total_bytes > request["max_bytes"]:
                        raise RuntimeError("RENDER_OUTPUT_LIMIT: PNG 总大小超过预算")
                    images.append({"file": filename, "bytes": len(data), **metadata})
                if errors:
                    raise RuntimeError("; ".join(errors[:4]))
                write_json(
                    directory / "progress.json",
                    {
                        "stage": "completed",
                        "completed_views": len(images),
                        "total_views": len(images),
                    },
                )
                return {
                    "images": images,
                    "browser_version": browser.version,
                    "page_errors": errors,
                    "snapshot_sha256": hashlib.sha256(packet).hexdigest(),
                    "atlas_sha256": hashlib.sha256(
                        (directory / "atlas.png").read_bytes()
                    ).hexdigest(),
                    "warnings": json.loads(packet)["warnings"],
                }
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def main() -> None:
    directory = Path(sys.argv[1]).resolve()
    started = time.monotonic()
    write_json(directory / "progress.json", {"stage": "starting", "completed_views": 0})
    try:
        result = {"ok": True, **capture(directory)}
    except Exception as error:
        message = str(error)
        code = (
            "BROWSER_UNAVAILABLE"
            if isinstance(error, ModuleNotFoundError)
            or "Executable doesn't exist" in message
            or "distribution" in message
            and "not found" in message
            else "RENDER_OUTPUT_LIMIT"
            if "RENDER_OUTPUT_LIMIT" in message
            else "RENDER_FAILED"
        )
        result = {
            "ok": False,
            "error": error.as_dict()
            if isinstance(error, WorkbenchError)
            else {"code": code, "message": message[:2000], "location": "render"},
        }
    result["elapsed_ms"] = round((time.monotonic() - started) * 1000, 2)
    write_json(directory / "result.json", result)


if __name__ == "__main__":
    main()
