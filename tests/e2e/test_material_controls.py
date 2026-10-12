"""Regressions for material inspector interactions during async requests."""

import json

import httpx
import pytest
import test_walk
from playwright.sync_api import Page, Route

walk_page = test_walk.walk_page
settled = test_walk.settled


def choose(page: Page, name: str) -> None:
    page.locator("#search").fill(name)
    page.locator(f'[data-name="minecraft:{name}"]').click()
    settled(page)


@pytest.mark.e2e
def test_inspector_cannot_change_while_preview_is_pending(
    walk_page: tuple[Page, httpx.Client, str, list[str]],
) -> None:
    page, _, path, _ = walk_page
    choose(page, "andesite_stairs")
    held: list[Route] = []
    page.route("**" + path + "/preview", lambda route: held.append(route))
    page.locator("#preview").click()
    page.wait_for_function("window.workbench.busy")
    page.wait_for_function(
        "document.getElementById('properties').inert || [...document.querySelectorAll('#properties input,#properties select,#properties button')].every(e=>e.disabled)"
    )
    assert page.locator("#automatic-placement").is_checked()
    assert (
        page.locator(
            '[data-variant-property="shape"][data-variant-value="straight"]'
        ).get_attribute("aria-pressed")
        == "true"
    )
    assert held
    held[0].continue_()
    settled(page)
    assert page.locator("#cancel-preview").is_visible()
    page.locator('[data-variant-property="shape"][data-variant-value="outer_left"]').click()
    assert not page.locator("#automatic-placement").is_checked()
    assert page.locator("#cancel-preview").is_hidden()


@pytest.mark.e2e
def test_old_project_variant_thumbnail_cannot_replace_current_atlas(
    walk_page: tuple[Page, httpx.Client, str, list[str]],
) -> None:
    page, client, _, _ = walk_page
    choose(page, "andesite_stairs")
    held: list[tuple[Route, dict]] = []

    def hold_old_variant(route: Route) -> None:
        if held:
            route.continue_()
            return
        response = route.fetch()
        held.append((route, response.json()))

    # A property redraw launches independent thumbnails. Delay one old-project
    # response while allowing HUD and project navigation requests to finish.
    page.route("**/api/material/andesite_stairs?**", hold_old_variant)
    page.locator('[data-variant-property="shape"][data-variant-value="inner_left"]').click()
    page.wait_for_function("!window.workbench.busy")
    page.wait_for_timeout(100)
    assert held
    new_project = client.post("/api/projects", json={"name": "缩略图切换回归"}).json()["project_id"]
    # Trigger a project list refresh via the new-project button would prompt and
    # create another file; adding the existing server project is the exact UI path.
    page.evaluate(
        "id => document.getElementById('projects').add(new Option('切换项目', id))", new_project
    )
    page.locator("#projects").select_option(new_project)
    page.wait_for_function(
        "id => window.workbench.project === id && !window.workbench.busy", arg=new_project
    )
    settled(page)
    current_width = page.evaluate("window.workbench.viewer.atlas.width")
    delayed_route, delayed_model = held[0]
    delayed_model["atlas"]["width"] = 12345
    delayed_route.fulfill(
        status=200, content_type="application/json", body=json.dumps(delayed_model)
    )
    page.wait_for_timeout(150)
    assert page.evaluate("window.workbench.viewer.atlas.width") == current_width
    assert page.locator("#material-id").inner_text() == "minecraft:oak_planks"
