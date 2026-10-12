"""Real browser creation and switching across installed version-specific atlases.

CI exercises the baseline; set DW_TEST_VERSIONS=1.20.1,1.21.4,26.1 for the
official multi-version matrix after scripts/audit_versions.py --download.
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import expect, sync_playwright

from design_workbench.adapters.resources.catalog import Catalog


@pytest.mark.e2e
def test_version_selection_and_project_switching(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    versions = os.environ.get("DW_TEST_VERSIONS", "1.20.1").split(",")
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
        env=env,
        cwd=tmp_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            assert process.poll() is None
            try:
                if httpx.get(url + "/api/info", timeout=1).status_code == 200:
                    break
            except httpx.TransportError:
                pass
            time.sleep(0.1)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel=os.environ.get("DW_BROWSER_CHANNEL"), headless=True
            )
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            identifiers = []
            for version in versions:
                page.goto(url)
                page.locator("[data-home-create]").first.click()
                page.wait_for_function(
                    "document.querySelector('#home-minecraft-version').options.length > 1"
                )
                page.locator("#home-minecraft-version").select_option(version)
                expect(page.locator("#home-resource-status")).to_contain_text("已就绪")
                page.locator("#home-project-name").fill("版本验证 " + version)
                screenshots = root / "artifacts/versions"
                screenshots.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(screenshots / "version-selection.png"))
                page.locator("#home-create-submit").click()
                page.wait_for_url("**/?project=*")
                page.wait_for_function("window.workbench?.summary && !window.workbench.busy")
                expect(page.locator("#version")).to_have_text("Java " + version)
                identifier = page.evaluate("window.workbench.project")
                identifiers.append(identifier)
                registered = Catalog(version).blocks
                block = next(
                    name
                    for name in ("pale_oak_planks", "heavy_core", "stone")
                    if "minecraft:" + name in registered
                )
                result = page.request.post(
                    url + f"/api/projects/{identifier}/edit",
                    data={
                        "expected_revision": 0,
                        "request_id": "browser-version",
                        "operations": [
                            {
                                "op": "fill",
                                "bounds": {"low": [0, 0, 0], "high": [2, 2, 2]},
                                "state": {"name": block},
                            }
                        ],
                    },
                )
                assert result.ok, result.text()
                page.locator("#save").click()
                page.wait_for_function(
                    "window.workbench.summary?.blocks === 27 && !window.workbench.busy"
                )
                page.locator("#search").fill(block)
                total = page.request.get(
                    url + f"/api/catalog?project={identifier}&query={block}"
                ).json()["total"]
                expect(page.locator("#catalog-total")).to_have_text(str(total))
                expect(page.locator(".material-card").first).to_be_visible()
                page.wait_for_function("window.workbench.viewer.pendingBuilds.size === 0")
                page.screenshot(path=str(screenshots / f"java-{version}.png"))
                capture = page.request.post(
                    url + f"/api/projects/{identifier}/views",
                    data={
                        "expected_revision": 1,
                        "request_id": "version-capture",
                        "views": [{"name": "iso"}],
                        "width": 256,
                        "height": 256,
                    },
                    timeout=90000,
                )
                assert capture.ok, capture.text()
                result = capture.json()
                assert result["status"] == "succeeded", result
                resources = page.request.get(url + "/api/info?project=" + identifier).json()
                assert result["resource_hash"] == resources["resource_manifest"]["bundle_hash"]
                assert (
                    page.request.get(url + result["images"][0]["url"]).body().startswith(b"\x89PNG")
                )
            for identifier, version in zip(identifiers, versions, strict=True):
                page.locator("#projects").select_option(identifier)
                expect(page.locator("#version")).to_have_text("Java " + version)
                page.wait_for_function(
                    "window.workbench.summary?.blocks === 27 && !window.workbench.busy"
                )
                assert (
                    page.request.get(url + "/api/info?project=" + identifier).json()[
                        "minecraft_version"
                    ]
                    == version
                )
            assert not errors, errors
            browser.close()
    finally:
        process.terminate()
        process.wait(timeout=10)
