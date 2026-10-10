import asyncio
import base64
import hashlib
import io
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

from design_workbench.application.contracts import EditRequest
from design_workbench.application.render_contracts import RenderRequest
from design_workbench.bootstrap import Workbench
from design_workbench.config import Settings
from design_workbench.domain.errors import WorkbenchError
from design_workbench.interfaces.tools import Tools

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.e2e
def test_mcp_returns_png_content_and_cancels_browser_task(tmp_path: Path) -> None:
    settings = configured(tmp_path)
    env = {
        **os.environ,
        "DW_DATA_DIR": str(settings.data_dir),
        "DW_CACHE_DIR": str(settings.cache_dir),
        "DW_LOG_DIR": str(settings.log_dir),
    }
    if settings.browser_channel:
        env["DW_BROWSER_CHANNEL"] = settings.browser_channel

    async def run() -> Path:
        parameters = StdioServerParameters(
            command=sys.executable, args=["-m", "design_workbench.interfaces.cli", "mcp"], env=env
        )
        async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            created = await session.call_tool(
                "project.create", {"request_id": "mcp-browser", "request": {"name": "MCP 图片验证"}}
            )
            project = created.structuredContent["project_id"]
            assert not (
                await session.call_tool(
                    "scene.commit_edit", {"project": project, "request": box_request()}
                )
            ).isError
            body = {
                "project": project,
                "request": {
                    "expected_revision": 1,
                    "request_id": "wire-image",
                    "views": [{"name": "iso"}],
                    "width": 192,
                    "height": 128,
                },
            }
            captured = await session.call_tool("render.views", body)
            assert not captured.isError, captured
            contents = [content for content in captured.content if content.type == "image"]
            assert len(contents) == 1 and contents[0].mimeType == "image/png"
            assert Image.open(io.BytesIO(base64.b64decode(contents[0].data))).size == (192, 128)
            assert captured.structuredContent["images"][0]["revision"] == 1
            directory = Path(captured.structuredContent["images"][0]["path"]).parent.parent
            body["request"] = {**body["request"], "wait": False, "request_id": "wire-cancel"}
            pending = await session.call_tool("render.views", body)
            cancelled = await session.call_tool(
                "render.cancel", {"task_id": pending.structuredContent["task_id"]}
            )
            assert cancelled.structuredContent["status"] == "cancelled"
        return directory

    directory = asyncio.run(run())
    assert not directory.exists(), "MCP shutdown must remove its owned screenshots"


def configured(tmp_path: Path, **values: object) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        cache_dir=ROOT / ".local/cache",
        log_dir=tmp_path / "logs",
        browser_channel=os.environ.get("DW_BROWSER_CHANNEL", "chrome" if os.name == "nt" else None),
        **values,
    )


def box_request() -> dict:
    return {
        "expected_revision": 0,
        "request_id": "box",
        "operations": [
            {
                "op": "fill",
                "bounds": {"low": [0, 0, 0], "high": [6, 5, 8]},
                "state": {"name": "oak_planks"},
                "hollow": True,
            }
        ],
    }


