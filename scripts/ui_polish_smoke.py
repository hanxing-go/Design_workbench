"""Read-only visual/interaction QA for the Minecraft landing-page polish."""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    output = Path("artifacts/ui-polish")
    output.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        page.on("pageerror", lambda error: errors.append(str(error)))
        base = "http://127.0.0.1:8766"
        before = page.request.get(f"{base}/api/projects").json()
        for name in [
            "diamond_pickaxe",
            "grass_block",
            "crafting_table",
            "chest",
            "chest_front",
            "chest_top",
        ]:
            response = page.request.get(f"{base}/api/ui/sprites/{name}.png")
            assert response.ok, (name, response.status)
            assert response.body().startswith(b"\x89PNG")
        assert page.request.get(f"{base}/api/ui/sprites/not-an-asset.png").status == 404
        page.goto(base)
        page.wait_for_selector(".home-brand .vanilla-sprite")
        page.locator("#designs").scroll_into_view_if_needed()
        page.wait_for_selector(".project-art.has-preview", timeout=60000)
        assert page.locator(".project-card strong").first.inner_text().strip()
        assert page.locator(".project-card").first.evaluate(
            "e => getComputedStyle(e).display === 'grid' && [...e.children].every(c => c.getBoundingClientRect().right <= e.getBoundingClientRect().right + 1)"
        )
        page.wait_for_function(
            "getComputedStyle(document.querySelector('#app')).cursor.includes('data:image/png')"
        )
        page.wait_for_timeout(8500)
        page.evaluate('window.scrollTo({top: 0, behavior: "instant"})')
        page.screenshot(path=str(output / "home-desktop.png"), full_page=True)
        page.locator(".home-start").screenshot(path=str(output / "start-cards.png"))
        page.locator(".home-designs").screenshot(path=str(output / "designs.png"))
        page.locator("#design-toggle").click()
        assert page.locator(".home-projects").evaluate("el => el.classList.contains('is-list')")
        page.locator("#design-toggle").click()
        page.locator("#home-search").fill("不存在的设计-QA")
        assert page.locator("#home-no-results").is_visible()
        page.locator("#home-clear-search").click()
        assert page.locator(".project-card").count() == len(before["items"])
        page.locator(".hero-create").click()
        assert page.locator("#home-create-dialog").is_visible()
        assert page.locator("#home-project-name").evaluate("el => el === document.activeElement")
        page.keyboard.press("Escape")
        assert not page.locator("#home-create-dialog").is_visible()
        page.goto(f"{base}/?view=sponsor")
        page.wait_for_selector(".sponsor-diamond-large .vanilla-sprite")
        page.mouse.move(20, 500)
        page.wait_for_timeout(800)
        page.locator(".sponsor-art").screenshot(path=str(output / "chest-closed.png"))
        page.screenshot(path=str(output / "sponsor-desktop.png"), full_page=True)
        chest = page.locator("#community-chest")
        chest.hover()
        page.wait_for_timeout(850)
        page.locator(".sponsor-art").screenshot(path=str(output / "chest-open.png"))
        chest.click()
        page.mouse.move(20, 500)
        assert chest.get_attribute("aria-pressed") == "true"
        chest.focus()
        page.keyboard.press("Enter")
        assert chest.get_attribute("aria-pressed") == "false"
        for width in [390, 768, 1920]:
            page.set_viewport_size({"width": width, "height": 900})
            for route, name in [("/", "home"), ("/?view=sponsor", "sponsor")]:
                page.goto(base + route)
                page.wait_for_selector(".home-brand .vanilla-sprite")
                page.wait_for_timeout(1200)
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
                    name,
                    width,
                )
                if width == 390:
                    if name == "home":
                        page.locator("#designs").scroll_into_view_if_needed()
                        page.wait_for_selector(".project-art.has-preview", timeout=30000)
                        page.evaluate('window.scrollTo({top: 0, behavior: "instant"})')
                        page.wait_for_timeout(8500)
                    page.screenshot(path=str(output / f"{name}-mobile.png"), full_page=True)
        page.emulate_media(reduced_motion="reduce")
        page.goto(f"{base}/?view=sponsor")
        page.wait_for_selector("#community-chest")
        assert (
            page.locator(".chest-particles i").first.evaluate(
                "el => getComputedStyle(el).animationName"
            )
            == "none"
        )
        after = page.request.get(f"{base}/api/projects").json()
        assert [(p["project_id"], p["revision"]) for p in before["items"]] == [
            (p["project_id"], p["revision"]) for p in after["items"]
        ]
        assert not errors, errors
        (output / "qa.json").write_text(
            json.dumps(
                {
                    "browser_errors": errors,
                    "viewports": [390, 768, 1440, 1920],
                    "projects_unchanged": True,
                    "checks": "assets, previews, cursor, search, list toggle, dialog focus/Escape, chest hover/click/keyboard, reduced motion, overflow",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        browser.close()
    print(f"PASS: visual and interaction QA; screenshots in {output}")


if __name__ == "__main__":
    main()
