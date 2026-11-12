# Is it healthy?

Checks packaged-food ingredient lists (pasted text or a label photo) against India-specific public sources (FSSAI, ICMR-NIN), with optional health flags (diabetes, BP, thyroid, cardiac history). Output is informational, not medical advice.

Stack: React + TypeScript, FastAPI, LangGraph / LangChain, PostgreSQL, Chroma.

Design docs live in `architecture/`: `functional.md` (what it does), `hld.md` (components), `plan.md` (design topics and progress).

The knowledge base has two stores, filled from public PDFs by one command:

- **Chroma**: prose, split into chunks, for questions in words ("salt intake per day").
- **Postgres**: tables, for exact lookups (a food category, an INS code, a limit).

## Layout

```text
src/
  ai_engine/
    requirements.txt
    knowledge_base/
      sources.yaml        list of sources to ingest
      config.py           paths, Chroma host/port, chunk size, embedding model
      models.py           SourceConfig, Page, Chunk
      sources/            one class per source type (PdfSource), plus the factory
      chroma_store.py     Chroma connection, upsert, query
      loaders/            one Postgres loader per source (parse rows, upsert)
      db/                 SQLAlchemy engine and session
      run.py              entry point
    agents/               LangGraph analysis pipeline (local LLM through Ollama)
      config.py           Ollama URL, model, temperature, retrieval top-k
      schemas.py          graph state and the structured outputs of each chain
      prompts.py          prompt templates
      llm.py              chat model
      retrieval.py        Chroma lookup and context formatting for prompts
      chains.py           prompt | model, one chain per LLM step
      nodes.py            graph nodes
      graph.py            graph wiring, run()
      run.py              command-line entry point
    migrations/           Alembic migrations for the `knowledge` schema
    alembic.ini
  backend/                Health API (FastAPI)
    main.py               app, /health
    routers/              auth, categories, jobs, images
    schemas.py            request and response models
    security.py           password hashing, JWT, current user
    analysis.py           background analysis run
    ocr.py                upload checks, call to the OCR service
    migrations/           Alembic migrations for the `app` schema
    alembic.ini
    tests/                pytest, against the test database
  ocr/                    OCR service (FastAPI + Tesseract), runs in Docker
    main.py               POST /ocr
    reader.py             image clean-up, Tesseract
    extract.py            cuts the ingredients section out of the text
  shared/db/
    models.py             `knowledge` schema tables, used by both services
    app_models.py         `app` schema tables (users, jobs)
  data/knowledge/
    raw/                  downloaded PDFs (git-ignored)
    chroma/               Chroma data (git-ignored)
architecture/             design docs
docker-compose.yml        Postgres, Chroma, OCR, Ollama (optional)
```

## Setup

Run everything from the repo root.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r src/ai_engine/requirements.txt -r src/backend/requirements.txt
cp .env.example .env      # then set a password in .env
```

`.env` holds the Postgres credentials, `DATABASE_URL`, `TEST_DATABASE_URL`, `JWT_SECRET`, and the Ollama and OCR settings. It is git-ignored; both services, the tests and `docker compose` read it.

## Knowledge base

### 1. Start Postgres, Chroma, and OCR

```bash
docker compose up -d
alembic -c src/ai_engine/alembic.ini upgrade head
alembic -c src/backend/alembic.ini upgrade head
```

Chroma is on port 8000 and keeps data under `src/data/knowledge/chroma` (same folder as before). Check it's up:

```bash
curl http://localhost:8000/api/v2/heartbeat
```

### 2. Build

```bash
python -m src.ai_engine.knowledge_base.run                                  # all enabled sources
python -m src.ai_engine.knowledge_base.run --only dgi_2024                  # one source
python -m src.ai_engine.knowledge_base.run --only dgi_2024 --fresh          # force re-download
python -m src.ai_engine.knowledge_base.run --only dgi_2024 --skip-download  # use the PDF already in raw/
```

A PDF already in `raw/` is not downloaded again. `--fresh` and `--skip-download` can't be combined.

Each source goes to the store named in `sources.yaml`. Example output:

```text
== dgi_2024: Dietary Guidelines for Indians 2024
Empty pages: 4, Source: dgi_2024
   pages=144 chunks=414 stored=414

