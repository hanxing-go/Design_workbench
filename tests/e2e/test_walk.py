"""E1 acceptance through real browser input and independent HTTP scene reads."""

import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import Page, Route, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts/e1"


def settled(page: Page) -> None:
    page.wait_for_function("window.workbench && !window.workbench.busy", timeout=30_000)
    page.evaluate("window.workbench.viewer.whenReady()")


@pytest.fixture
def walk_page(tmp_path: Path) -> Iterator[tuple[Page, httpx.Client, str, list[str]]]:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, "-m", "design_workbench.interfaces.cli", "serve", "--port", str(port)],
        cwd=tmp_path,
        env={
            **os.environ,
            "DW_DATA_DIR": str(tmp_path / "data"),
            "DW_CACHE_DIR": str(ROOT / ".local/cache"),
            "DW_LOG_DIR": str(tmp_path / "logs"),
        },
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=30) as client:
            deadline = time.monotonic() + 25
            while True:
                assert process.poll() is None, "Local service terminated"
                try:
                    info = client.get("/api/info")
                    if info.is_success:
                        assert info.json()["resources_ready"], "E1 requires official resources"
                        break
                except httpx.TransportError:
                    pass
                assert time.monotonic() < deadline, "Local service startup timed out"
                time.sleep(0.1)
            identifier = client.post("/api/projects", json={"name": "E1 行走验收"}).json()[
                "project_id"
            ]
            path = f"/api/projects/{identifier}"
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    channel=os.environ.get("DW_BROWSER_CHANNEL"), headless=True
                )
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                errors: list[str] = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(str(client.base_url) + f"?project={identifier}")
                settled(page)
                ARTIFACTS.mkdir(parents=True, exist_ok=True)
                yield page, client, path, errors
                assert not errors
                browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def cells(client: httpx.Client, path: str) -> dict[str, tuple[str, dict[str, str], str, bool]]:
    packet = client.post(path + "/render").json()
    return {
        ",".join(map(str, cell[:3])): (
            packet["models"][cell[3]]["name"],
            packet["models"][cell[3]]["properties"],
            cell[4],
            cell[5],
        )
        for chunk in packet["chunks"].values()
        for cell in chunk
    }


def pose(page: Page, position: list[float], target: list[float], *, orbit: bool = False) -> None:
    page.evaluate(
        """({position, target, orbit}) => {
          const v=window.workbench.viewer;
          v.camera.position.set(...position);
          if(orbit) {v.controls.target.set(...target); v.controls.update();}
          else v.camera.lookAt(...target);
          v.drawNow();
        }""",
        {"position": position, "target": target, "orbit": orbit},
    )


def state(page: Page) -> dict:
    return page.evaluate(
        """() => {const v=window.workbench.viewer; return {
          position:v.camera.position.toArray(), target:v.controls.target.toArray(),
          rotation:v.camera.quaternion.toArray(), fov:v.camera.fov,
          active:v.walk.active, locked:v.walk.locked, enabled:v.controls.enabled
        }}"""
    )


def wait_locked(page: Page) -> None:
    # pointerLockElement can change before the handler focuses the canvas.
    page.wait_for_function("""() => {
      const v = window.workbench.viewer;
      return v.walk.locked && document.activeElement === v.renderer.domElement;
    }""")
    page.locator("#walk-menu").wait_for(state="hidden")


def lock(page: Page) -> None:
    page.locator("#walk-resume").click()
    wait_locked(page)


def unlock(page: Page, panel: str = "inspector") -> None:
    page.keyboard.press("Escape")
    page.wait_for_function("!window.workbench.viewer.walk.locked")
    page.locator(f'[data-walk-panel="{panel}"]').click()


def click_edit(page: Page, button: str, status: int = 200) -> dict:
    with page.expect_response(lambda r: r.url.endswith("/edit")) as result:
        # Moving the OS pointer while locked rotates the camera; click in place.
        page.mouse.down(button=button)
        page.mouse.up(button=button)
    assert result.value.status == status, result.value.text()
    settled(page)
    return result.value.json()


