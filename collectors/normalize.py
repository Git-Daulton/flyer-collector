import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


OUT_DIR = Path("out")

# Input filenames expected from your collectors
SOBEYS_RAW = OUT_DIR / "sobeys_products.json"
WALMART_RAW = OUT_DIR / "walmart_products.json"

# Output filenames (normalized)
SOBEYS_NORM = OUT_DIR / "deals_sobeys.normalized.json"
WALMART_NORM = OUT_DIR / "deals_walmart.normalized.json"
ALL_NORM = OUT_DIR / "deals_all.normalized.json"

SCHEMA_VERSION = 1
CURRENCY = "CAD"


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _file_mtime_iso(path: Path) -> str:
    try:
        ts = os.path.getmtime(path)
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except Exception:
        return _now_utc_iso()


def _safe_str(x: Any) -> str:
    return "" if x is None else str(x)


def _parse_iso_datetime(s: Optional[str]) -> Optional[str]:
    """Pass through ISO-ish strings; return None if empty."""
    if not s:
        return None
    return str(s)


_float_re = re.compile(r"[-+]?\d+(?:\.\d+)?")

def _extract_float(s: Any) -> Optional[float]:
    """Extract first float-looking number from s."""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    txt = str(s)
    m = _float_re.search(txt.replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def _parse_multi_buy_qty(pre: Any) -> Optional[int]:
    """
    Detect patterns like:
      "2/"  or "2 /"  or "2/"
    You can extend this later for '2 for' etc.
    """
    if not pre:
        return None
    txt = str(pre).strip()
    m = re.match(r"^\s*(\d+)\s*/\s*$", txt)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None


def _normalize_unit(post: Any) -> str:
    """
    Normalize unit from post_price_text.
    Examples: "lb" -> "lb", "ea" -> "ea", "" -> "ea".
    """
    if not post:
        return "ea"
    u = str(post).strip().lower()
    if not u:
        return "ea"
    return u


def _build_price(pre: Any, price_text: Any, post: Any, numeric_override: Optional[float] = None) -> Dict[str, Any]:
    pre_s = _safe_str(pre).strip()
    post_s = _safe_str(post).strip()
    text_s = _safe_str(price_text).strip()

    value = numeric_override if numeric_override is not None else _extract_float(price_text)
    unit = _normalize_unit(post_s)

    multi_qty = _parse_multi_buy_qty(pre_s)
    unit_value = None
    if value is not None and multi_qty and multi_qty > 0:
        # Example: pre "2/" + price "4.50" means 2 for 4.50 => unit_value 2.25
        unit_value = round(value / multi_qty, 4)

    return {
        "currency": CURRENCY,
        "value": value,
        "unit": unit,
        "pre": pre_s if pre_s else "",
        "post": post_s if post_s else "",
        "text": text_s if text_s else "",
        "multi_buy_qty": multi_qty,
        "unit_value": unit_value,
    }


def _is_promo_only(price_obj: Dict[str, Any], sale_story: Any) -> bool:
    """
    Promo-only heuristic: no numeric price AND some sale_story text (e.g., points offers).
    """
    if price_obj.get("value") is None and _safe_str(sale_story).strip():
        return True
    return False


def _sobeys_categories(item: Dict[str, Any]) -> Dict[str, Any]:
    cats = item.get("item_categories") or {}
    out = {}
    for level in ("l1", "l2", "l3"):
        c = cats.get(level)
        if isinstance(c, dict) and c.get("category_name"):
            out[level] = {
                "name": c.get("category_name"),
                "google_id": c.get("google_category_id"),
            }
    return out


def normalize_sobeys(raw_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    captured_at = _file_mtime_iso(SOBEYS_RAW)

    items_norm: List[Dict[str, Any]] = []
    flyer_ranges: Dict[str, Tuple[Optional[str], Optional[str]]] = {}

    for it in raw_items:
        flyer_id = _safe_str(it.get("flyer_id"))
        valid_from = _parse_iso_datetime(it.get("valid_from_timestamp") or it.get("valid_from"))
        valid_to = _parse_iso_datetime(it.get("valid_to_timestamp") or it.get("valid_to"))

        # Track flyer validity window (min/max)
        if flyer_id:
            cur = flyer_ranges.get(flyer_id, (None, None))
            vf, vt = cur
            vf = vf or valid_from
            vt = vt or valid_to
            # crude min/max by string (ISO sorts OK if same tz style; good enough for our use)
            if valid_from and vf and valid_from < vf:
                vf = valid_from
            if valid_to and vt and valid_to > vt:
                vt = valid_to
            flyer_ranges[flyer_id] = (vf, vt)

        price = _build_price(it.get("pre_price_text"), it.get("price_text"), it.get("post_price_text"))
        promo_only = _is_promo_only(price, it.get("sale_story"))

        item_out = {
            "source_item_id": _safe_str(it.get("id")),
            "flyer_id": flyer_id,
            "title": _safe_str(it.get("name")).strip(),
            "brand": _safe_str(it.get("brand")).strip() or None,
            "description": _safe_str(it.get("description")).strip() or None,
            "price": price,
            "original_price": _extract_float(it.get("original_price")),
            "sale_story": _safe_str(it.get("sale_story")).strip() or None,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "categories": _sobeys_categories(it),
            "image_url": it.get("image_url") or (it.get("images")[0] if it.get("images") else None),
            "page": it.get("page"),
            "promo_only": promo_only,
        }
        items_norm.append(item_out)

    flyers = [
        {"flyer_id": fid, "valid_from": rng[0], "valid_to": rng[1]}
        for fid, rng in sorted(flyer_ranges.items(), key=lambda x: x[0])
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "retailer": "sobeys",
        "captured_at": captured_at,
        "flyers": flyers,
        "items": items_norm,
    }


def normalize_walmart(raw_wrapper: Dict[str, Any]) -> Dict[str, Any]:
    captured_at = _parse_iso_datetime(raw_wrapper.get("retrieved_at")) or _file_mtime_iso(WALMART_RAW)

    data = raw_wrapper.get("data") or {}
    raw_items = data.get("items") or []

    items_norm: List[Dict[str, Any]] = []
    flyer_ranges: Dict[str, Tuple[Optional[str], Optional[str]]] = {}

    for it in raw_items:
        # Only flyer items for Walmart
        if _safe_str(it.get("item_type")).lower() != "flyer":
            continue
        if _safe_str(it.get("merchant_name")).strip().lower() != "walmart":
            continue

        flyer_id = _safe_str(it.get("flyer_id"))
        valid_from = _parse_iso_datetime(it.get("valid_from"))
        valid_to = _parse_iso_datetime(it.get("valid_to"))

        if flyer_id:
            cur = flyer_ranges.get(flyer_id, (None, None))
            vf, vt = cur
            vf = vf or valid_from
            vt = vt or valid_to
            if valid_from and vf and valid_from < vf:
                vf = valid_from
            if valid_to and vt and valid_to > vt:
                vt = valid_to
            flyer_ranges[flyer_id] = (vf, vt)

        # Walmart already provides numeric current_price
        price = _build_price(it.get("pre_price_text"), it.get("current_price"), it.get("post_price_text"), numeric_override=_extract_float(it.get("current_price")))
        promo_only = _is_promo_only(price, it.get("sale_story"))

        categories = {}
        l1 = it.get("_L1")
        l2 = it.get("_L2")
        if l1:
            categories["l1"] = {"name": _safe_str(l1), "google_id": None}
        if l2:
            categories["l2"] = {"name": _safe_str(l2), "google_id": None}

        item_out = {
            "source_item_id": _safe_str(it.get("id") or it.get("flyer_item_id")),
            "flyer_id": flyer_id,
            "title": _safe_str(it.get("name")).strip(),
            "brand": None,  # Walmart payload doesn’t reliably include brand name here
            "description": None,
            "price": price,
            "original_price": _extract_float(it.get("original_price")),
            "sale_story": _safe_str(it.get("sale_story")).strip() or None,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "categories": categories,
            "image_url": it.get("clean_image_url") or it.get("clipping_image_url"),
            "page": None,  # not present in this dataset
            "promo_only": promo_only,
        }
        items_norm.append(item_out)

    flyers = [
        {"flyer_id": fid, "valid_from": rng[0], "valid_to": rng[1]}
        for fid, rng in sorted(flyer_ranges.items(), key=lambda x: x[0])
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "retailer": "walmart",
        "captured_at": captured_at,
        "flyers": flyers,
        "items": items_norm,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    outputs = []

    # Sobeys
    if SOBEYS_RAW.exists():
        raw = json.loads(SOBEYS_RAW.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise RuntimeError("sobeys_products.json expected to be a list of items.")
        sob_norm = normalize_sobeys(raw)
        SOBEYS_NORM.write_text(json.dumps(sob_norm, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append(sob_norm)
        print(f"[normalize] wrote {SOBEYS_NORM} ({len(sob_norm['items'])} items)")
    else:
        print("[normalize] sobeys_products.json not found; skipping")

    # Walmart
    if WALMART_RAW.exists():
        raw = json.loads(WALMART_RAW.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or "data" not in raw:
            raise RuntimeError("walmart_products.json expected to be an object with a 'data' field.")
        wal_norm = normalize_walmart(raw)
        WALMART_NORM.write_text(json.dumps(wal_norm, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append(wal_norm)
        print(f"[normalize] wrote {WALMART_NORM} ({len(wal_norm['items'])} items)")
    else:
        print("[normalize] walmart_products.json not found; skipping")

    # Merge pool
    merged_items = []
    merged_flyers = []
    for o in outputs:
        merged_items.extend([
            {**it, "retailer": o["retailer"]}
            for it in o.get("items", [])
        ])
        merged_flyers.extend([
            {**f, "retailer": o["retailer"]}
            for f in o.get("flyers", [])
        ])

    merged = {
        "schema_version": SCHEMA_VERSION,
        "captured_at": _now_utc_iso(),
        "sources": [o["retailer"] for o in outputs],
        "flyers": merged_flyers,
        "items": merged_items,
    }
    ALL_NORM.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[normalize] wrote {ALL_NORM} ({len(merged_items)} items total)")


if __name__ == "__main__":
    main()
