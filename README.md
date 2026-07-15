# SDIE — Strategic Decision Intelligence Engine (scaffold)

Modular-monolith backend (Clean Architecture / DDD, one bounded context per
directory) + Next.js frontend. This scaffold implements two fully working
bounded contexts end to end: **financial_modeling** and **decision_analysis**.
Others (`problem_framing`, `evidence_research`, `workspace`) are stubbed as
empty directories ready for the same layering.

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
python -m pytest tests/unit -v        # 22 tests, pure domain logic, needs no DB at all

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
imports the `groq` SDK. Swapping providers later means writing a new
adapter behind the same port, not touching any use case or domain code.
No context currently calls the LLM yet (evidence_research is still a stub);
this wiring exists so that context can be built directly against
`get_llm_client()` next.

Note: HTTP routes require `X-Tenant-Id` / `X-User-Id` headers (stub auth —
see `shared_kernel/infrastructure/auth.py`). Persisting cash-flow models and
decision analyses requires the Postgres container to be up; the domain
math itself (`domain/services.py` in each context) needs no infrastructure
at all and is what the unit tests exercise.

## Frontend

```
cd frontend
npm install
npm run dev     # http://localhost:3000
```

Talks to the backend via a Next.js rewrite (`/backend/* -> localhost:8000/*`),
configurable through `NEXT_PUBLIC_API_BASE_URL`.

## Layout

```
backend/src/sdie/<context>/
  domain/          entities, value objects, pure calculation logic
  application/      use cases + ports (interfaces)
  infrastructure/    SQLAlchemy repos, ORM models
  interface/          FastAPI router + Pydantic schemas

frontend/
  app/               Next.js routes (financial modeling, decision analysis)
  components/ui/     shared design-system primitives
  lib/                typed API client + shared types (mirrors backend schemas)
```

## What's next

Evidence & Research (RAG ingestion + citation-grounded retrieval),
Problem Framing (issue trees / MECE), and the Recommendation Synthesis
context that fuses quant output with cited evidence into an auditable
`DecisionRationale` aggregate.