@pytest.mark.e2e
def test_contextual_placement_connections_complete_door_and_visual_variants(
    walk_page: tuple[Page, httpx.Client, str, list[str]],
) -> None:
    page, client, path, _ = walk_page
    response = client.post(
        path + "/edit",
        json={
            "expected_revision": 0,
            "request_id": "placement-floor",
            "operations": [
                {
                    "op": "fill",
                    "bounds": {"low": [-2, 0, -2], "high": [7, 0, 3]},
                    "state": {"name": "oak_planks"},
                },
                {
                    "op": "fill",
                    "bounds": {"low": [0, 1, 0], "high": [0, 3, 0]},
                    "state": {"name": "stone"},
                },
            ],
        },
    )
    assert response.is_success, response.text
    page.reload()
    settled(page)

    def choose(name: str) -> None:
        page.locator("#search").fill(name)
        page.locator(f'[data-name="minecraft:{name}"]').click()
        settled(page)
        assert page.locator("#automatic-placement").is_checked()

    def click_surface(target: list[float], camera: list[float], *, tool: str = "place") -> dict:
        page.locator(f'[data-tool="{tool}"]').click()
        coordinates = page.evaluate(
            """({target, camera}) => {
          const v=window.workbench.viewer;
          v.camera.position.set(...camera); v.controls.target.set(...target);
          v.controls.update(); v.drawNow();
          const p=v.camera.position.clone().set(...target).project(v.camera);
          const r=v.renderer.domElement.getBoundingClientRect();
          return [r.x+(p.x+1)*r.width/2,r.y+(1-p.y)*r.height/2];
        }""",
            {"target": target, "camera": camera},
        )
        with page.expect_response(lambda r: r.url.endswith("/edit")) as edited:
            page.mouse.click(*coordinates)
        assert edited.value.status == 200, edited.value.text()
        settled(page)
        return edited.value.json()

    choose("oak_slab")
    click_surface([3.5, 1, 0.5], [3.5, 6, 5])
    assert cells(client, path)["3,1,0"][1]["type"] == "bottom"
    click_surface([3.5, 1.5, 0.5], [3.5, 6, 5])
    assert cells(client, path)["3,1,0"][1]["type"] == "double"
    page.locator("#undo").click()
    settled(page)
    assert cells(client, path)["3,1,0"][1]["type"] == "bottom"
    page.locator("#redo").click()
    settled(page)
    assert cells(client, path)["3,1,0"][1]["type"] == "double"

    choose("torch")
    click_surface([0.5, 1.4, 1], [0.5, 2, 6])
    torch = cells(client, path)["0,1,1"]
    assert torch[0] == "minecraft:wall_torch" and torch[1]["facing"] == "south"
    choose("ladder")
    click_surface([0.5, 2.4, 1], [0.5, 3, 6])
    assert cells(client, path)["0,2,1"][1]["facing"] == "south"

    choose("oak_door")
    click_surface([5.5, 1, 0.5], [5.5, 6, 5])
    placed = cells(client, path)
    assert placed["5,1,0"][1]["half"] == "lower"
    assert placed["5,2,0"][1]["half"] == "upper"
    page.locator("#undo").click()
    settled(page)
    assert "5,1,0" not in cells(client, path) and "5,2,0" not in cells(client, path)
    page.locator("#redo").click()
    settled(page)
    assert "5,2,0" in cells(client, path)
    click_surface([5.5, 1.5, 1], [5.5, 2, 6], tool="erase")
    assert "5,1,0" not in cells(client, path) and "5,2,0" not in cells(client, path)

    choose("iron_bars")
    click_surface([1.5, 1, 0.5], [1.5, 6, 5])
    click_surface([2.5, 1, 0.5], [2.5, 6, 5])
    placed = cells(client, path)
    assert placed["1,1,0"][1]["east"] == "true"
    assert placed["2,1,0"][1]["west"] == "true"
    page.locator("#undo").click()
    settled(page)
    assert cells(client, path)["1,1,0"][1]["east"] == "false"
    page.locator("#redo").click()
    settled(page)
    assert cells(client, path)["1,1,0"][1]["east"] == "true"

    choose("andesite_stairs")
    shapes = page.locator('[data-variant-property="shape"]')
    assert shapes.count() == 5
    page.wait_for_function("""() => [...document.querySelectorAll('[data-variant-property="shape"] img')]
      .every(image => image.complete && image.naturalWidth > 0)""")
    page.locator('[data-variant-property="shape"][data-variant-value="outer_left"]').click()
    assert not page.locator("#automatic-placement").is_checked()
    page.locator('[data-variant-property="half"][data-variant-value="top"]').click()
    click_surface([6.5, 1, 0.5], [6.5, 6, 5])
    placed = cells(client, path)["6,1,0"][1]
    assert placed["shape"] == "outer_left" and placed["half"] == "top"
    page.locator("#automatic-placement").check()
    assert page.locator("#automatic-placement").is_checked()
    page.locator("#properties").screenshot(path=str(ARTIFACTS / "placement-shape-controls.png"))
    page.locator("#fit").click()
    settled(page)
    page.screenshot(path=str(ARTIFACTS / "placement-result.png"))

    revision = client.get(path).json()["revision"]
    exact = client.post(
        path + "/edit",
        json={
            "expected_revision": revision,
            "request_id": "old-half-door",
            "auto_connect": False,
            "complete_structures": False,
            "operations": [
                {
                    "op": "set",
                    "blocks": [
                        {
                            "position": [7, 1, 2],
                            "state": {"name": "oak_door", "properties": {"half": "lower"}},
                        },
                    ],
                }
            ],
        },
    )
    assert exact.is_success, exact.text
    page.locator("#save").click()
    settled(page)
    page.locator("#check").click()
    page.wait_for_function("!document.querySelector('#apply-rules').hidden")
    assert "7, 1, 2" in page.locator("#check-issues").inner_text()
    page.locator("#apply-rules").click()
    settled(page)
    assert "7,2,2" not in cells(client, path)
    page.locator("#commit").click()
    settled(page)
    assert cells(client, path)["7,2,2"][1]["half"] == "upper"


