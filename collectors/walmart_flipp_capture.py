import json
from pathlib import Path
from datetime import datetime, timezone

import requests

# Use a postal code near you (no space)
POSTAL_CODE = "E3C0B8"
LOCALE = "en-ca"

OUT_PATH = Path("out/walmart_products.json")

SEARCH_URL = "https://backflipp.wishabi.com/flipp/items/search"

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    params = {
        "locale": LOCALE,
        "postal_code": POSTAL_CODE,
        # Using merchant name as the query (common approach)
        "q": "walmart",
    }

    headers = {
        "User-Agent": UA,
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-CA,en;q=0.9",
    }

    r = requests.get(SEARCH_URL, params=params, headers=headers, timeout=60)
    r.raise_for_status()
    data = r.json()

    payload = {
        "source": "flipp_backflipp_items_search",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "request": {"url": r.url},
        "data": data,
    }

    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[walmart/flipp] saved -> {OUT_PATH}")

if __name__ == "__main__":
    main()