@pytest.mark.e2e
def test_snapshot_pngs_remain_frozen_during_concurrent_edit(tmp_path: Path) -> None:
    workbench = Workbench(configured(tmp_path))
    assert workbench.pack is not None, "P6 requires imported official resources"
    tools = Tools(workbench)
    try:
        project = tools.call(
            "project.create", {"request_id": "p6", "request": {"name": "截图修订验收"}}
        )["project_id"]
        tools.call("scene.commit_edit", {"project": project, "request": box_request()})
        capture = {
            "expected_revision": 1,
            "request_id": "baseline",
            "views": [
                {"name": "iso"},
                {"name": "top", "layer": 2},
                {
                    "name": "custom",
                    "camera": {"position": [3.5, 2.5, 5], "target": [3.5, 2.5, 0], "fov": 70},
                },
            ],
            "width": 400,
            "height": 320,
        }
        baseline = tools.renderer.submit(
            tools.project_path(project), RenderRequest.model_validate(capture)
        )
        assert baseline["status"] == "succeeded", baseline
        baseline_png = tools.renderer.image(baseline["task_id"], 0).read_bytes()
        assert Image.open(io.BytesIO(baseline_png)).size == (400, 320)
        assert len(baseline["images"]) == 3 and baseline["page_errors"] == []
        assert baseline["images"][1]["visible_cells"] < baseline["images"][1]["snapshot_cells"]
        assert baseline["images"][2]["camera"]["fov"] == 70
        baseline_layer = Image.open(tools.renderer.image(baseline["task_id"], 1)).copy()
        assert (
            ImageChops.difference(Image.open(io.BytesIO(baseline_png)), baseline_layer).getbbox()
            is not None
        )
        frozen_request = RenderRequest.model_validate(
            {**capture, "request_id": "frozen", "wait": False}
        )
        frozen = tools.renderer.submit(tools.project_path(project), frozen_request)
        workbench.service(tools.project_path(project)).edit(
            EditRequest.model_validate(
                {
                    "expected_revision": 1,
                    "request_id": "concurrent-user",
                    "operations": [
                        {
                            "op": "fill",
                            "bounds": {"low": [8, 0, 0], "high": [11, 15, 3]},
                            "state": {"name": "red_concrete"},
                        }
                    ],
                }
            )
        )
        frozen_request.wait = True
        finished = tools.renderer.submit(tools.project_path(project), frozen_request)
        assert finished["task_id"] == frozen["task_id"] and finished["revision"] == 1
        assert finished["snapshot_sha256"] == baseline["snapshot_sha256"]
        assert tools.renderer.image(finished["task_id"], 0).read_bytes() == baseline_png
        current = tools.renderer.submit(
            tools.project_path(project),
            RenderRequest.model_validate(
                {**capture, "request_id": "current", "expected_revision": 2}
            ),
        )
        assert (
            current["revision"] == 2 and current["snapshot_sha256"] != baseline["snapshot_sha256"]
        )
        assert tools.renderer.image(current["task_id"], 0).read_bytes() != baseline_png
        with pytest.raises(WorkbenchError) as conflict:
            tools.renderer.submit(
                tools.project_path(project),
                RenderRequest.model_validate({**capture, "request_id": "stale"}),
            )
        assert conflict.value.code == "REVISION_CONFLICT" and conflict.value.revision == 2
        with pytest.raises(WorkbenchError) as conflict:
            tools.renderer.submit(
                tools.project_path(project), RenderRequest.model_validate({**capture, "width": 420})
            )
        assert conflict.value.code == "REQUEST_ID_REUSED"
        for result in (baseline, finished, current):
            assert all(image["revision"] == result["revision"] for image in result["images"])
            assert result["resource_hash"] == workbench.pack.manifest["bundle_hash"]
    finally:
        directory = tools.renderer.directory
        tools.close()
        assert not directory.exists()


@pytest.mark.e2e
def test_render_queue_cancel_timeout_failure_and_output_budget(tmp_path: Path) -> None:
    tools = Tools(Workbench(configured(tmp_path, max_render_jobs=1, render_workers=1)))
    try:
        project = tools.call(
            "project.create", {"request_id": "failures", "request": {"name": "任务生命周期"}}
        )["project_id"]
        tools.call("scene.commit_edit", {"project": project, "request": box_request()})
        tools.workbench.settings.max_render_cells = 1
        with pytest.raises(WorkbenchError) as failure:
            tools.renderer.submit(
                tools.project_path(project),
                RenderRequest(expected_revision=1, request_id="too-many-cells"),
            )
        assert failure.value.code == "RENDER_CELL_LIMIT" and not tools.renderer.jobs
        tools.workbench.settings.max_render_cells = 100_000
        with pytest.raises(WorkbenchError) as failure:
            tools.renderer.submit(
                tools.project_path(project),
                RenderRequest.model_validate(
                    {
                        "expected_revision": 1,
                        "request_id": "too-large-space",
                        "views": [
                            {"name": "iso", "bounds": {"low": [0, 0, 0], "high": [200, 200, 200]}}
                        ],
                    }
                ),
            )
        assert (
            failure.value.code == "SELECTION_LIMIT" and failure.value.location == "views.0.bounds"
        )
        assert not tools.renderer.jobs
        request = RenderRequest(expected_revision=1, request_id="cancel", wait=False)
        queued = tools.renderer.submit(tools.project_path(project), request)
        with pytest.raises(WorkbenchError) as failure:
            tools.renderer.submit(
                tools.project_path(project), request.model_copy(update={"request_id": "full"})
            )
        assert failure.value.code == "RENDER_QUEUE_FULL"
        cancelled = tools.renderer.cancel(queued["task_id"])
        assert (
            cancelled["status"] == "cancelled" and cancelled["error"]["code"] == "RENDER_CANCELLED"
        )
        for index, timeout in enumerate((0.01, 0.15, 0.3)):
            timed = tools.renderer.submit(
                tools.project_path(project),
                RenderRequest(expected_revision=1, request_id=f"timeout-{index}", timeout=timeout),
            )
            assert timed["status"] == "timed_out" and timed["error"]["code"] == "RENDER_TIMEOUT"
        tools.workbench.settings.browser_channel = "p6-missing-browser"
        failed = tools.renderer.submit(
            tools.project_path(project), RenderRequest(expected_revision=1, request_id="failure")
        )
        assert failed["status"] == "failed" and failed["error"]["code"] in {
            "BROWSER_UNAVAILABLE",
            "RENDER_FAILED",
        }
        tools.workbench.settings.browser_channel = os.environ.get(
            "DW_BROWSER_CHANNEL", "chrome" if os.name == "nt" else None
        )
        tools.workbench.settings.max_render_bytes = 1024
        limited = tools.renderer.submit(
            tools.project_path(project),
            RenderRequest(expected_revision=1, request_id="limited", views=[{"name": "iso"}]),
        )
        assert limited["status"] == "failed" and limited["error"]["code"] == "RENDER_OUTPUT_LIMIT"
        assert not list(tools.renderer.directory.rglob("*.png"))
        assert tools.call("scene.summary", {"project": project})["revision"] == 1
    finally:
        tools.close()


