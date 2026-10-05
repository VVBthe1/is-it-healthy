# Architecture discussion plan

Discuss and decide in this order. Do not implement until the item is marked decided.

Status: `open` | `decided` | `blocked`

---

## 1. Knowledge strategy — decided

RDA is still useful. It is not the condition engine.

- [x] Four sources: IFCT 2017 (composition) + RDA/EAR 2020 (healthy-person EAR/RDA/TUL numbers) + DGI 2024 (disease-prevention language) + FSSAI (additives / INS).
- [x] RDA role: numeric ceilings/floors and TUL. Seed `condition_rules` thresholds. Compare when a quantity exists (IFCT per 100g, later nutrition panel). Do not use RDA to look up INS codes or diabetes/thyroid/cardiac advice.
- [x] Hybrid store: Postgres for facts; vector RAG for prose and citations.
- [x] DB is a derived cache of public sources. Every row keeps `source_url`, `doc_version`, `published_date`.
- [x] Score agent reads DB/rules; details agents may RAG. No invented milligrams.
- [x] V1 gaps: low BP (almost no ICMR protocol), thyroid (sparse), IFCT 2017 age.

---

## 2. HLD — overall architecture — decided

- [x] Components: Web, Health (public API), AI engine (private), Postgres, Chroma server, LLM.
- [x] RAG inbuilt in AI engine. Chroma is the vector *store*, not a RAG microservice. Server mode (not PersistentClient).
- [x] Postgres: `app` + `knowledge`. No pgvector for v1.
- [x] Lifecycle: Health owns OCR + jobs; AI engine owns the graph; UI polls `/jobs/{id}`. Sync OK for short text; async for image.
- [x] Agents 1–4 stay in AI engine (see `architecture/hld.md`).
- [x] Auth v1: none for users. LLM key + Health→AI token in env. Chroma not public.

Doc: `architecture/hld.md`

---

## 3. LLD — flows — open

Depends on 2.

Cover:

- [ ] End-to-end pipeline steps (ingest → OCR → normalize → categorize → agents → response).
- [ ] OCR: library, image types, language (Eng/Hindi), failure handling.
- [ ] Normalization / aliasing (INS, E-numbers, Hindi names).
- [ ] Categorization rules vs model.
- [ ] Per-agent inputs/outputs and graph edges.
- [ ] API contracts and error shapes.

---

## 4. Data layer — partly decided

Depends on 1 (and informs 2–3). The concrete “data stuff”:

- [x] Source list: `sources.yaml`, each source names its store (`chroma` / `postgres`).
- [ ] Ingest cadence (gazette poll, delta).
- [x] Knowledge tables (`knowledge` schema): `source_docs`, `food_categories` (tree), `additives`, `additive_limits`, `foods`, `nutrients`, `food_nutrients`, `nutrient_requirements`. Alembic migrations.
- [ ] Remaining schemas: `condition_rules`, ingredient aliases (Hindi names, E-numbers).
- [ ] Appendix A lists some limits per additive group ("BENZOATES" = INS 210–213): expand to members or add a groups table.
- [x] Chunking / embedding: 1,000 chars, 150 overlap, per page; local all-MiniLM-L6-v2; stable chunk ids replace on re-run.
- [ ] Provenance and citation format in the API.
- [x] Tables vs RAG: prose (DGI, FSSAI compendium, labelling) in Chroma; codes, limits, categories, IFCT, RDA in Postgres. Vector search can't match codes ("INS 621" returns unrelated rows) and splits limit tables from their headers.

---

## Build progress

| Area | State |
| --- | --- |
| Chroma: DGI 2024, FSSAI compendium, labelling (2,529 chunks) | Done |
| Postgres: schema + migrations | Done |
| Postgres: food categories (306 rows) | Done |
| Postgres loaders: additives, Appendix A limits, IFCT, RDA | Todo |
| FastAPI: health, categories | Done |
| FastAPI: `app` schema, jobs, `POST /analyses`, `GET /jobs/{id}`, tests | Done |
| FastAPI: JWT auth (register, token, me), jobs owned by users | Done |
| AI engine: LangGraph on local Ollama, citation checks, wired into jobs | Done |
| OCR POC: Tesseract service in Docker, `POST /ocr`, `POST /analyses/image`, Ollama compose profile | Done |
| OCR: vision-model fallback for curved or low-confidence photos, labelled photo test set | Todo |
| Frontend | Todo |

---

## Parking lot

- Certification mapping onto this graph (not a separate demo).
- Score threshold for `is_healthy` (currently default ≥ 60).
- Clinician review of condition rules (later).
