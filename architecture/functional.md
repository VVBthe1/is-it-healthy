# Functional requirements

## Goal

Given an ingredients list (text or image) and optional medical flags, return whether the item is healthy for that person, which ingredients are unsafe and why, and what each ingredient does.

Not medical advice. Output is informational.

## Inputs

| Input | Required | Notes |
| --- | --- | --- |
| Ingredients text | One of text or image | Paste / typed list. |
| Ingredients image | One of text or image | Label / handwritten / screenshot. OCR → text. |
| Diabetes | Optional | Boolean. |
| High BP | Optional | Boolean. |
| Low BP | Optional | Boolean. |
| Thyroid | Optional | Boolean. |
| Heart surgery history | Optional | Boolean. |

If both text and image are sent, use image OCR then merge with provided text. Flag conflicts.

## Pipeline

1. **Ingest** — accept text and/or image.
2. **OCR** (image only) — extract ingredient text.
3. **Normalize** — split, clean, alias (e.g. E-numbers / INS codes, Hindi/English names).
4. **Categorize** — assign each ingredient to a category (see below).
5. **Fan-out agents** (LangGraph) — run 1–3 in parallel; 4 after they finish.
6. **Respond** — structured JSON + UI-ready payload.

## Ingredient categories

Use FSSAI / Indian Food Code style buckets:

- Cereals & grains
- Pulses & legumes
- Dairy
- Oils & fats
- Sweeteners
- Salt / sodium
- Spices & condiments
- Fruits & vegetables
- Nuts & seeds
- Meat / egg / fish
- Additives: colours, preservatives, emulsifiers, stabilizers, flavour enhancers, antioxidants, acidity regulators, others
- Unknown (must still appear in the response)

## Agents

| # | Agent | Job |
| --- | --- | --- |
| 1 | Ingredient details | Identity, INS/E-number, category, typical use. Postgres facts + RAG prose. |
| 2 | Ingredient impacts | General health effects (sodium, sugar, trans fat, additives, allergens). Postgres + RAG. |
| 3 | Health score | Score 0–100 from DB/`condition_rules` + medical flags. No RAG for numbers. Cite which flags moved the score. |
| 4 | Response composer | Build the user-facing result from 1–3. No new research. |

## Output (required fields)

- `is_healthy`: boolean (threshold TBD; default score ≥ 60 and no high-severity unsafe items).
- `health_score`: 0–100.
- `medical_flags_applied`: list of flags used.
- `unsafe_ingredients[]`: name, category, reason, severity (`low` / `medium` / `high`), related medical condition(s) if any, source citation.
- `ingredient_details[]`: name, category, what it does, notable effects.
- `unknown_ingredients[]`: names OCR/parser could not resolve.
- `disclaimer`: not a diagnosis / not medical advice.

## Rules

- No medical flags → general population scoring only.
- High BP and low BP together → warn; do not invent a combined recommendation.
- Unknown ingredients must not be silently dropped.
- Every unsafe claim and score movement must cite a `source_id` (DB row and/or RAG chunk).
- Prefer India sources (FSSAI, ICMR-NIN) over generic web.
- If a number is not in Postgres, return unknown. Do not invent milligrams.

## Stack (constraints)

- Frontend: React + TypeScript.
- Backend: FastAPI (Python).
- Orchestration: LangGraph + LangChain.
- Knowledge: hybrid — Postgres (facts) + Chroma (RAG prose). DB is a derived cache of public sources.
- Learning target: LangGraph / LangChain certification work should map onto this graph, not a separate demo.

## Knowledge — India-first sources

FSSAI has **no public ingredient REST API**. Licensing Excel dumps are not useful. Ingest documents into two sinks: tables (Postgres) and prose (vector store).

### Who does what

| Source | Role | Not for |
| --- | --- | --- |
| IFCT 2017 | What’s *in* the food (Na, sugar, fat per 100g). | Live updates; additive identity. |
| RDA/EAR 2020 (updated 2023) | Healthy-person targets: EAR, RDA, TUL. Seed numeric thresholds. Compare when a quantity exists. | INS lookup; diabetes / thyroid / cardiac advice. |
| DGI 2024 | Disease-prevention language (salt, sugar, oil, ultra-processed). Closest to “is this healthy.” | Milligram tables. |
| FSSAI | INS/E-numbers, permitted additives, category limits, trans-fat rules. | Clinical diet advice. |

RDA is kept. DGI 2024 still cites Nutrient Requirements 2020. Without RDA/TUL you have no Indian number for “too much”; without DGI/FSSAI you cannot score conditions or additives.

V1 ingredient lists often have **no grams**. Then: flag presence via `condition_rules` (seeded from RDA/DGI); use IFCT per-100g only as context; do not pretend a full RDA comparison. Nutrition-panel comparison is a later input.

### Primary (ingest)

| Source | URL | Why | Update pattern |
| --- | --- | --- | --- |
| FSSAI regulations index | https://fssai.gov.in/cms/food-safety-and-standards-regulations.php | Master list of current regulations. | Page + linked PDFs change when gazette drops. |
| FSS (Food Products Standards and Food Additives) compendium | https://fssai.gov.in/cms/Compendium-FSS-FPS-FA.php | Permitted additives, INS, category limits (Appendix A). | Versioned PDF; superseded by gazette. |
| FSSAI gazette notifications | https://fssai.gov.in/notifications.php?notification=gazette-notification | Amendments — the actually updating feed. | New PDFs; poll HTML listing. |
| FSSAI advisories / orders | https://fssai.gov.in/advisories.php | Operational clarifications. | Poll listing. |
| FoSCoS standardized products | https://foscos.fssai.gov.in/standard-product | Named Indian products + categories. | HTML catalog. |
| Food product categories (FoSCoS) | https://foscos.fssai.gov.in/assets/docs/Compiled%20FPC_FoSCoS.pdf | Category taxonomy. | Occasional PDF. |
| FSSAI Common Digital Dashboard | https://cdd.fssai.gov.in/ | Rules, notifications, guidelines in one catalog. | HTML. |
| ICMR-NIN IFCT 2017 | https://www.nin.res.in/ebooks/IFCT2017.pdf | Nutrient composition of Indian foods. | Static book. Extract: https://github.com/ifct2017/ifct2017 |
| ICMR-NIN RDA/EAR 2020 | https://www.nin.res.in/downloads/ | EAR / RDA / TUL numbers. | New PDF when ICMR revises. |
| Dietary Guidelines for Indians 2024 | https://nin.res.in/dietaryguidelines/pdfjs/locale/DGI_2024.pdf | Condition-adjacent dietary guidance. | New edition when ICMR revises. |

### Pipeline

1. Seed: FSSAI compendiums + IFCT + RDA/EAR + DGI 2024.
2. Poll gazette + advisories; fetch new PDFs by URL/hash.
3. Parse PDF/HTML → **tables → Postgres**, **prose → embed**. Every record: `source_url`, `published_date`, `doc_version`.
4. Replace by `source_url` so old gazette text does not linger.
5. Do **not** scrape FoSCoS behind login. Public pages/PDFs only.

### Gaps (do not fake)

- No official live FSSAI additive lookup API.
- IFCT 2017 is the national composition table; it is not continuously updated. Still use it.
- Low BP: almost no ICMR protocol. Conservative / unknown, do not invent.
- Thyroid: sparse in these sources. Explicit rules later, not retrieval.
- FSSAI = allowed in food. Condition scoring = DGI + encoded rules (clinician review later), with RDA/TUL as numeric rails.