@pytest.mark.e2e
def test_first_person_immersive_material_menu_and_layout_restore(
    walk_page: tuple[Page, httpx.Client, str, list[str]],
) -> None:
    page, client, path, _ = walk_page
    page.locator("#cabin").click()
    settled(page)
    page.locator("#toggle-library").click()
    assert page.locator("#library").is_hidden()
    assert page.locator("#inspector").is_visible()
    saved_panels = page.evaluate("localStorage.getItem('workbench.panels')")
    saved_parents = page.evaluate("""() => Object.fromEntries(
      ['library','inspector','undo','walk-toggle','compare','slice-controls'].map(id=>
        [id, document.getElementById(id).parentElement.className || document.getElementById(id).parentElement.id]))""")
    assert page.locator("#walk-toggle").inner_text() == "第一人称"
    page.locator("#walk-toggle").click()
    wait_locked(page)
    page.wait_for_function("document.querySelector('#stage canvas').clientWidth === innerWidth")
    assert page.locator("#stage").bounding_box() == {"x": 0, "y": 0, "width": 1440, "height": 1000}
    for selector in ("header", "footer", ".toolbar", "#library", "#inspector", "#walk-menu"):
        assert page.locator(selector).is_hidden()
    assert page.locator("#walk-crosshair").is_visible()
    assert page.locator("#walk-material-name").inner_text() == "橡木木板"
    pose(page, [4.5, 2.62, 6.5], [8.5, 2.62, 6.5])
    page.screenshot(path=str(ARTIFACTS / "immersive-interior.png"))

    unlock(page, "library")
    assert page.locator("#stage").bounding_box() == {"x": 0, "y": 0, "width": 1440, "height": 1000}
    assert page.locator("#walk-toggle").inner_text() == "退出第一人称"
    assert page.locator("#walk-menu").is_visible()
    assert page.locator("#library").is_visible()
    assert page.locator("#inspector").is_hidden()
    assert page.locator("#walk-crosshair").is_hidden()
    with page.expect_response(lambda r: "/api/catalog?" in r.url):
        page.locator("#search").fill("spruce_stairs")
    page.locator('[data-name="minecraft:spruce_stairs"]').click()
    settled(page)
    page.locator('[data-variant-property="facing"][data-variant-value="east"]').click()
    settled(page)
    assert "云杉" in page.locator("#walk-material-name").inner_text()
    assert "朝东" in page.locator("#walk-material-properties").inner_text()
    page.wait_for_function("!document.querySelector('#walk-material-image').hidden")
    assert page.locator("#walk-material-image").is_visible()
    page.screenshot(path=str(ARTIFACTS / "immersive-material-menu.png"))
    lock(page)
    assert page.locator("#walk-menu").is_hidden()
    pose(page, [4.5, 2.62, 6.5], [8.5, 2.62, 6.5])
    assert click_edit(page, "right")["changed"] == 1
    placed = cells(client, path)["7,2,6"]
    assert placed[0] == "minecraft:spruce_stairs"
    assert placed[1]["facing"] == "east"

    unlock(page)
    assert page.locator("#inspector").is_visible()
    assert page.locator("#library").is_hidden()
    assert page.locator("#low").is_visible()
    assert page.locator("#layer-number").is_visible()
    page.locator("#undo").click()
    settled(page)
    assert "7,2,6" not in cells(client, path)
    page.screenshot(path=str(ARTIFACTS / "immersive-tools-menu.png"))
    page.locator("#walk-toggle").click()
    assert not state(page)["active"]
    assert page.locator("#library").is_hidden() and page.locator("#inspector").is_visible()
    assert page.evaluate("localStorage.getItem('workbench.panels')") == saved_panels
    assert (
        page.evaluate("""() => Object.fromEntries(
      ['library','inspector','undo','walk-toggle','compare','slice-controls'].map(id=>
        [id, document.getElementById(id).parentElement.className || document.getElementById(id).parentElement.id]))""")
        == saved_parents
    )
    assert page.locator("header").is_visible() and page.locator("footer").is_visible()

    page.set_viewport_size({"width": 640, "height": 500})
    page.locator("#walk-toggle").click()
    wait_locked(page)
    page.wait_for_function("document.querySelector('#stage canvas').clientWidth === innerWidth")
    assert page.locator("#stage").bounding_box() == {"x": 0, "y": 0, "width": 640, "height": 500}
    unlock(page)
    exit_box = page.locator("#walk-toggle").bounding_box()
    assert exit_box and exit_box["y"] >= 0 and exit_box["y"] + exit_box["height"] <= 500
    assert page.locator("#low").is_visible()
    low_box = page.locator("#low").bounding_box()
    assert low_box and 0 <= low_box["y"] < low_box["y"] + low_box["height"] <= 500
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.screenshot(path=str(ARTIFACTS / "immersive-narrow-menu.png"))
    page.locator("#layer-number").scroll_into_view_if_needed()
    exit_box = page.locator("#walk-toggle").bounding_box()
    assert exit_box and 0 <= exit_box["y"] < exit_box["y"] + exit_box["height"] <= 500
    page.locator("#walk-toggle").click()
    assert page.locator("#walk-toggle").inner_text() == "第一人称"