== fssai_food_categories: Food Product Categories used for Licensing/Registration
   rows=306
```

- `pages`: pages with text (image-only pages are skipped and counted as empty).
- `chunks`: pieces the pages were split into.
- `stored`: chunks written to Chroma. Lower than `chunks` means a batch failed; the error is printed above.
- `rows`: rows upserted into Postgres.

The first build downloads the embedding model (~80 MB) to `~/.cache/chroma/`. Re-running a build is safe: Chroma chunks and Postgres rows are overwritten, not duplicated.

### 3. Query Chroma

```bash
python -m src.ai_engine.knowledge_base.run --query "salt intake per day"
python -m src.ai_engine.knowledge_base.run --query "allergen declaration on label"
```

Returns the five closest chunks with their source and page. Example (text shortened):

```text
{'text': 'High intake of salt is associated with high blood pressure ...', 'source_id': 'dgi_2024', 'page_number': 90, 'distance': 0.690}
{'text': '... not more than 5g of salt per day (equivalent to 2g of sodium) ...', 'source_id': 'dgi_2024', 'page_number': 90, 'distance': 0.691}
{'text': '... The current Indian as well as WHO recommendation for sodium intake is 2300mg per day ...', 'source_id': 'dgi_2024', 'page_number': 91, 'distance': 0.704}
{'text': 'POINTS TO REGISTER · Use iodized salt · Restrict the intake of added salt ... maximum of 5g per day ...', 'source_id': 'dgi_2024', 'page_number': 93, 'distance': 0.763}
{'text': '... Prevalence of hypertension is low in populations consuming less than 3g salt per day ...', 'source_id': 'dgi_2024', 'page_number': 91, 'distance': 0.791}
```

`distance`: lower is closer. Use it to rank results, not as a confidence score.

### 4. Query Postgres

```bash
docker compose exec postgres psql -U healthy -d healthy
```

```sql
-- top-level food categories
select code, name from knowledge.food_categories where parent_code is null
order by string_to_array(code, '.')::int[];

-- children of one category
select code, name from knowledge.food_categories where parent_code = '14.1';

-- path from a category up to the top
with recursive path as (
    select code, name, parent_code from knowledge.food_categories where code = '14.1.4.1'
    union all
    select c.code, c.name, c.parent_code
    from knowledge.food_categories c join path p on c.code = p.parent_code
)
select * from path;
```

Category codes are written without leading zeros (`1.1.2`), the same as FSSAI Appendix A.

### 5. Remove a source from Chroma

Disabling a source in `sources.yaml` stops future builds; chunks already stored stay until deleted:

```bash
python -c "import chromadb; c = chromadb.HttpClient(host='localhost', port=8000).get_collection('knowledge_v1'); c.delete(where={'source_id': 'ifct_2017'}); print(c.count())"
```

Prints the chunk count left in the collection.

## Analysis pipeline

Runs on a local model through [Ollama](https://ollama.com); no API key or per-call cost.

### 1. Start Ollama

```bash
brew install ollama
ollama serve              # in its own terminal, or run the Ollama app
ollama pull qwen2.5:7b    # ~4.7 GB, once
```

The model is set by `OLLAMA_MODEL` in `.env`. `qwen2.5:14b` gives better answers and is slower.

Or run Ollama in Docker (CPU only on macOS, so several times slower; use it on Linux or GPU hosts):

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull qwen2.5:7b
```

### 2. Run

Needs Chroma (see Knowledge base) and Ollama running.

```bash
python -m src.ai_engine.agents.run "Ingredients: Wheat flour (Maida), Sugar, Edible vegetable oil (Palm oil), Salt, Preservative (INS 211)"
```

