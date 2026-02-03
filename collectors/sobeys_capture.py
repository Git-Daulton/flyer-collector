import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

STORE_URL = "https://www.sobeys.com/flyer?set_preferred_store_number=0849"
OUT_PATH = Path("out/sobeys_products.json")

# This matches the gold endpoint you found:
PRODUCTS_RE = re.compile(r"dam\.flippenterprise\.net/.*/products\?.*display_type=all")

def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    captured = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()

        def on_response(resp):
            if PRODUCTS_RE.search(resp.url):
                try:
                    captured["url"] = resp.url
                    captured["json"] = resp.json()
                except Exception:
                    pass

        page.on("response", on_response)
        page.goto(STORE_URL, wait_until="networkidle")

        if "json" not in captured:
            raise RuntimeError("Did not capture products feed. Site may have changed.")

        OUT_PATH.write_text(
            json.dumps(captured["json"], ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        print("Captured from:", captured.get("url"))
        print("Saved:", OUT_PATH)

        browser.close()

if __name__ == "__main__":
    main()
