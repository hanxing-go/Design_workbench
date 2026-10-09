"""Real user workflows, visual artifacts and P5 browser performance gates."""

import json
import os
import statistics
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).parents[1]
ARTIFACTS = ROOT / "artifacts"
BASE = os.environ.get("DW_TEST_URL", "http://127.0.0.1:8765")


def ready(page: Page) -> None:
    page.wait_for_function("window.workbench && !window.workbench.busy", timeout=60000)
    page.wait_for_function("window.workbench.viewer.drawHandle === 0", timeout=60000)
    status = page.locator("#status")
    assert "error" not in (status.get_attribute("class") or ""), status.inner_text()


def click(page: Page, selector: str) -> None:
    page.locator(selector).click()
    ready(page)


def verify_design_tools(page: Page) -> dict[str, object]:
    page.once("dialog", lambda dialog: dialog.accept("高级工具验收"))
    click(page, "#new-project")
    identifier = page.evaluate("window.workbench.project")

    def inspect(group: str) -> list[dict[str, object]]:
        response = page.request.post(
            f"{BASE}/api/projects/{identifier}/inspect", data={"group": group}
        )
        assert response.ok, response.text()
        return response.json()["blocks"]

    def bounds(low: str, high: str) -> None:
        page.locator("#low").fill(low)
        page.locator("#high").fill(high)
        click(page, "#select-bounds")

    def material(name: str) -> None:
        page.locator("#search").fill(name)
        page.wait_for_selector(f'[data-name="minecraft:{name}"]')
        ready(page)
        click(page, f'[data-name="minecraft:{name}"]')

    def apply() -> None:
        revision = page.evaluate("window.workbench.summary.revision")
        click(page, "#preview")
        assert page.evaluate("window.workbench.summary.revision") == revision
        click(page, "#commit")
        assert page.evaluate("window.workbench.summary.revision") == revision + 1

    material("oak_stairs")
    page.locator('[data-property="facing"]').select_option("west")
    page.locator('[data-property="half"]').select_option("top")
    bounds("0,0,0", "0,0,0")
    page.locator("#operation").select_option("fill")
    page.locator("#result-group").fill("parts")
    apply()
    state = inspect("parts")[0]
    assert state["properties"]["facing"] == "west"
    assert state["properties"]["half"] == "top"
    page.locator("#compare").select_option("before")
    ready(page)
    assert page.evaluate("window.workbench.viewer.chunks.size") == 0
    page.locator("#compare").select_option("current")
    ready(page)
    assert page.evaluate("window.workbench.viewer.chunks.size") == 1
    bounds("2,0,0", "2,0,0")
    apply()
    click(page, "#fit")
    click(page, '[data-view="front"]')
    canvas = page.locator("#stage canvas")

    def hit(x: float, shift: bool = False) -> None:
        position = page.evaluate(
            """x => {
              const w=window.workbench.viewer,c=w.camera;
              c.updateMatrixWorld();const T=c.position.constructor;
              const p=new T(x,.75,1.001).project(c);
              const r=w.renderer.domElement.getBoundingClientRect();
              return {x:(p.x+1)*r.width/2,y:(1-p.y)*r.height/2};
            }""",
            x,
        )
        canvas.click(position=position, modifiers=["Shift"] if shift else [])
        ready(page)

    hit(0.5)
    hit(2.5, True)
    assert page.evaluate("window.workbench.selection") == {"low": [0, 0, 0], "high": [2, 0, 0]}
    page.locator("#operation").select_option("group")
    page.locator("#result-group").fill("columns")
    apply()
    assert len(inspect("columns")) == 2
    page.locator("#group-tree button").filter(has_text="columns").click()
    assert page.locator("#group-filter").input_value() == "columns"
    page.locator("#operation").select_option("transform")
    page.locator("#offset").fill("8,0,0")
    page.locator("#rotation").select_option("90")
    page.locator("#mirror").select_option("x")
    page.locator("#copy").check()
    page.locator("#result-group").fill("transformed")
    apply()
    assert {tuple(block["position"]) for block in inspect("transformed")} == {(8, 0, 0), (8, 0, -2)}
    page.locator("#group-filter").select_option("transformed")
    page.locator("#operation").select_option("transform")
    page.locator("#offset").fill("0,0,4")
    page.locator("#result-group").fill("moved")
    apply()
    assert not inspect("transformed") and len(inspect("moved")) == 2
    page.locator("#group-filter").select_option("columns")
    page.locator("#operation").select_option("array")
    page.locator("#count").fill("1,1,2")
    page.locator("#step").fill("0,0,8")
    page.locator("#result-group").fill("array")
    apply()
    assert len(inspect("array")) == 2
    material("stone")
    page.locator("#operation").select_option("extrude")
    page.locator("#polygon").fill("20,0\n23,0\n23,3\n20,3")
    page.locator("#height").fill("2")
    page.locator("#result-group").fill("extruded")
    apply()
    assert len(inspect("extruded")) == 18
    page.locator("#operation").select_option("arc")
    page.locator("#center").fill("30,0,20")
    page.locator("#radius").fill("4")
    page.locator("#height").fill("2")
    page.locator("#end-angle").fill("180")
    page.locator("#result-group").fill("arc")
    apply()
    assert inspect("arc")
    material("oak_stairs")
    bounds("20,4,0", "26,4,4")
    page.locator("#operation").select_option("roof")
    page.locator("#result-group").fill("roof")
    apply()
    assert len(inspect("roof")) == 35
    material("glass")
    bounds("20,1,0", "24,3,0")
    page.locator("#operation").select_option("window")
    page.locator("#result-group").fill("windows")
    apply()
    assert len(inspect("windows")) == 15
    assert any(block["name"] == "minecraft:glass" for block in inspect("windows"))
    page.locator("#group-filter").select_option("array")
    page.locator("#operation").select_option("delete")
    apply()
    assert not inspect("array")
    # A canceled preview must leave both authority and revision unchanged.
    before = page.evaluate("window.workbench.summary.revision")
    page.locator("#group-filter").select_option("roof")
    click(page, "#preview")
    click(page, "#cancel-preview")
    assert page.evaluate("window.workbench.summary.revision") == before
    assert len(inspect("roof")) == 35
    click(page, "#check")
    assert page.locator("#check-result").inner_text()
    # Below-ground blocks remain selectable and erasable, independently of the empty-ground hit.
    material("stone")
    bounds("0,-2,0", "0,-2,0")
    page.locator("#operation").select_option("fill")
    page.locator("#result-group").fill("below-ground")
    apply()
    click(page, '[data-view="front"]')
    position = page.evaluate("""() => {
        const w=window.workbench.viewer,c=w.camera;
        c.updateMatrixWorld();const T=c.position.constructor;
        const p=new T(.5,-1.5,1.001).project(c);
        const r=w.renderer.domElement.getBoundingClientRect();
        return {x:(p.x+1)*r.width/2,y:(1-p.y)*r.height/2};
    }""")
    canvas.click(position=position)
    ready(page)
    assert page.evaluate("window.workbench.selection") == {"low": [0, -2, 0], "high": [0, -2, 0]}
    click(page, '[data-tool="erase"]')
    canvas.click(position=position)
    ready(page)
    assert not inspect("below-ground")
    click(page, '[data-tool="select"]')
    page.locator("#compare").select_option("before")
    ready(page)
    page.once("dialog", lambda dialog: dialog.accept("切换对比状态验收"))
    click(page, "#new-project")
    assert page.locator("#compare").input_value() == "current"
    page.locator("#projects").select_option(identifier)
    ready(page)
    page.screenshot(path=str(ARTIFACTS / "advanced-tools.png"))
    return {
        "project_id": identifier,
        "passed": True,
        "verified": [
            "properties",
            "before/current",
            "Shift selection",
            "group tree",
            "move",
            "copy",
            "rotation",
            "mirror",
            "array",
            "extrude",
            "arc",
            "roof",
            "window",
            "delete",
            "cancel preview",
            "consistency",
            "negative-Y canvas select/erase",
            "project switch resets comparison",
        ],
    }