Prints the result as JSON: `health_score`, `is_healthy`, `unsafe_ingredients`, `ingredient_details`, `unknown_ingredients`, each claim with its `source_id` and page.

### How the graph works

```text
START → normalize → categorize → details ─┐
                               → impacts ─┴→ score → compose → END
```

- `normalize`: splits and cleans the list, reads INS/E-numbers. No LLM.
- `categorize`: one LLM call assigns each ingredient a category and a plain search name (INS 211 → sodium benzoate); anything unclear is `unknown`.
- `details` and `impacts` run in parallel. Each retrieves excerpts from Chroma per ingredient and asks the model to answer from those excerpts only, with citations. Citations not in the retrieved excerpts are dropped; an impact left without one is set to `none`.
- `score`: starts at 100 and subtracts a fixed penalty per severity. No LLM.
- `compose`: assembles the response and the disclaimer. No LLM.

Every LLM step returns structured output validated against a Pydantic model (`schemas.py`).

### Tests

```bash
python -m pytest src/ai_engine/agents/tests
```

Cover the steps that don't use the LLM: parsing, citation checks, scoring and composing.

## OCR

Reads an ingredients list from a label photo. Runs in Docker with Tesseract; started by `docker compose up -d`, on port 8002.

```bash
curl localhost:8002/health
curl -F file=@label.jpg localhost:8002/ocr
```

Returns the full `text`, the `ingredients` section (from "Ingredients:" to the next section such as Nutrition or Allergen) and a mean word `confidence` from 0 to 100.

Works on flat, well-lit label photos. Curved or crumpled packs give low confidence; the API rejects those below 70 and asks for a retake or typed text.

```bash
python -m pytest src/ocr/tests
```

## Health API

```bash
uvicorn src.backend.main:app --reload --port 8001
```

Docs at http://localhost:8001/docs. Port 8000 is Chroma. Analyses need Chroma and Ollama running (see Analysis pipeline) and take about a minute; poll the job until it is `done` or `failed`.

| Endpoint | What |
| --- | --- |
| `GET /health` | API and database are up |
| `POST /auth/register` | Create a user (email, password of 8+ characters) |
| `POST /auth/token` | Log in (form fields `username` = email, `password`); returns a bearer token valid for 30 minutes |
| `GET /auth/me` | The logged-in user. Needs a token |
| `GET /categories?search=milk&limit=50` | Food categories, ordered by code; `limit` 1–200 |
| `GET /categories/{code}` | One category with its parent and children |
| `POST /analyses` | Queue an analysis of an ingredient list; returns `202` and a `job_id`. Needs a token |
| `POST /ocr` | Upload a label photo (JPEG, PNG or WebP, up to 10 MB); returns the extracted text to review. Needs a token |
| `POST /analyses/image` | Upload a label photo and queue an analysis of its ingredients; returns `202`, the `job_id` and the text used. Needs a token |
| `GET /jobs/{job_id}` | Job status (`queued`, `running`, `done`, `failed`) and result. Needs a token; only the owner sees a job |

```bash
curl -X POST localhost:8001/auth/register -H 'Content-Type: application/json' -d '{"email": "asha@example.com", "password": "correct-horse-battery"}'
TOKEN=$(curl -s -X POST localhost:8001/auth/token -d 'username=asha@example.com&password=correct-horse-battery' | python -c 'import sys, json; print(json.load(sys.stdin)["access_token"])')
curl -X POST localhost:8001/analyses -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"ingredients": "sugar, salt, INS 211"}'
curl -X POST localhost:8001/analyses/image -H "Authorization: Bearer $TOKEN" -F file=@label.jpg
curl localhost:8001/jobs/<job_id> -H "Authorization: Bearer $TOKEN"
```

In `/docs`, use **Authorize** with the email and password to call protected endpoints.

Tokens are signed with `JWT_SECRET` from `.env`. Changing it logs everyone out.

### Tests

Tests run against a separate database, `healthy_test`, migrated to head at the start of each run. Create it once:

