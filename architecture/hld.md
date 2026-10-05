# HLD

Personal v1. Browser hits Health only. AI engine is private.

## Components

```text
Browser
  → Web (React + TypeScript)
  → Edge (static + /api)
       → Health service          public API
            → OCR
            → Postgres.app       jobs, results
            → AI engine          private
                 → LangGraph (agents 1–4)
                 → RAG retriever (inbuilt, LangChain)
                 → Postgres.knowledge
                 → Chroma (server)
                 → LLM (Ollama, local)
```

| Component | Public | Job |
| --- | --- | --- |
| Web | yes | UI |
| Health service | yes (API) | Ingest, OCR, flags, jobs, persist result. No LLM. |
| AI engine | no | LangGraph, retrieve, score. Only Health calls it. |
| Postgres | no | `app` + `knowledge` schemas. Master facts. |
| Chroma | no | Vector store for RAG chunks. Server mode (`chroma run` / Docker :8000). |
| LLM | no | Local model served by Ollama. No API key, no per-call cost. |
| Ingest | no | Download script + delta processing → Postgres tables + Chroma. See Knowledge base. |

RAG is **not** a separate service. Chroma is the store; the retriever is code inside the AI engine.

Chroma: **server mode**, not `PersistentClient`. Health / AI / ingest are multiple processes; embedded Chroma is not process-safe. Do not expose :8000 publicly.

## Knowledge base

Built and refreshed offline by the ingest job. Request flow only reads it.

```text
sources config → download → raw files + manifest → detect delta → extract → Postgres (tables) + Chroma (chunks) → run log
```

1. **Sources config** — one file listing each source: URL, kind (`file` or `listing`), check frequency.
2. **Download** — fetch into a local raw folder. Manifest records URL, download date, content hash.
3. **Delta**
   - `listing` (FSSAI gazette, advisories): diff links against last run; download only new ones.
   - `file` (IFCT, RDA, DGI, additives compendium): re-download, compare hash; process only if changed.
   - Missing from a listing: keep, mark `superseded`. Never hard-delete.
4. **Extract** — tables → Postgres; prose → chunks → Chroma. Every row/chunk keeps `source_url`, `doc_version`, `published_date`.
5. **Replace, don't duplicate** — changed file replaces its old rows and chunks.
6. **Run log** — per run: new / changed / skipped / failed.

Run manually in v1; schedule later. Public pages and PDFs only.

Each source names its store. Prose (DGI, FSSAI regulations) is chunked and embedded into Chroma. Tables and lists (food categories, additives, limits, IFCT, RDA) go to Postgres through one loader per source. Codes and numbers are never looked up through vector search.

## Request lifecycle

1. UI POST `/analyze` (text and/or image + medical flags) → Health.
2. Health stores job (`pending`), runs OCR if image, writes normalized text onto the job.
3. Health POST to AI engine `/run` with job payload (ingredients text, flags, job_id).
4. AI engine: normalize/alias → categorize → agents 1–3 parallel → composer → return structured result.
5. Health writes result (`done` / `failed`). UI GET `/jobs/{id}`.

- Pasted text, short list: Health may wait on AI (sync).
- Image / long list: return `job_id` immediately (async). Same AI contract either way.

## Agent boundaries (AI engine)

| Agent | Reads | Must not |
| --- | --- | --- |
| 1 Details | Postgres + Chroma | Invent INS / nutrients |
| 2 Impacts | Postgres + Chroma | Invent milligrams |
| 3 Score | Postgres `condition_rules` + flags + outputs of 1–2 | Call RAG for numbers |
| 4 Composer | 1–3 only | New retrieval |

## Auth / secrets (v1)

- No user accounts.
- Ollama and Chroma URLs: AI engine env only.
- Health → AI engine: shared internal token.
- Chroma bound to localhost / compose network.

## Out of scope here

OCR library, chunk sizes, table DDL, per-source extraction rules → LLD / data layer.