@pytest.mark.e2e
def test_cli_external_edit_updates_ui_and_http_serves_actual_png(tmp_path: Path) -> None:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    settings = configured(tmp_path)
    env = {
        **os.environ,
        "DW_DATA_DIR": str(settings.data_dir),
        "DW_CACHE_DIR": str(settings.cache_dir),
        "DW_LOG_DIR": str(settings.log_dir),
    }
    if settings.browser_channel:
        env["DW_BROWSER_CHANNEL"] = settings.browser_channel
    process = subprocess.Popen(
        [sys.executable, "-m", "design_workbench.interfaces.cli", "serve", "--port", str(port)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=90) as client:
            deadline = time.monotonic() + 25
            while True:
                assert process.poll() is None
                try:
                    if client.get("/api/info").is_success:
                        break
                except httpx.TransportError:
                    pass
                assert time.monotonic() < deadline
                time.sleep(0.1)
            project = client.post("/api/projects", json={"name": "外部 CLI 编辑"}).json()[
                "project_id"
            ]
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    channel=settings.browser_channel, headless=True
                )
                try:
                    page = browser.new_page(viewport={"width": 1100, "height": 800})
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(str(client.base_url) + f"?project={project}")
                    page.wait_for_function("window.workbench && !window.workbench.busy")
                    source = tmp_path / "edit.json"
                    source.write_text(
                        json.dumps({"project": project, "request": box_request()}), encoding="utf-8"
                    )
                    subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "design_workbench.interfaces.cli",
                            "tool",
                            "scene.commit_edit",
                            str(source),
                        ],
                        env=env,
                        capture_output=True,
                        check=True,
                    )
                    page.wait_for_function(
                        "window.workbench.summary.revision === 1 && !window.workbench.busy",
                        timeout=15_000,
                    )
                    assert page.evaluate(
                        "window.workbench.viewer.occupied().size"
                    ) == page.evaluate("window.workbench.summary.blocks")
                    result = client.post(
                        f"/api/projects/{project}/views",
                        json={
                            "expected_revision": 1,
                            "request_id": "http",
                            "views": [{"name": "iso"}],
                            "width": 320,
                            "height": 240,
                        },
                    ).json()
                    assert result["status"] == "succeeded", result
                    png = client.get(result["images"][0]["url"])
                    assert png.headers["content-type"] == "image/png" and Image.open(
                        io.BytesIO(png.content)
                    ).size == (320, 240)
                    assert (
                        hashlib.sha256(png.content).digest()
                        == hashlib.sha256(Path(result["images"][0]["path"]).read_bytes()).digest()
                    )
                    assert not errors
                finally:
                    browser.close()
    finally:
        process.terminate()
        process.wait(timeout=15)
