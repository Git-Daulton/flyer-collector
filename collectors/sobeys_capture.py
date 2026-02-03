import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

STORE_URL = "https://www.sobeys.com/flyer?set_preferred_store_number=0849"
OUT_PATH = Path("out/sobeys_products.json")
DEBUG_SHOT = Path("out/debug_sobeys.png")

PRODUCTS_RE = re.compile(r"dam\.flippenterprise\.net/.*/products\?.*display_type=all")

def capture_once() -> list:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()

        page.set_default_navigation_timeout(120_000)
        page.set_default_timeout(120_000)

        try:
            # Wait for the specific JSON response we care about
            with page.expect_response(lambda r: bool(PRODUCTS_RE.search(r.url)), timeout=120_000) as resp_info:
                page.goto(STORE_URL, wait_until="domcontentloaded")

            resp = resp_info.value
            data = resp.json()
            return data

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
    for attempt in range(1, 3):  # simple retry
        try:
            data = capture_once()
            OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[sobeys] saved -> {OUT_PATH}")
            return
        except Exception as e:
            last_err = e
            print(f"[sobeys] attempt {attempt} failed: {e}")

    raise RuntimeError(f"[sobeys] failed after retries: {last_err}")

if __name__ == "__main__":
    main()