@pytest.mark.e2e
def test_walk_cabin_edits_history_reopen_and_conflict(
    walk_page: tuple[Page, httpx.Client, str, list[str]],
) -> None:
    page, client, path, errors = walk_page
    page.locator("#cabin").click()
    settled(page)
    baseline = cells(client, path)
    assert len(baseline) == 449
    pose(page, [4.5, 8, 14], [4.5, 8, 0], orbit=True)
    saved = state(page)
    page.evaluate("""() => {
      window.e1InputTrace=[];
      for(const name of ['keydown','keyup','pointerlockchange','visibilitychange','blur','focus']) {
        (name==='blur'||name==='focus'?window:document).addEventListener(name,e=>window.e1InputTrace.push({
          name, code:e.code, target:e.target?.tagName, time:performance.now(),
          focused:document.hasFocus(), hidden:document.hidden, locked:!!document.pointerLockElement
        }));
      }
    }""")
    requests: list[dict] = []
    page.on(
        "request", lambda r: requests.append(r.post_data_json) if r.url.endswith("/edit") else None
    )
    page.locator("#walk-toggle").click()
    wait_locked(page)
    assert state(page)["fov"] == 70
    assert state(page)["position"][1] == pytest.approx(2.62)
    assert not state(page)["enabled"]
    page.keyboard.down("w")
    try:
        # The per-frame movement cap makes software-rendered CI advance more slowly.
        page.wait_for_function("window.workbench.viewer.camera.position.z < 9", timeout=15_000)
    finally:
        page.keyboard.up("w")
    inside = state(page)["position"]
    input_trace = page.evaluate("window.e1InputTrace")
    assert 4 < inside[2] < 9, (inside, input_trace)  # Through Z=10.
    assert inside[:2] == pytest.approx([4.5, 2.62])

    pose(page, inside, [8.5, 2.62, inside[2]])
    hit = page.evaluate("window.workbench.viewer.pickCenter()")
    assert hit["position"][0] == 8
    placed = [v + n for v, n in zip(hit["position"], hit["normal"], strict=True)]
    assert ",".join(map(str, placed)) not in baseline
    added = click_edit(page, "right")
    assert added["changed"] == 1 and added["revision"] == 2
    pose(page, inside, [0.5, 2.62, inside[2]])
    removed = page.evaluate("window.workbench.viewer.pickCenter().position")
    deleted = click_edit(page, "left")
    assert deleted["changed"] == 1 and deleted["revision"] == 3
    edited = cells(client, path)
    assert edited[",".join(map(str, placed))][0] == "minecraft:oak_planks"
    assert ",".join(map(str, removed)) not in edited
    assert [r["expected_revision"] for r in requests] == [1, 2]
    assert len({r["request_id"] for r in requests}) == 2
    page.locator("#stage").screenshot(path=str(ARTIFACTS / "cabin-interior.png"))
    with page.expect_response(lambda r: r.url.endswith("/history/undo")):
        page.keyboard.press("Control+z")
    settled(page)
    assert ",".join(map(str, removed)) in cells(client, path)
    with page.expect_response(lambda r: r.url.endswith("/history/redo")):
        page.keyboard.press("Control+Shift+z")
    settled(page)
    assert state(page)["active"] and cells(client, path) == edited
    edit_revision = client.get(path).json()["revision"]
    assert edit_revision == 5

    # Alt selects even though ordinary left click deletes; Shift must only descend.
    for target in ([p + 0.5 for p in placed], [inside[0], 0.5, inside[2]]):
        pose(page, inside, target)
        page.keyboard.down("Alt")
        page.mouse.down()
        page.mouse.up()
        page.keyboard.up("Alt")
        settled(page)
    selection = page.evaluate("window.workbench.selection")
    assert selection["low"][1] == 1 and selection["high"][1] == placed[1]
    assert "Alt+点击" in page.locator("#selection-hint").text_content()
    y = state(page)["position"][1]
    page.keyboard.down("Shift")
    page.wait_for_timeout(180)
    page.keyboard.up("Shift")
    assert state(page)["position"][1] < y - 0.5
    assert page.evaluate("window.workbench.selection") == selection
    assert client.get(path).json()["revision"] == edit_revision

    unlock(page)
    page.locator("#low").fill("3,1,3")
    page.locator("#high").fill("3,1,3")
    page.locator("#select-bounds").click()
    page.locator("#preview").click()
    settled(page)
    lock(page)
    assert page.evaluate("window.workbench.viewer.ghosts.children.length") > 0
    unlock(page)
    assert page.locator("#cancel-preview").is_visible()
    page.keyboard.press("Escape")
    assert page.locator("#cancel-preview").is_hidden()
    assert state(page)["active"]

    # Before/after and groups stay usable without changing the walking camera.
    camera = state(page)["position"]
    page.locator("#compare").select_option("before")
    settled(page)
    assert state(page)["position"] == camera
    assert page.evaluate(
        "window.workbench.viewer.occupied().has('" + ",".join(map(str, removed)) + "')"
    )
    page.locator("#compare").select_option("current")
    settled(page)
    page.locator("#group-tree button").filter(has_text="floor").click()
    assert page.locator("#group-filter").input_value() == "floor"

    # Commit the competing writer after the browser constructs its edit request.
    # Otherwise external-change polling can legitimately refresh the browser first.
    conflict_scene: dict[str, tuple[str, dict[str, str], str, bool]] = {}

    def competing_writer(route: Route) -> None:
        assert route.request.post_data_json["expected_revision"] == edit_revision
        response = client.post(
            path + "/edit",
            json={
                "expected_revision": edit_revision,
                "request_id": "other-writer",
                "operations": [
                    {"op": "set", "blocks": [{"position": [20, 0, 0], "state": {"name": "stone"}}]}
                ],
            },
        )
        assert response.is_success
        conflict_scene.update(cells(client, path))
        route.continue_()

    lock(page)
    pose(page, inside, [p + 0.5 for p in placed])
    page.route("**" + path + "/edit", competing_writer)
    try:
        conflict = click_edit(page, "left", 409)
    finally:
        page.unroute("**" + path + "/edit", competing_writer)
    assert conflict["error"]["code"] == "REVISION_CONFLICT"
    assert cells(client, path) == conflict_scene
    page.keyboard.press("g")
    restored = state(page)
    for field in ("position", "target", "rotation", "fov"):
        assert restored[field] == pytest.approx(saved[field])
    assert not restored["active"] and restored["enabled"]

    page.reload()
    settled(page)
    assert state(page)["fov"] == 40 and not state(page)["active"]
    assert cells(client, path) == conflict_scene
    assert page.evaluate("window.workbench.summary.revision") == edit_revision + 1
    for _ in range(3):
        page.locator("#undo").click()
        settled(page)
    assert cells(client, path) == baseline
    for _ in range(2):
        page.locator("#redo").click()
        settled(page)
    assert cells(client, path) == edited
    page.set_viewport_size({"width": 640, "height": 900})
    toggle = page.locator("#walk-toggle")
    assert toggle.is_visible()
    toggle.click()
    wait_locked(page)
    page.screenshot(path=str(ARTIFACTS / "narrow-controls.png"))
    page.keyboard.press("g")
    assert not state(page)["active"]
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    (ARTIFACTS / "cabin-report.json").write_text(
        json.dumps(
            {
                "browser": page.context.browser.version,
                "baseline_blocks": len(baseline),
                "inside": inside,
                "placed": placed,
                "removed": removed,
                "single_click_revisions": [added["revision"], deleted["revision"]],
                "walking_undo_redo": True,
                "alt_expands_selection": True,
                "shift_only_descends": True,
                "escape_preserves_then_cancels_preview": True,
                "comparison_and_groups": True,
                "input_trace": input_trace,
                "conflict_status": 409,
                "reopen_persisted": True,
                "undo_to_baseline": True,
                "redo_persisted": True,
                "camera_restored": restored,
                "errors": errors,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


@pytest.mark.e2e
def test_walk_motion_mouse_speed_pause_and_shortcuts(
    walk_page: tuple[Page, httpx.Client, str, list[str]],
) -> None:
    page, _, _, _ = walk_page
    pose(page, [0, 10, 10], [0, 10, 0], orbit=True)
    page.locator("#walk-toggle").click()
    wait_locked(page)
    assert state(page)["position"][1] == pytest.approx(1.62)

    def fly(keys: list[str], duration: int) -> float:
        before = state(page)["position"]
        for key in keys:
            page.keyboard.down(key)
        page.wait_for_timeout(duration)
        for key in reversed(keys):
            page.keyboard.up(key)
        after = state(page)["position"]
        return sum((a - b) ** 2 for a, b in zip(after, before, strict=True)) ** 0.5

    normal = fly(["w"], 400)
    fast = fly(["Control", "w"], 400)
    assert 2.4 < normal < 4.2
    assert 1.6 < fast / normal < 2.5
    assert fly(["Space"], 180) > 0.6
    assert page.locator("#layer-play").get_attribute("aria-pressed") == "false"
    before_rotation = state(page)["rotation"]
    page.mouse.move(700, 400)
    page.mouse.move(800, 450)
    assert state(page)["rotation"] != before_rotation
    # Look vertically up using actual pointer input, then still move horizontally.
    page.mouse.move(800, -2000)
    direction = page.evaluate(
        "window.workbench.viewer.camera.getWorldDirection(window.workbench.viewer.camera.position.clone()).toArray()"
    )
    assert direction[1] > 0.99
    before_y = state(page)["position"][1]
    assert fly(["w"], 180) > 0.6
    assert state(page)["position"][1] == pytest.approx(before_y)
    # Simulate a long main-thread stall; the resumed frame must cap displacement.
    start = state(page)["position"]
    page.keyboard.down("w")
    page.evaluate("() => {const until=performance.now()+800; while(performance.now()<until) {}}")
    page.keyboard.up("w")
    end = state(page)["position"]
    stall_distance = sum((a - b) ** 2 for a, b in zip(end, start, strict=True)) ** 0.5
    assert stall_distance < 1.6, stall_distance
    page.keyboard.down("w")
    page.evaluate("window.dispatchEvent(new Event('blur'))")
    stopped = state(page)["position"]
    page.wait_for_timeout(180)
    assert state(page)["position"] == stopped
    page.keyboard.up("w")
    unlock(page)
    stopped = state(page)["position"]
    assert fly(["w"], 180) == 0
    page.locator("#low").fill("g")
    page.locator("#low").press("g")
    assert state(page)["active"]
    page.locator("#operation").focus()
    page.keyboard.press("g")
    assert state(page)["active"]
    page.locator("#operation").select_option("extrude")
    page.locator("#polygon").press("g")
    assert state(page)["active"]
    lock(page)
    page.keyboard.press("?")
    page.locator("#help-dialog").wait_for(state="visible")
    page.wait_for_function("!window.workbench.viewer.walk.locked")
    page.keyboard.press("Escape")
    assert page.locator("#help-dialog").is_hidden()
    assert state(page)["active"] and page.locator("#walk-menu").is_visible()
    page.locator("#walk-toggle").click()
    assert not state(page)["active"]
    (ARTIFACTS / "motion-report.json").write_text(
        json.dumps(
            {
                "normal_distance_400ms": normal,
                "fast_distance_400ms": fast,
                "stall_distance_800ms": stall_distance,
                "vertical_direction": direction,
                "blur_stops_motion": True,
                "unlocked_stops_motion": True,
                "typing_preserves_mode": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


@pytest.mark.e2e
def test_walk_pick_distance_ground_layers_and_click_hold(
    walk_page: tuple[Page, httpx.Client, str, list[str]],
) -> None:
    page, client, path, _ = walk_page
    response = client.post(
        path + "/edit",
        json={
            "expected_revision": 0,
            "request_id": "pick-fixture",
            "operations": [
                {
                    "op": "set",
                    "blocks": [
                        {"position": [0, y, 0], "state": {"name": "oak_planks"}} for y in (-2, 0, 3)
                    ],
                }
            ],
        },
    )
    assert response.is_success
    page.reload()
    settled(page)
    pose(page, [0.5, 0.5, 10], [0.5, 0.5, 0.5], orbit=True)
    page.locator("#walk-toggle").click()
    wait_locked(page)
    pose(page, [0.5, 0.5, 10], [0.5, 0.5, 0.5])
    assert page.evaluate("window.workbench.viewer.pickCenter()") is None
    unlock(page)
    page.locator("#walk-reach").fill("12")
    page.locator("#walk-reach").press("Tab")
    assert page.evaluate("window.workbench.viewer.pickCenter().position") == [0, 0, 0]
    page.locator("#walk-reach").fill("0")
    page.locator("#walk-reach").press("Tab")
    assert page.evaluate("window.workbench.viewer.walkReach") == 12
    page.locator("#walk-reach").fill("5")
    page.locator("#walk-reach").press("Tab")
    pose(page, [0.5, 0.5, 6], [0.5, 0.5, 0.5])
    assert page.evaluate("window.workbench.viewer.pickCenter().position") == [0, 0, 0]  # Exactly 5.
    pose(page, [0.5, 0.5, 6.01], [0.5, 0.5, 0.5])
    assert page.evaluate("window.workbench.viewer.pickCenter()") is None
    assert (
        page.evaluate("""() => {const v=window.workbench.viewer, r=v.renderer.domElement.getBoundingClientRect();
      return v.pick(new PointerEvent('pointerup',{clientX:r.x+r.width/2, clientY:r.y+r.height/2})).position;}""")
        == [0, 0, 0]
    )

    # Slice hides the upper cube from the same rendered-mesh ray, without deleting it.
    page.locator("#layer-number").fill("1")
    page.locator("#layer-number").press("Tab")
    settled(page)
    pose(page, [0.5, 3.5, 3], [0.5, 3.5, 0.5])
    assert page.evaluate("window.workbench.viewer.pickCenter()") is None
    pose(page, [0.5, -1.5, 3], [0.5, -1.5, 0.5])
    assert page.evaluate("window.workbench.viewer.pickCenter().position") == [0, -2, 0]
    assert len(cells(client, path)) == 3
    page.locator("#layer-reset").click()
    settled(page)
    pose(page, [4.5, 1.62, 4.5], [4.5, 0, 4.5])
    assert page.evaluate("window.workbench.viewer.pickCenter().ground")
    lock(page)
    ground = click_edit(page, "right")
    assert ground["changed"] == 1
    assert "4,0,4" in cells(client, path)
    # A held pointer does not auto-repeat, and cannot overwrite an occupied adjacent cell.
    pose(page, [0.5, 3.5, 3], [0.5, 3.5, 0.5])
    with page.expect_response(lambda r: r.url.endswith("/edit")):
        page.mouse.down(button="right")
        page.wait_for_timeout(400)
        page.mouse.up(button="right")
    settled(page)
    assert client.get(path).json()["revision"] == 3
    pose(page, [0.5, 3.5, 3], [0.5, 3.5, 0.5])
    # Now the nearest block is the new one; place another then stand inside it.
    second = click_edit(page, "right")
    assert second["revision"] == 4
    pose(page, [0.5, 3.5, 2.5], [0.5, 3.5, 0])
    assert page.evaluate("window.workbench.viewer.occupied().has('0,3,2')")
    page.keyboard.down("d")
    page.wait_for_timeout(180)
    page.keyboard.up("d")
    assert state(page)["position"][0] > 1  # No collision with the cube we started inside.
    unlock(page)
    page.locator("#walk-reach").fill("7")
    page.locator("#walk-reach").press("Tab")
    page.locator("#walk-toggle").click()
    page.reload()
    settled(page)
    assert page.evaluate("window.workbench.viewer.walkReach") == 7
    assert not state(page)["active"]
    (ARTIFACTS / "pick-report.json").write_text(
        json.dumps(
            {
                "reach_default": 5,
                "reach_configured": 12,
                "reach_persisted_after_reload": 7,
                "range_boundary": True,
                "ground_position": [4, 0, 4],
                "negative_y_pick": [0, -2, 0],
                "hidden_layer_not_pickable": True,
                "held_click_edits": 1,
                "collision_free": True,
                "project_camera_not_persisted": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
