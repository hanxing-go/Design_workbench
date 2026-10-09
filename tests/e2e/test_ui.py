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
            page.goto(url)
            page.wait_for_function("window.workbench && !window.workbench.busy")
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
            page.screenshot(path=str(tmp_path / "browser.png"))
            assert not errors
            browser.close()
    finally:
        process.terminate()
        process.wait(timeout=10)
