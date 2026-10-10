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
def test_real_browser_edit_history_and_blueprint(tmp_path: Path) -> None:
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
            assert process.poll() is None, "本地服务启动失败"
            try:
                response = httpx.get(url + "/api/info", timeout=1)
                if response.status_code == 200:
                    assert response.json()["resources_ready"], "浏览器验收必须配置实际素材"
                    break
            except httpx.TransportError:
                pass
            if time.monotonic() > deadline:
                pytest.fail("本地服务启动超时")
            time.sleep(0.1)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel=os.environ.get("DW_BROWSER_CHANNEL"), headless=True
            )
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            # The home page lists real projects without creating one on a visit.
            page.goto(url)
            page.wait_for_selector("#home-empty:not([hidden])")
            assert page.request.get(url + "/api/projects").json()["items"] == []
            assert page.locator("#home-title").is_visible()
            page.locator("[data-home-guide]").first.click()
            assert page.locator("#home-guide-dialog").is_visible()
            page.keyboard.press("Escape")
            page.locator("[data-home-create]").first.click()
            page.locator("#home-project-name").fill("   ")
            page.locator("#home-create-submit").click()
            assert page.locator("#home-create-dialog").is_visible()
            assert page.locator("#home-create-error").inner_text()
            page.locator("#home-project-name").fill("我的建筑")
            page.locator("#home-create-submit").click()
            page.wait_for_url("**/?project=*")
            page.wait_for_function("window.workbench && !window.workbench.busy")
            assert page.locator("#layer-play").is_disabled()
            page.locator("#cabin").click()
            page.wait_for_function("!window.workbench.busy")
            assert page.evaluate("window.workbench.summary.blocks") == 449
            page.locator("#group-filter").select_option("roof")
            page.locator("#operation").select_option("replace")
            page.locator("#preview").click()
            page.wait_for_function("!window.workbench.busy")
            assert page.evaluate("window.workbench.summary.revision") == 1
            page.locator("#commit").click()
            page.wait_for_function("!window.workbench.busy")
            assert page.evaluate("window.workbench.summary.revision") == 2
            page.locator("#undo").click()
            page.wait_for_function("!window.workbench.busy")
            page.locator("#redo").click()
            page.wait_for_function("!window.workbench.busy")
            assert page.evaluate("window.workbench.summary.revision") == 4
            with page.expect_download() as download:
                page.locator("#export").click()
            downloaded = tmp_path / "browser.litematic"
            download.value.save_as(str(downloaded))
            assert downloaded.stat().st_size > 100
            # The one-based playback UI must still send actual Y coordinates to the renderer.
            page.locator("#layer-speed").select_option("4")
            page.locator("#layer-play").click()
            assert page.evaluate("window.workbench.viewer.layer") == 0
            page.wait_for_function(
                "document.querySelector('#layer-play').getAttribute('aria-pressed') === 'false'"
            )
            assert page.evaluate("window.workbench.viewer.layer") == 10
            assert page.locator("#layer-number").input_value() == "11"
            page.locator("#layer-number").fill("2")
            page.locator("#layer-number").press("Tab")
            assert page.evaluate("window.workbench.viewer.layer") == 1
            page.locator("#layer-reset").click()
            assert page.evaluate("window.workbench.viewer.layer === Infinity")

            width = page.locator("#stage").bounding_box()["width"]
            page.locator("#toggle-library").click()
            assert page.locator("#library").is_hidden()
            assert page.locator("#stage").bounding_box()["width"] > width
            page.locator("#focus-mode").click()
            assert page.locator("#library").is_hidden() and page.locator("#inspector").is_hidden()
            page.locator("#focus-mode").click()
            assert page.locator("#library").is_hidden() and page.locator("#inspector").is_visible()
            page.reload()
            page.wait_for_function("window.workbench && !window.workbench.busy")
            assert page.locator("#library").is_hidden()
            page.locator("#toggle-library").click()

            page.locator("#help").click()
            assert page.locator("#help-dialog").is_visible()
            page.keyboard.press("Escape")
            assert page.locator("#help-dialog").is_hidden()
            page.locator("#stage").focus()
            page.keyboard.press("2")
            assert "active" in page.locator('[data-tool="place"]').get_attribute("class")
            page.keyboard.press("1")
            page.keyboard.press("F2")
            page.locator("#project-name").fill("  重命名后的木屋  ")
            page.locator("#rename-submit").click()
            page.wait_for_function("!window.workbench.busy")
            assert page.locator("#rename-dialog").is_hidden()
            assert page.locator("#scene-name").inner_text() == "重命名后的木屋"
            assert page.locator("#projects option:checked").inner_text() == "重命名后的木屋"
            page.locator("#stage").focus()
            page.keyboard.press("Control+z")
            page.wait_for_function("!window.workbench.busy")
            assert page.locator("#scene-name").inner_text() == "我的建筑"
            page.keyboard.press("Control+Shift+z")
            page.wait_for_function("!window.workbench.busy")
            assert page.locator("#scene-name").inner_text() == "重命名后的木屋"
            page.reload()
            page.wait_for_function("window.workbench && !window.workbench.busy")
            assert page.locator("#scene-name").inner_text() == "重命名后的木屋"

            # Negative-height, single-layer and empty projects are common boundary cases.
            identifier = page.request.post(
                url + "/api/projects", data={"name": "地下播放测试"}
            ).json()["project_id"]
            path = f"{url}/api/projects/{identifier}"
            page.request.post(
                path + "/edit",
                data={
                    "expected_revision": 0,
                    "request_id": "negative",
                    "operations": [
                        {
                            "op": "fill",
                            "bounds": {"low": [0, -3, 0], "high": [0, -1, 0]},
                            "state": {"name": "stone"},
                        }
                    ],
                },
            )
            page.goto(url + f"/?project={identifier}")
            page.wait_for_function("window.workbench && !window.workbench.busy")
            assert page.locator("#layer-total").inner_text() == "3"
            page.locator("#layer-play").click()
            assert page.evaluate("window.workbench.viewer.layer") == -3
            page.locator("#layer-play").click()
            page.locator("#layer-number").fill("99")
            page.locator("#layer-number").press("Tab")
            assert page.evaluate("window.workbench.viewer.layer") == -1
            page.locator("#layer-number").fill("")
            page.locator("#layer-number").press("Tab")
            assert page.locator("#layer-number").input_value() == "3"
            page.locator("#stage").focus()
            page.keyboard.press("ArrowLeft")
            assert page.evaluate("window.workbench.viewer.layer") == -2
            page.keyboard.press("Space")
            page.keyboard.press("Escape")
            assert page.locator("#layer-play").get_attribute("aria-pressed") == "false"

            page.request.post(
                path + "/edit",
                data={
                    "expected_revision": 1,
                    "request_id": "single-layer",
                    "operations": [
                        {
                            "op": "delete",
                            "selector": {"bounds": {"low": [0, -3, 0], "high": [0, -3, 0]}},
                        },
                        {
                            "op": "delete",
                            "selector": {"bounds": {"low": [0, -1, 0], "high": [0, -1, 0]}},
                        },
                    ],
                },
            )
            page.reload()
            page.wait_for_function("window.workbench && !window.workbench.busy")
            assert page.locator("#layer-play").is_disabled()
            assert page.locator("#layer-total").inner_text() == "1"
            assert page.locator("#layer-number").input_value() == "1"
            page.request.post(
                path + "/edit",
                data={
                    "expected_revision": 2,
                    "request_id": "empty",
                    "operations": [
                        {
                            "op": "delete",
                            "selector": {"bounds": {"low": [0, -2, 0], "high": [0, -2, 0]}},
                        }
                    ],
                },
            )
            page.reload()
            page.wait_for_function("window.workbench && !window.workbench.busy")
            assert page.locator("#layer-play").is_disabled()
            assert page.locator("#layer-total").inner_text() == "0"
            assert page.locator("#layer-label").inner_text() == "暂无方块"

            # Text entry must not trigger tool or panel shortcuts; narrow screens use overlays.
            page.locator("#search").focus()
            page.keyboard.press("]")
            assert page.locator("#inspector").is_visible()
            page.set_viewport_size({"width": 390, "height": 844})
            page.evaluate("localStorage.removeItem('workbench.panels')")
            page.reload()
            page.wait_for_function("window.workbench && !window.workbench.busy")
            assert page.locator("#library").is_hidden() and page.locator("#inspector").is_hidden()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.locator("#toggle-library").click()
            assert page.locator("#library").is_visible()
            page.screenshot(path=str(tmp_path / "browser.png"))

            # Home project search, layout, return links, and blueprint import are functional.
            page.locator(".workbench-home-link").click()
            page.wait_for_selector(".project-card")
            assert page.locator(".project-card").count() == 2
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.locator("#home-search").fill("不存在的设计")
            assert page.locator("#home-no-results").is_visible()
            page.locator("#home-search").fill("重命名后的木屋")
            assert page.locator(".project-card").count() == 1
            page.locator("#design-toggle").click()
            assert page.locator("#design-toggle").get_attribute("aria-pressed") == "true"
            page.locator(".project-card").click()
            page.wait_for_function("window.workbench && !window.workbench.busy")
            assert page.locator("#scene-name").inner_text() == "重命名后的木屋"
            page.goto(url)
            page.wait_for_selector(".project-card")
            page.locator("#home-import-file").set_input_files(str(downloaded))
            page.wait_for_url("**/?project=*")
            page.wait_for_function("window.workbench && !window.workbench.busy")
            assert page.evaluate("window.workbench.summary.blocks") == 449
            assert page.locator("#scene-name").inner_text() == "我的建筑"

            # The sample shortcut creates a separate editable cabin, exactly once.
            page.goto(url)
            page.wait_for_selector(".project-card")
            page.locator("#home-cabin").click()
            page.locator("#home-create-submit").click()
            page.wait_for_function(
                "window.workbench && window.workbench.summary?.blocks === 449 && !window.workbench.busy"
            )
            assert page.evaluate("window.workbench.summary.revision") == 1
            page.reload()
            page.wait_for_function("window.workbench && !window.workbench.busy")
            assert page.evaluate("window.workbench.summary.revision") == 1
            assert not errors
            browser.close()
    finally:
        process.terminate()
        process.wait(timeout=10)
