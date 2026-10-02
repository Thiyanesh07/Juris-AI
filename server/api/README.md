# LegalGraph AI — API Service

FastAPI backend for the LegalGraph AI platform. This slice (S01) establishes the
project foundation only: dependency management, application entry point, and a
single liveness endpoint. No databases, AI models, or business logic are wired
up yet.

## Stack

- Python 3.12, managed with [uv](https://docs.astral.sh/uv/)
- FastAPI + Pydantic v2 + Uvicorn
- SQLAlchemy 2.x (async) + asyncpg + Alembic on PostgreSQL (G01)
- pytest, Ruff (format + lint), mypy (strict) as dev tooling

## Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/) — uv resolves the
  pinned Python 3.12 interpreter automatically (see `.python-version`).
- Docker for the local PostgreSQL instance (see below).

## Local PostgreSQL

From the repository root:

```bash
docker compose --env-file .env.example --profile infra up -d postgres
```

This starts PostgreSQL 16 on `127.0.0.1:5434` with the credentials from
`.env.example` (database `legalgraph`, user `legalgraph`). Configuration is
environment-driven: the backend reads `DATABASE_URL`
(`postgresql+asyncpg://...`), plus optional `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`,
`DB_POOL_RECYCLE_SECONDS`, `DB_ECHO`. There are no hard-coded credentials.

## Commands

Run from `server/api/`:

```bash
# Create .venv, install dependencies, and generate uv.lock
uv sync

# Run tests (uses an isolated legalgraph_test database; requires Docker PostgreSQL)
uv run pytest

# Format, lint, and type-check
uv run ruff format .
uv run ruff check .
uv run mypy

# Start the API (http://127.0.0.1:8000)
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Endpoints

| Method | Path               | Purpose                                                     |
| ------ | ------------------ | ----------------------------------------------------------- |
| GET    | `/health`          | Liveness + component overview (database status included).   |
| GET    | `/health/database` | Database connectivity check (200 when reachable, 503 else). |

`GET /health` is always HTTP 200 while the process is up; it reports
`status: "degraded"` and `components.database.status: "unreachable"` when
PostgreSQL cannot be reached. The database check is a lightweight `SELECT 1`.

## Phase 1 dense retrieval

G03 preserves PDFs, extracted pages and hierarchy-aware JSONL chunks. G04 uses
the configurable `EMBEDDING_MODEL_NAME` (default `law-ai/InLegalBERT`) as an
encoder: final hidden states are mean-pooled with the attention mask, then
L2-normalized. FAISS `IndexFlatIP` therefore returns cosine-similarity scores.
Index artifacts live in `data/indexes/<VECTOR_INDEX_NAME>/` as `index.faiss`,
`embeddings.npy`, and `metadata.json`; metadata keeps the deterministic FAISS
row-to-chunk mapping and citation-ready source fields.

An administrator builds the corpus index with `POST /retrieval/rebuild` (HTTP
200 when complete) or:

```bash
uv run python -m app.cli rebuild-index
uv run python -m app.cli query "equality before law" --top-k 3
```

## Phase 4 knowledge graph population

After ingestion leaves documents in `READY`, graph population is a separate
operation. It reads chunk text from PostgreSQL, runs deterministic entity and
relation extraction (no LLMs, no FAISS), and writes provenance-linked nodes and
relationships to Neo4j in one transaction per document.

Neo4j stores `Document` and `Chunk` metadata (not chunk text), shared legal
entities (`Article`, `Section`, `Act`, `Court`, `Concept`), `CONTAINS`,
`SUPPORTED_BY`, and `DEFINES` relationships with deterministic `provenance_key`
values. Re-running `populate-graph` for a document replaces that document's
subgraph and removes orphaned entities that are no longer supported.

```bash
# Populate all READY documents
uv run python -m app.cli populate-graph

# Limit corpus, target one document, or rebuild the full graph after ID rule changes
uv run python -m app.cli populate-graph --limit 2
uv run python -m app.cli populate-graph --document-id <UUID>
uv run python -m app.cli populate-graph --clear

# Inspect Neo4j connectivity and counts
uv run python -m app.cli graph-stats
```

Graph failures mark `GRAPH_POPULATION` jobs as `failed` but leave documents
`READY`. Extraction stages (`ENTITY_EXTRACTION`, `RELATION_EXTRACTION`) are
marked completed before the Neo4j write; a failed write does not roll them back.
The command exits with a non-zero status when any document fails, while still
processing the rest of the corpus.

Authenticated clients use `POST /retrieval/search` with `{"query": "...",
"top_k": 5}`. This returns evidence only: it does not call an LLM or perform
graph traversal. Passages longer than 512 tokens are truncated at embed time.
Hugging Face downloads the configured checkpoint only when it is not already
cached and an embedding operation is requested.

## Phase 6 LLM legal QA + citations

Phase 6 answers authenticated legal questions by reusing Phase 5 hybrid retrieval,
formatting evidence for an OpenAI-compatible chat model, validating structured
citations, and returning grounded responses (no research-session persistence).

Configure the LLM in `.env` (see `.env.example`):

```text
LLM_PROVIDER=openai_compatible
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=your-key-here
LLM_BASE_URL=https://api.openai.com/v1
LLM_TIMEOUT_SECONDS=30
LLM_MAX_OUTPUT_TOKENS=800
QA_MAX_EVIDENCE=5
QA_MAX_CONTEXT_CHARS=12000
QA_MAX_CHUNK_CHARS=4000
```

`POST /qa/ask` (authenticated) accepts `{"query": "...", "top_k": 5}`. Effective
retrieval depth is capped server-side by `QA_MAX_EVIDENCE`. The service calls
`hybrid_retrieve` directly (not the HTTP retrieval route). When hybrid retrieval
returns no evidence, the API responds HTTP 200 with `status: "insufficient_evidence"`
and does not call the LLM. Neo4j fallback (`fallback: "dense_only"`) still allows
LLM generation when dense evidence exists.

Example response (abbreviated):

```json
{
  "query": "What does Article 14 guarantee?",
  "status": "answered",
  "answer": "Equality before the law is guaranteed [1].",
  "insufficient_evidence": false,
  "citations": [{ "marker": 1, "evidence_rank": 1, "citation_ref": "Article 14" }],
  "evidence": [],
  "retrieval": { "mode": "hybrid", "evidence_count": 1 },
  "llm_called": true,
  "disclaimer": "Informational research aid. Not legal advice."
}
```

Failure behavior (no secrets or raw provider payloads in errors):

| Condition | HTTP |
| --- | ---: |
| Invalid request | 422 |
| Unauthenticated | 401 |
| Missing LLM API key / provider misconfiguration | 503 |
| Retrieval failure (embedding/index/PostgreSQL) | 503 |
| LLM timeout | 504 |
| Provider unavailable | 503 |
| Invalid model output after one retry | 502 |
| Empty retrieval | 200 |

CLI (same service layer as the API):

```bash
uv run python -m app.cli qa "What is Article 14?" --top-k 3
```

This is an academic research aid and **not legal advice**; answers are grounded
only on retrieved evidence and validated citations, not guaranteed to be legally
complete or correct.

## Database schema & migrations

SQLAlchemy 2.x models in `app/models/` are the single schema source; Alembic
(`alembic/`) tracks schema history and connects to the same `DATABASE_URL`
(`alembic/env.py` imports the application settings and `Base.metadata`).

Run from `server/api/`:

```bash
# Apply all migrations to the configured database
uv run alembic upgrade head

# Roll back one revision (or use "base" to roll back everything)
uv run alembic downgrade -1

# Generate a new migration after changing the models (review before applying!)
uv run alembic revision --autogenerate -m "describe the change"
```

Conventions:

- All tables use UUID primary keys (`uuid4`).
- Timestamps are timezone-aware `timestamptz` in UTC (`created_at` on every
  entity; `updated_at` only where rows change). Calendar date ranges
  (`DocumentVersion`) use plain `date` columns.
- Enums are native PostgreSQL enum types (`user_role`, `document_type`,
  `document_status`, `processing_job_stage`, `processing_job_status`,
  `validation_status`).
- Deletes: user removal cascades to their research data; document removal is
  RESTRICTed while citations reference it, and cascades to versions/jobs;
  audit events survive user removal (`actor_id` SET NULL).

## Authentication setup (G02)

The backend owns the Google OAuth authorization-code flow and stores only a
signed, HTTP-only browser session cookie. Create a **Web application** OAuth
client in Google Cloud Console and add `GOOGLE_REDIRECT_URI` (for local use with
the Vite dev proxy: `http://localhost:5173/auth/google/callback`) as an
authorized redirect URI.
Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, and a
long random `SESSION_SECRET` in a local `.env`; never expose these values to
Vite. Keep `SESSION_COOKIE_SECURE=false` locally and set it to `true` behind
HTTPS in production.

The frontend calls `/auth/me` with cookies and starts login through
`/auth/google/login`. New identities receive `USER`; existing roles are never
changed during login. To promote a local user, use an authenticated database
administration session (not a public API), for example:
`UPDATE users SET role = 'admin' WHERE email = 'you@example.com';`.

## Layout

```
server/api/
├── alembic/             # migration environment + versions
├── alembic.ini
├── app/
│   ├── main.py          # FastAPI app; includes the health router
│   ├── api/routes/      # HTTP routers (health)
│   ├── core/config.py   # environment-driven Settings (pydantic-settings)
│   ├── db/              # Base/mixins, async engine/session, SELECT 1 ping
│   ├── models/          # SQLAlchemy 2.x application models + enums
│   ├── schemas/         # Pydantic v2 schemas (reserved)
│   ├── services/        # application service layer (reserved)
│   ├── repositories/    # PostgreSQL data access (reserved)
│   ├── graph/           # Neo4j client, extraction, population
│   ├── retrieval/       # FAISS dense/hybrid retrieval
│   ├── qa/              # LLM legal QA + citation validation (Phase 6)
│   ├── rag/             # multi-hop reasoning, LangGraph (reserved)
│   ├── ingestion/       # legal corpus ingestion (reserved)
│   └── evaluation/      # benchmarks & metrics (reserved)
├── tests/               # health + PostgreSQL integration + migration tests
├── pyproject.toml
└── .python-version
```

The `reserved` packages are intentionally empty; they document the target
architecture and will be filled in slice by slice.
