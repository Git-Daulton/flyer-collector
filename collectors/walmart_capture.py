import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

STORE_URL = "https://www.walmart.ca/en/flyer?flyer_type=walmartcanada&store_code=3032"
OUT_PATH = Path("out/walmart_products.json")
DEBUG_SHOT = Path("out/debug_walmart.png")

PRODUCTS_RE = re.compile(r"dam\.flippenterprise\.net/.*/products\?.*display_type=all")

def capture_once() -> list:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()

        page.set_default_navigation_timeout(120_000)
        page.set_default_timeout(120_000)

        try:
            with page.expect_response(lambda r: bool(PRODUCTS_RE.search(r.url)), timeout=120_000) as resp_info:
                page.goto(STORE_URL, wait_until="domcontentloaded")

            resp = resp_info.value
            return resp.json()

        except Exception:
            OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            try:
                page.screenshot(path=str(DEBUG_SHOT), full_page=True)
            except Exception:
                pass
            raise

        finally:
            browser.close()

def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    last_err = None
    for attempt in range(1, 3):
        try:
            data = capture_once()
            OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[walmart] saved -> {OUT_PATH}")
            return
        except Exception as e:
            last_err = e
            print(f"[walmart] attempt {attempt} failed: {e}")

    raise RuntimeError(f"[walmart] failed after retries: {last_err}")

if __name__ == "__main__":
    main()
