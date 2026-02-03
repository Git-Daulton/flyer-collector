# PROJECT_NOTES — flyer-collector

## What this project does (one sentence)
A scheduled GitHub Actions pipeline that captures weekly grocery flyer deal data (currently Sobeys + Walmart), normalizes it into a consistent JSON format, and publishes the latest output as GitHub Release assets.

---

## High-level workflow
1) GitHub Actions runs on a schedule (weekly) or manually via workflow_dispatch.
2) Capturers fetch raw deal/product feed data per store:
   - Sobeys: automated capture (Playwright-based) from the Sobeys flyer site / feed calls.
   - Walmart: capture via Flipp endpoints to avoid “robot/human” captcha on walmart.ca.
3) `collectors/normalize.py` merges and standardizes raw feeds into uniform JSON:
   - store-specific normalized feeds
   - an “all stores combined” normalized feed
4) Outputs are saved to `out/` and then:
   - uploaded as a workflow artifact (short retention)
   - attached to a GitHub Release marked “latest” (long-lived + easy to fetch)

---

## Repository structure (important files)
- `.github/workflows/collect.yml`
  - Orchestrates install + capture + normalize + release publishing.
- `collectors/`
  - `sobeys_capture.py` — capture Sobeys feed JSON
  - `walmart_flipp_capture.py` — capture Walmart via Flipp (captcha-safe)
  - `normalize.py` — produces normalized output JSONs in `out/`
- `requirements.txt`
  - Python dependencies
- `out/` (generated)
  - Contains captured + normalized outputs (not hand-edited)

---

## Output files (the “products” of the pipeline)
These files are generated into `out/`:

- `out/deals_sobeys.normalized.json`
- `out/deals_walmart.normalized.json`
- `out/deals_all.normalized.json`
- `out/flyer-data.zip` (zip of `out/` contents)

> Releases: The workflow publishes these same files to the latest GitHub Release.

---

## Normalized JSON format (contract)
Each deal entry should be normalized to a consistent shape so downstream tools (recipe generator, shopping list, etc.) can treat all stores uniformly.

Typical fields:
- `store` (e.g. `"sobeys"`, `"walmart"`)
- `title` / `name`
- `price` (as a string or numeric + currency)
- `unit_price` (optional)
- `valid_from`, `valid_to` (optional; best effort)
- `category` (optional; best effort)
- `brand` (optional)
- `image_url` (optional)
- `source_url` (optional)
- `raw` (optional: original blob for debugging)

The goal is: **predictable keys, even if some values are missing**.

---

## Known pitfalls / gotchas
### 1) Walmart captcha (“Robot or human?”)
Direct walmart.ca automation can trigger a press-and-hold captcha in headless environments.
**Solution:** use Flipp/aggregated endpoints for Walmart capture (`walmart_flipp_capture.py`).

### 2) Sobeys timeouts in GitHub runners
Sometimes `page.goto(..., wait_until="networkidle")` can exceed timeout.
Mitigations:
- Use `wait_until="domcontentloaded"` then wait for a specific request/event.
- Increase Playwright timeout for the navigation step.
- Add retry logic around navigation/capture.

### 3) GitHub web editor “Commit changes” confusion
GitHub’s newer web editor sometimes disables commit until you use Source Control / add a commit message.
Using VS Code locally is the recommended workflow.

---

## How to run locally (developer workflow)
### Prereqs
- Git
- Python 3.11+
- (Optional) Playwright browser deps for Sobeys capture

### Setup
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python -m playwright install --with-deps chromium
