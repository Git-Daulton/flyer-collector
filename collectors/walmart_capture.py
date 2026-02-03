import json
import re
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

STORE_URL = "https://www.walmart.ca/en/flyer?flyer_type=walmartcanada&store_code=3032"
OUT_PATH = Path("out/walmart_products.json")
DEBUG_SHOT = Path("out/debug_walmart.png")
DEBUG_TXT = Path("out/debug_walmart_response.txt")

PRODUCTS_RE = re.compile(r"dam\.flippenterprise\.net/.*/products\?.*display_type=all")

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

def find_products_url() -> str:
    """Use Playwright only to observe the products feed request URL."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=UA,
            locale="en-CA",
            extra_http_headers={"Accept-Language": "en-CA,en;q=0.9"},
            viewport={"width": 1280, "height": 720},
        )
        page = ctx.new_page()
        page.set_default_timeout(120_000)
        page.set_default_navigation_timeout(120_000)

        seen = {"url": None}

        def on_request(req):
            if PRODUCTS_RE.search(req.url):
                seen["url"] = req.url

        page.on("request", on_request)

        try:
            page.goto(STORE_URL, wait_until="domcontentloaded")

            # Give it a moment to fire XHRs
            page.wait_for_timeout(5000)

            # If it didn’t fire yet, a tiny scroll often triggers the feed
            if not seen["url"]:
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(4000)

            if not seen["url"]:
                raise RuntimeError("Did not observe Walmart products feed request URL.")
            return seen["url"]

        finally:
            OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            try:
                page.screenshot(path=str(DEBUG_SHOT), full_page=True)
            except Exception:
                pass
            browser.close()

def fetch_json(products_url: str):
    """Fetch the observed URL with browser-like headers."""
    headers = {
        "User-Agent": UA,
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-CA,en;q=0.9",
        "Referer": STORE_URL,
        "Origin": "https://www.walmart.ca",
    }

    r = requests.get(products_url, headers=headers, timeout=60)

    # Save debug info either way
    DEBUG_TXT.write_text(
        f"GET {products_url}\n\nStatus: {r.status_code}\n"
        f"Content-Type: {r.headers.get('content-type','')}\n\n"
        f"{r.text[:4000]}\n",
        encoding="utf-8",
    )

    r.raise_for_status()

    # Some endpoints return JSON even with odd content-type
    text = r.text.lstrip()
    if text.startswith("{") or text.startswith("["):
        return r.json()

    raise RuntimeError("Response did not look like JSON (see debug_walmart_response.txt).")

def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    last_err = None
    for attempt in range(1, 4):
        try:
            url = find_products_url()
            data = fetch_json(url)
            OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[walmart] saved -> {OUT_PATH}")
            return
        except Exception as e:
            last_err = e
            print(f"[walmart] attempt {attempt} failed: {e}")

    raise RuntimeError(f"[walmart] failed after retries: {last_err}")

if __name__ == "__main__":
    main()
