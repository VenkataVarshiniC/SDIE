# SDIE — Strategic Decision Intelligence Engine (scaffold)

Modular-monolith backend (Clean Architecture / DDD, one bounded context per
directory) + Next.js frontend. Four bounded contexts are fully working end
to end: **financial_modeling**, **decision_analysis**, **evidence_research**,
and **recommendation_synthesis**. `problem_framing` and `workspace` are
still empty directories, ready for the same layering.

## Backend

```
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
```

### Database — no Docker needed

The app only needs one thing running: Postgres. (Redis is in config for a
future async job queue but nothing calls it yet — ignore it for now.)

**Option A — hosted free Postgres (fastest, no install):**
[Neon](https://neon.tech) or [Supabase](https://supabase.com) both have a
free tier and hand you a connection string in under a minute. Put it in
`backend/.env`:

```
SDIE_DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>/<db>?ssl=require
```

(Note the `?ssl=require` — hosted providers require TLS, and that's the
query param asyncpg understands via SQLAlchemy. Neon's dashboard gives you
a `postgresql://...` string; just swap the scheme to `postgresql+asyncpg://`
and keep everything else.)

**Option B — native local install:** download the installer for your OS
from [postgresql.org/download](https://www.postgresql.org/download/)
(Windows: the EDB installer, includes pgAdmin). During setup you'll set a
password for the `postgres` user — then:

```sql
-- in psql or pgAdmin's query tool
CREATE ROLE sdie WITH LOGIN PASSWORD 'sdie' SUPERUSER;
CREATE DATABASE sdie OWNER sdie;
```

and leave `backend/.env` pointed at the default:
`SDIE_DATABASE_URL=postgresql+asyncpg://sdie:sdie@localhost:5432/sdie`

Either way, once `SDIE_DATABASE_URL` is set:

```
python -m alembic upgrade head        # create tables — required before hitting any endpoint that persists
python -m pytest tests/unit -v        # 38 tests, pure domain logic, needs no DB at all
python -m pytest tests/integration -v # 12 tests against real Postgres, skip cleanly if unreachable

uvicorn sdie.main:app --reload        # http://localhost:8000/docs
```

`docker-compose.yml` is still there and works if you ever do have Docker —
it's just no longer required to get running.

### LLM provider: Groq (free tier)

Get a free key at https://console.groq.com/keys, then set it in `backend/.env`:

```
SDIE_GROQ_API_KEY=gsk_...
SDIE_GROQ_MODEL=llama-3.3-70b-versatile
```

All LLM calls go through `shared_kernel/application/ports.py::LLMPort` —
`shared_kernel/infrastructure/llm/groq_adapter.py` is the only file that
imports the `groq` SDK. No context calls the LLM yet — evidence retrieval
is lexical (Postgres full-text search), not semantic, so nothing needs an
embedding model today. This wiring exists so a future synthesis step (e.g.
turning a `DecisionRationale` into prose) can call `get_llm_client()`
directly.

Note: HTTP routes require `X-Tenant-Id` / `X-User-Id` headers (stub auth —
see `shared_kernel/infrastructure/auth.py`). Any unhandled server error
returns a JSON body with a `trace_id` and logs the full traceback
server-side (`shared_kernel/interface/error_handling.py`) — quote the
trace_id back if you ever need to debug one.

## What each context does

- **financial_modeling** — DCF, NPV/IRR/payback, one-way sensitivity,
  probability-weighted scenarios. Cash flows and computed results persist
  (`GET /financial-modeling/cash-flow-models`).
- **decision_analysis** — MCDA weighted-sum ranking, decision-tree EMV/EVPI,
  Monte Carlo simulation, Bayesian updating. Every run persists its full
  result payload (`GET /decision-analysis/analyses`).
- **evidence_research** — ingest text documents, retrieve them via Postgres
  native full-text search (`tsvector`/`ts_rank` — no pgvector extension or
  embedding API required). Returns `Citation`s: exact excerpt + source
  label, never a paraphrase (`POST /evidence-research/documents`,
  `POST /evidence-research/search`).
- **recommendation_synthesis** — the `DecisionRationale` aggregate: fuses a
  quant analysis (from financial_modeling or decision_analysis) with cited
  evidence into one auditable record. Analysts can override the
  recommendation, but the original is never deleted — every override is
  appended with a mandatory reason
  (`POST /recommendation-synthesis/rationales`,
  `POST /recommendation-synthesis/rationales/{id}/override`).

## Testing & CI

- `tests/unit/` — pure domain logic, no I/O, no DB. Runs anywhere, always.
- `tests/integration/` — real Postgres round-trips (ORM mapping, the
  generated `tsvector` column, RLS-scoped queries). Each test runs inside a
  transaction that's rolled back at teardown, so nothing persists and there's
  no separate test database to manage. Skips cleanly (not a failure) if
  `SDIE_DATABASE_URL` doesn't resolve.
- `.github/workflows/ci.yml` — runs both suites on GitHub's own runners
  (which have Docker, independent of whether *you* do) via a Postgres
  service container, plus `ruff` lint and a frontend typecheck + build.

## Frontend

```
cd frontend
npm install
npm run dev     # http://localhost:3000
```

Talks to the backend via a Next.js rewrite (`/backend/* -> localhost:8000/*`),
configurable through `NEXT_PUBLIC_API_BASE_URL`. Financial modeling and
decision analysis have full dashboards, including a "recent analyses"
history panel backed by the new list endpoints. Evidence research and
recommendation synthesis are API-only for now — reachable via
`http://localhost:8000/docs`.

## Layout

```
backend/src/sdie/<context>/
  domain/          entities, value objects, pure calculation logic
  application/      use cases + ports (interfaces)
  infrastructure/    SQLAlchemy repos, ORM models
  interface/          FastAPI router + Pydantic schemas

backend/migrations/   Alembic — 0001 (financial + decision analysis),
                      0002 (evidence research + recommendation synthesis)

frontend/
  app/               Next.js routes (financial modeling, decision analysis)
  components/ui/     shared design-system primitives
  lib/                typed API client + shared types (mirrors backend schemas)
```

## What's next

`problem_framing` (issue trees / MECE decomposition) is the remaining stub
from the original architecture. Real auth (OIDC/JWT replacing the header
stub) and a frontend for evidence_research / recommendation_synthesis are
the next highest-value additions on top of what's here.