def main() -> None:
    baseline = json.loads((ARTIFACTS / "p4-baseline.json").read_text(encoding="utf-8"))
    gates = baseline["p5_gates"]
    errors: list[str] = []
    external: list[str] = []
    report: dict[str, object] = {}
    with sync_playwright() as playwright:
        channel = os.environ.get("DW_BROWSER_CHANNEL")
        browser = playwright.chromium.launch(channel=channel, headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000}, accept_downloads=True
        )
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "request",
            lambda request: (
                external.append(request.url)
                if not request.url.startswith(BASE)
                and not request.url.startswith(("data:", "blob:"))
                else None
            ),
        )
        page.goto(BASE)
        ready(page)
        report["design_tools"] = verify_design_tools(page)
        page.once("dialog", lambda dialog: dialog.accept("浏览器验收木屋"))
        click(page, "#new-project")
        cabin_id = page.evaluate("window.workbench.project")
        click(page, "#cabin")
        original = page.evaluate("window.workbench.summary.blocks")
        assert original > 300
        page.screenshot(path=str(ARTIFACTS / "cabin-before.png"))
        page.locator("#search").fill("砖块")
        page.wait_for_function(
            "document.querySelector('[data-name=\"minecraft:bricks\"]')", timeout=30000
        )
        ready(page)
        click(page, '[data-name="minecraft:bricks"]')
        page.locator("#group-filter").select_option("roof")
        page.locator("#operation").select_option("replace")
        click(page, "#preview")
        assert page.evaluate("window.workbench.summary.revision") == 1
        assert page.locator("#preview-description").inner_text().startswith("将修改")
        click(page, "#commit")
        assert page.evaluate("window.workbench.summary.revision") == 2
        page.screenshot(path=str(ARTIFACTS / "cabin-after.png"))
        click(page, "#undo")
        assert page.evaluate("window.workbench.summary.revision") == 3
        click(page, "#redo")
        assert page.evaluate("window.workbench.summary.revision") == 4
        # Edit a window through bounds and real GUI inputs.
        page.locator("#low").fill("1,1,0")
        page.locator("#high").fill("3,3,0")
        click(page, "#select-bounds")
        page.locator("#operation").select_option("window")
        page.locator("#frame").fill("birch_log")
        click(page, "#preview")
        click(page, "#commit")
        assert page.evaluate("window.workbench.summary.revision") == 5
        # Real canvas raycast selection, then one placed block and removal.
        canvas = page.locator("#stage canvas")
        position = page.evaluate("""() => {
          const w=window.workbench.viewer,c=w.camera;
          c.updateMatrixWorld();
          const T=c.position.constructor;
          const p=new T(4.5,2.5,.01).project(c);
          const r=w.renderer.domElement.getBoundingClientRect();
          return {x:(p.x+1)*r.width/2,y:(1-p.y)*r.height/2};
        }""")
        canvas.click(position=position)
        ready(page)
        assert page.evaluate("window.workbench.selection !== null")
        click(page, '[data-tool="place"]')
        canvas.click(position=position)
        ready(page)
        revision = page.evaluate("window.workbench.summary.revision")
        assert revision == 6
        click(page, "#undo")
        click(page, '[data-tool="select"]')
        expected = page.evaluate("window.workbench.summary.blocks")
        click(page, "#save")
        page.reload()
        ready(page)
        assert page.evaluate("window.workbench.project") == cabin_id
        assert page.evaluate("window.workbench.summary.blocks") == expected
        with page.expect_download() as download:
            click(page, "#export")
        export_path = ARTIFACTS / "cabin-ui-export.litematic"
        download.value.save_as(str(export_path))
        assert export_path.stat().st_size > 100
        report["cabin"] = {
            "project_id": cabin_id,
            "blocks": expected,
            "workflow": "GUI create/cabin/material/preview/commit/window/raycast/place/undo/redo/save/reload/export",
            "export": export_path.name,
        }
        # Real file upload of the complete independently authored church.
        page.once("dialog", lambda dialog: dialog.accept("浏览器验收教堂"))
        click(page, "#new-project")
        church_id = page.evaluate("window.workbench.project")
        start = time.perf_counter()
        page.locator("#import-file").set_input_files(
            ROOT / ".local/imports/azalea-church.litematic"
        )
        ready(page)
        load_ms = (time.perf_counter() - start) * 1000
        assert page.evaluate("window.workbench.summary.blocks") == 36094
        assert load_ms < gates["browser_initial_load_ms"], load_ms
        page.screenshot(path=str(ARTIFACTS / "church-full.png"))
        total_chunks = page.evaluate("Object.keys(window.workbench.viewer.versions).length")
        page.locator("#low").fill("90,0,0")
        page.locator("#high").fill("99,9,9")
        click(page, "#select-bounds")
        page.locator("#operation").select_option("fill")
        page.locator("#result-group").fill("benchmark")
        start = time.perf_counter()
        click(page, "#commit")
        edit_ms = (time.perf_counter() - start) * 1000
        assert page.evaluate("window.workbench.summary.blocks") == 37094
        changed_chunks = (
            page.evaluate("Object.keys(window.workbench.viewer.versions).length") - total_chunks
        )
        assert changed_chunks < total_chunks
        assert edit_ms < gates["edit_1000_total_ms"], edit_ms
        click(page, "#undo")
        assert page.evaluate("window.workbench.summary.blocks") == 36094
        frame_times = page.evaluate("""() => {
          const w=window.workbench.viewer,times=[];
          for(let i=0;i<30;i++){
            w.camera.position.x += .05;
            const start=performance.now();w.drawNow();times.push(performance.now()-start);
          } return times;
        }""")
        frame_p95 = sorted(frame_times)[int(len(frame_times) * 0.95)]
        assert frame_p95 < gates["camera_frame_p95_ms"], frame_p95
        start = time.perf_counter()
        click(page, "#save")
        save_ms = (time.perf_counter() - start) * 1000
        assert save_ms < gates["save_reopen_ms"], save_ms
        page.locator("#layer").fill("25")
        page.locator("#layer").dispatch_event("input")
        ready(page)
        page.screenshot(path=str(ARTIFACTS / "church-cutaway.png"))
        for view in ("front", "side", "top", "iso"):
            click(page, f'[data-view="{view}"]')
        page.locator("#layer").fill("55")
        page.locator("#layer").dispatch_event("input")
        ready(page)
        start = time.perf_counter()
        with page.expect_download() as download:
            click(page, "#export")
        download.value.save_as(str(ARTIFACTS / "church-ui-export.litematic"))
        export_ms = (time.perf_counter() - start) * 1000
        assert export_ms < gates["export_ms"], export_ms
        report["church"] = {
            "project_id": church_id,
            "blocks": 36094,
            "import_and_display_ms": load_ms,
            "edit_1000_total_ms": edit_ms,
            "changed_chunks": changed_chunks,
            "full_chunks": total_chunks,
            "save_reopen_ms": save_ms,
            "export_ms": export_ms,
            "camera_frame_p95_ms": frame_p95,
            "camera_frame_median_ms": statistics.median(frame_times),
            "gates": gates,
            "export": "church-ui-export.litematic",
            "warnings": page.locator("#warnings").inner_text(),
        }
        page.set_viewport_size({"width": 720, "height": 960})
        page.screenshot(path=str(ARTIFACTS / "workbench-narrow.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
            "窄屏出现水平溢出"
        )
        assert not errors, errors
        assert not external, external
        report["browser"] = {
            "version": browser.version,
            "errors": errors,
            "external_requests": external,
            "narrow_width": 720,
        }
        report["passed"] = True
        (ARTIFACTS / "p5-browser-verification.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, ensure_ascii=False))
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
