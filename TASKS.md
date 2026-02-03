# TASKS — flyer-collector

This file is the execution plan for the project.
- ✅ = done
- 🔜 = next
- 🧪 = test/verify
- 🧊 = parked / later (V2+)

---

## Project goal (V1)
Automatically collect weekly flyer deal data (multi-store), normalize it, and produce a weekly “meal pack” output (JSON + PDF) that respects household constraints (preferences, appliances, cravings).

Current status: capture + normalize + release publishing is in-progress/working.

---

## V1 Milestones

### M0 — Data pipeline is reliable (capture → normalize → publish)
✅ **M0.1** Sobeys capture works in GitHub Actions (no networkidle hangs)
✅ **M0.2** Walmart capture uses Flipp (captcha-safe)
✅ **M0.3** Normalizer generates:
- `out/deals_sobeys.normalized.json`
- `out/deals_walmart.normalized.json`
- `out/deals_all.normalized.json`

🔜 **M0.4** Publish “latest” release assets every run:
- `deals_all.normalized.json` (primary)
- per-store normalized JSONs
- `flyer-data.zip`

🧪 **M0.5** Confirm stable URLs work (public repo):
- `https://github.com/<user>/<repo>/releases/latest/download/deals_all.normalized.json`
- `https://github.com/<user>/<repo>/releases/latest/download/flyer-data.zip`

🧪 **M0.6** Add a lightweight schema validation step (fail fast):
- Check required top-level keys exist
- Check `items` is a list
- Check each item has at least: `title`, `retailer`, `price.value OR promo_only`

---

## M1 — Planning bundle (deterministic pre-processing)
Goal: convert the big normalized deal pool into a small “planning bundle” that is safe for an LLM to use.

🔜 **M1.1** Define input files:
- `out/deals_all.normalized.json` (from pipeline)
- `prefs.json` (user constraints; committed, non-secret)
- `cravings.txt` (optional; committed)

🔜 **M1.2** Implement `planner/build_bundle.py`:
Outputs:
- `out/planning_bundle.json`

Bundle should include:
- “Usable items” filtered to likely-food categories
- A small list of “anchors” (cheap proteins, produce, staples)
- Price candidates per anchor
- A compact ingredient catalog with stable IDs

🧪 **M1.3** Validate bundle size:
- Keep it small enough to send to an LLM (avoid dumping thousands of items)
- Log counts and top anchors in CI output

---

## M2 — Meal-plan generation (LLM step, but validated)
Goal: generate 10–14 simple meals and a consolidated shopping list.

🔜 **M2.1** Decide how the LLM will run:
Option A: manual (you paste bundle into ChatGPT)
Option B: automated in CI (requires API key/secrets) 🧊 for later

For V1, start with Option A.

🔜 **M2.2** Add a prompt template:
- `planner/prompt_template.md`
- Must instruct model to reference ingredient IDs from the bundle (not free-form)

🔜 **M2.3** Add an output validator script:
- `planner/validate_mealplan.py`
Checks:
- All referenced ingredient IDs exist
- No banned ingredients (from `prefs.json`)
- No disallowed appliances required
- Per-meal ingredient lists are present
- Shopping list can be formed

Output:
- `out/mealplan.validated.json` (or fail with clear error messages)

🧪 **M2.4** Dry run:
- Use a captured week
- Generate a meal plan manually via ChatGPT using the prompt
- Validate and iterate until “mostly valid on first try”

---

## M3 — PDF rendering (static, deterministic)
Goal: take validated meal plan + selected deals and render a weekly PDF.

🔜 **M3.1** Define PDF contract (V1):
- 10 recipes (title, time estimate, steps)
- Ingredients list with:
  - cheapest store + price (from deal pool)
  - checkbox line per ingredient
- Keep layout simple; aesthetics later

🔜 **M3.2** Implement `render/render_pdf.py`:
Inputs:
- `out/mealplan.validated.json`
- `out/deals_all.normalized.json`
Outputs:
- `out/meal-pack.pdf`

🧪 **M3.3** Attach `meal-pack.pdf` to latest release assets.

---

## V1 Acceptance criteria (definition of done)
- Weekly workflow runs automatically.
- Latest release always contains:
  - `deals_all.normalized.json`
  - `flyer-data.zip`
  - `meal-pack.pdf`
- Meal pack includes:
  - ≥10 meals
  - ingredients + cheapest store/price
  - respects prefs (no disallowed foods; appliance constraints)

---

## V2+ Parking Lot (don’t start yet)
🧊 Multi-store “best basket” optimizer (split shopping across stores vs convenience mode)
🧊 Pantry integration (use-what-you-have; expiration-aware)
🧊 Nutrition targets (protein, calories, dietary patterns)
🧊 Auto “cravings inbox” (Google Form or mobile input)
🧊 Auto LLM in CI (API key + cost controls + retry/validation loop)
🧊 Add more stores (3–4) via config-driven collectors
🧊 Better categorization (food-only classifier / taxonomy mapping)