```bash
docker compose exec postgres psql -U healthy -d healthy -c 'create database healthy_test'
python -m pytest src/backend/tests
```

The analysis graph and the OCR service are replaced with stubs, so these tests don't need Ollama or Docker.

## Postgres

Two schemas, each with its own Alembic migrations:

- `knowledge`: `source_docs`, `food_categories`, `additives`, `additive_limits`, `foods`, `nutrients`, `food_nutrients`, `nutrient_requirements`. Every row links to `source_docs` for provenance. Models in `src/shared/db/models.py`, migrations in `src/ai_engine/migrations/`.
- `app`: `users`, `jobs` (each job belongs to a user). Models in `src/shared/db/app_models.py`, migrations in `src/backend/migrations/`.

List the tables:

```bash
docker compose exec postgres psql -U healthy -d healthy -c '\dt knowledge.*' -c '\dt app.*'
```

After changing a models file, generate and apply a migration with the matching config:

```bash
alembic -c src/ai_engine/alembic.ini revision --autogenerate -m "describe the change"   # knowledge
alembic -c src/backend/alembic.ini revision --autogenerate -m "describe the change"     # app
alembic -c src/ai_engine/alembic.ini upgrade head
alembic -c src/backend/alembic.ini upgrade head
```

Connection: `DATABASE_URL` in `.env` (required; there is no default).

## Sources

Defined in `src/ai_engine/knowledge_base/sources.yaml`.

| id | What | Store |
| --- | --- | --- |
| `dgi_2024` | ICMR-NIN Dietary Guidelines for Indians 2024 | Chroma |
| `fssai_fps_fa_compendium` | FSSAI food products standards and additives, incl. Appendix A limits | Chroma |
| `fssai_labelling_2020` | FSSAI labelling and display regulations | Chroma |
| `fssai_food_categories` | FSSAI food product categories | Postgres (`food_categories`) |
| `rda_2020_brief` | ICMR-NIN RDA/EAR 2020, brief note (full report is paid) | Disabled: Postgres loader not written |
| `ifct_2017` | ICMR-NIN Indian Food Composition Tables 2017 | Disabled: Postgres loader not written |
| `fssai_substances_added` | FSSAI Chapter 3, substances added to food | Disabled: duplicates the compendium's additives chapter |
| `fssai_gazette` | FSSAI gazette notifications (listing) | Disabled: needs delta updates |
| `fssai_advisories` | FSSAI advisories and orders (listing) | Disabled: needs delta updates |

To add a source, append an entry with the same fields. `store` is `chroma` (default) or `postgres`; a `postgres` source also needs a loader registered in `loaders/__init__.py`. Unknown keys, a bad URL, or an unsupported `kind` fail when the file loads. Set `enabled: false` to skip one.

The IFCT PDF is encrypted; `cryptography` (in requirements) lets pypdf open it.

## How it works

- **Extract:** pypdf reads each page; whitespace is collapsed; page numbers are 1-based.
- **Chunk:** 1,000 characters with 150 overlap, per page (`config.py`). Ids are stable, `dgi_2024:p23:c1` = page 23, second chunk, so re-running a source overwrites its chunks instead of duplicating them.
- **Embed:** Chroma's default `all-MiniLM-L6-v2`, run locally, no API key. The model name is saved in the collection metadata. Vectors from different models can't be mixed, so a new model needs a new collection (`CHROMA_COLLECTION` in `config.py`).
- **Metadata per chunk:** `source_id`, `source_url`, `publisher`, `title`, `doc_version`, `page_number`.
- **Postgres loaders:** each `postgres` source has a loader that reads the PDF line by line, parses rows and upserts them (`INSERT ... ON CONFLICT DO UPDATE`). The source row and its data are saved in one transaction.

PDF extraction leaves some noise in chunks: figure labels and repeated page footers.

## Roadmap

- Postgres loaders for IFCT, RDA, additives and Appendix A limits.
- Delta updates: listing sources, skip unchanged files.
- AI engine (LangGraph agents), Health API, frontend.
