import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import sync_playwright


@pytest.mark.e2e
def test_real_browser_design_control_and_restart(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    env = {
        **os.environ,
        "DW_DATA_DIR": str(tmp_path / "data"),
        "DW_CACHE_DIR": str(root / ".local/cache"),
        "DW_LOG_DIR": str(tmp_path / "log"),
    }

    def start() -> subprocess.Popen[bytes]:
        process = subprocess.Popen(
            [sys.executable, "-m", "design_workbench.interfaces.cli", "serve", "--port", str(port)],
            env=env,
            cwd=tmp_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                if httpx.get(url + "/api/info", timeout=1).status_code == 200:
                    return process
            except httpx.TransportError:
                pass
            assert process.poll() is None
            time.sleep(0.1)
        process.terminate()
        process.wait(timeout=10)
        pytest.fail("测试服务启动失败")

    def stop(process: subprocess.Popen[bytes]) -> None:
        process.terminate()
        process.wait(timeout=10)

    process = start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel=os.environ.get("DW_BROWSER_CHANNEL"), headless=True
            )
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            project = page.request.post(
                url + "/api/projects", data={"name": "AI 浏览器验收"}
            ).json()["project_id"]
            page.goto(url + f"/?project={project}")
            page.wait_for_function("window.workbench?.summary && !window.workbench.busy")
            page.locator("#ai-tasks").click()
            page.locator("#ai-prompt").fill("新建小场景，保留可撤销的修改")
            page.locator("#ai-create").click()
            page.wait_for_function("document.getElementById('ai-run-id').value.length === 32")
            run = page.locator("#ai-run-id").input_value()
            assert "尚未报告" in page.locator("#ai-usage").inner_text()

            def proposal(key: str, revision: int, state: str = "stone") -> None:
                result = page.request.post(
                    url + "/api/tools/v1/design.propose",
                    data={
                        "run_id": run,
                        "request_id": key,
                        "request": {
                            "expected_revision": revision,
                            "request_id": key,
                            "operations": [
                                {
                                    "op": "fill",
                                    "bounds": {"low": [0, 0, 0], "high": [2, 1, 2]},
                                    "state": {"name": state},
                                }
                            ],
                        },
                        "explanation": "搭建一个 18 格的基础",
                    },
                ).json()
                assert result["status"] == "awaiting_approval", result
                page.wait_for_function(
                    "document.getElementById('ai-state').textContent.includes('等待确认')"
                )

            proposal("first", 0)
            assert page.request.get(url + f"/api/projects/{project}").json()["blocks"] == 0
            page.locator("#ai-view-proposal").click()
            assert not page.locator("#ai-panel").is_visible()
            page.locator("#ai-tasks").click()
            page.locator("#ai-approve").click()
            page.wait_for_function("window.workbench.summary.revision === 1")
            assert page.evaluate("window.workbench.summary.blocks") == 18
            capture = page.request.post(
                url + "/api/tools/v1/design.call",
                data={
                    "run_id": run,
                    "request_id": "capture",
                    "tool": "render.views",
                    "arguments": {
                        "request": {
                            "expected_revision": 1,
                            "request_id": "actual-views",
                            "views": [{"name": "iso"}],
                            "width": 192,
                            "height": 128,
                        }
                    },
                },
            ).json()
            assert capture["status"] == "succeeded", capture
            image_url = capture["images"][0]["url"]
            assert page.request.get(url + image_url).body().startswith(b"\x89PNG")
            page.locator("#ai-candidate-name").fill("初稿候选")
            page.locator("#ai-candidate-feedback").fill("保留石材基础")
            page.locator("#ai-save-candidate").click()
            page.wait_for_selector("#ai-candidates .ai-candidate")
            with page.expect_download() as download:
                page.locator("#ai-candidates a").filter(has_text="下载工程").click()
            target = tmp_path / "candidate.dwbench"
            download.value.save_as(target)
            assert target.read_bytes().startswith(b"SQLite format 3")
            proposal("rejected", 1, "oak_planks")
            page.locator("#ai-reject").click()
            page.wait_for_function(
                "document.getElementById('ai-state').textContent.includes('进行中')"
            )
            assert page.evaluate("window.workbench.summary.revision") == 1
            page.locator("#ai-cancel").click()
            page.wait_for_function(
                "document.getElementById('ai-state').textContent.includes('已取消')"
            )
            stopped = page.request.post(
                url + "/api/tools/v1/design.call",
                data={
                    "run_id": run,
                    "request_id": "while-cancelled",
                    "tool": "scene.summary",
                    "arguments": {},
                },
            ).json()
            assert stopped["error"]["code"] == "DESIGN_STOPPED"
            stop(process)
            process = start()
            page.reload()
            page.wait_for_function("window.workbench?.summary && !window.workbench.busy")
            page.locator("#ai-tasks").click()
            page.wait_for_function(
                "document.getElementById('ai-state').textContent.includes('已取消')"
            )
            assert page.locator("#ai-candidates").inner_text().find("初稿候选") >= 0
            assert page.request.get(url + image_url).body().startswith(b"\x89PNG")
            assert page.locator("#ai-candidates img").count() == 1
            page.locator("#ai-resume").click()
            page.wait_for_function(
                "document.getElementById('ai-state').textContent.includes('进行中')"
            )
            # A stale proposal fails without overwriting the current scene, and the user can recover.
            failed = page.request.post(
                url + "/api/tools/v1/design.propose",
                data={
                    "run_id": run,
                    "request_id": "stale",
                    "request": {
                        "expected_revision": 0,
                        "request_id": "stale",
                        "operations": [
                            {
                                "op": "set",
                                "blocks": [{"position": [0, 0, 0], "state": {"name": "glass"}}],
                            }
                        ],
                    },
                    "explanation": "过期改稿",
                },
            ).json()
            assert failed["error"]["code"] == "REVISION_CONFLICT"
            page.wait_for_function(
                "document.getElementById('ai-state').textContent.includes('发生错误')"
            )
            page.locator("#ai-resume").click()
            page.wait_for_function(
                "document.getElementById('ai-state').textContent.includes('进行中')"
            )
            usage = page.request.post(
                url + "/api/tools/v1/design.usage",
                data={
                    "run_id": run,
                    "request_id": "usage",
                    "input_tokens": 3000000,
                    "output_tokens": 1,
                    "source": "browser contract counter fixture",
                },
            ).json()
            assert usage["status"] == "budget_exceeded"
            page.wait_for_function(
                "document.getElementById('ai-state').textContent.includes('预算已用完')"
            )
            page.locator("#ai-extend").click()
            page.locator("#ai-budget-tokens-extend").fill("4000000")
            page.locator("#ai-extend-form button[type=submit]").click()
            page.wait_for_function(
                "document.getElementById('ai-state').textContent.includes('进行中')"
            )
            qa = root / "artifacts/ai-controls"
            qa.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(qa / "task-desktop.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 700})
            page.screenshot(path=str(qa / "task-mobile.png"), full_page=True)
            page.locator("#ai-candidates button").click()
            page.wait_for_function(
                f"window.workbench.project !== '{project}' && !window.workbench.busy"
            )
            assert page.evaluate("window.workbench.summary.blocks") == 18
            assert page.request.get(url + f"/api/projects/{project}").json()["revision"] == 1
            assert not errors, errors
            browser.close()
    finally:
        if process.poll() is None:
            stop(process)


@pytest.mark.e2e
def test_design_cancels_owned_render_and_enforces_async_time_budget(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from design_workbench.config import Settings
    from design_workbench.interfaces.http import create_app

    root = Path(__file__).resolve().parents[2]
    settings = Settings(
        data_dir=tmp_path / "data",
        cache_dir=root / ".local/cache",
        log_dir=tmp_path / "log",
        browser_channel=os.environ.get("DW_BROWSER_CHANNEL"),
    )
    with TestClient(create_app(settings)) as client:
        project = client.post("/api/projects", json={"name": "任务截图控制"}).json()["project_id"]
        client.post(
            f"/api/projects/{project}/edit",
            json={
                "expected_revision": 0,
                "request_id": "base",
                "operations": [
                    {"op": "set", "blocks": [{"position": [0, 0, 0], "state": {"name": "stone"}}]}
                ],
            },
        )
        tools = client.app.state.tools
        run = tools.call(
            "design.start",
            {
                "project": project,
                "request_id": "cancel-run",
                "expected_revision": 1,
                "prompt": "取消测试",
            },
        )["run_id"]
        pending = tools.call(
            "design.call",
            {
                "run_id": run,
                "request_id": "capture",
                "tool": "render.views",
                "arguments": {
                    "request": {
                        "expected_revision": 1,
                        "request_id": "pending-cancel",
                        "wait": False,
                        "views": [{"name": "iso"}],
                        "width": 192,
                        "height": 128,
                    }
                },
            },
        )
        assert "task_id" in pending, pending
        cancelled = tools.call("design.cancel", {"run_id": run, "request_id": "cancel"})
        assert cancelled["status"] == "cancelled"
        assert tools.renderer.status(pending["task_id"])["status"] == "cancelled"
        assert tools.workbench.service(tools.project_path(project)).summary()["revision"] == 1
        budget_run = tools.call(
            "design.start",
            {
                "project": project,
                "request_id": "budget-run",
                "expected_revision": 1,
                "prompt": "异步预算测试",
                "budget": {"seconds": 1},
            },
        )["run_id"]
        capture = tools.call(
            "design.call",
            {
                "run_id": budget_run,
                "request_id": "capture-budget",
                "tool": "render.views",
                "arguments": {
                    "request": {
                        "expected_revision": 1,
                        "request_id": "pending-budget",
                        "wait": False,
                        "views": [{"name": "iso"}],
                        "width": 192,
                        "height": 128,
                    }
                },
            },
        )
        # No status polling triggers the deadline: the task owns a budget watcher.
        time.sleep(1.8)
        assert tools.designs.status(budget_run)["status"] == "budget_exceeded"
        assert tools.renderer.status(capture["task_id"])["status"] == "cancelled"
