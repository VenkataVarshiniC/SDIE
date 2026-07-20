# SDIE — Strategic Decision Intelligence Engine (scaffold)

Modular-monolith backend (Clean Architecture / DDD, one bounded context per
directory) + Next.js frontend. All six bounded contexts are fully working
end to end: **financial_modeling**, **decision_analysis**,
**evidence_research**, **recommendation_synthesis**, **problem_framing**,
and **workspace** — the orchestration layer that ties the other five
together into one product.

## Backend

```
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
```

### Database — no Docker needed

**Option A — hosted free Postgres:** [Neon](https://neon.tech) or
[Supabase](https://supabase.com), free tier, connection string in under a
minute. Put it in `backend/.env` as
`SDIE_DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>/<db>?ssl=require`.

**Option B — native install:** [postgresql.org/download](https://www.postgresql.org/download/),
then:
```sql
CREATE ROLE sdie WITH LOGIN PASSWORD 'sdie' SUPERUSER;
CREATE DATABASE sdie OWNER sdie;
```

Either way:
```
python -m alembic upgrade head        # 0001 -> 0002 -> 0003 -> 0004
python -m pytest tests/unit -v        # 86 tests, pure domain logic, no DB
python -m pytest tests/integration -v # 18 tests against real Postgres, skip cleanly if unreachable

uvicorn sdie.main:app --reload        # http://localhost:8000/docs
```

### LLM provider: Groq (free tier)

Get a free key at https://console.groq.com/keys → `backend/.env`:
```
SDIE_GROQ_API_KEY=gsk_...
SDIE_GROQ_MODEL=llama-3.3-70b-versatile
```
Used in exactly one place: `POST /recommendation-synthesis/rationales/{id}/narrative`,
which turns a `DecisionRationale` into a prose memo, grounded strictly in
that rationale's own recommendation, confidence note, and cited excerpts —
the system prompt forbids introducing anything else. Without a key, that
one endpoint returns `503` with a link to get one; everything else works
with zero LLM dependency.

## What each context does

- **financial_modeling** — DCF, NPV/IRR/payback, sensitivity, scenarios.
  Every valuation also runs against an industry benchmark table (WACC
  ranges, IRR hurdles by sector — pass `industry` on creation) and returns
  `flags`: plain-language warnings when a discount rate, IRR, or cash flow
  pattern sits outside where similar deals normally land.
- **decision_analysis** — MCDA ranking, decision-tree EMV/EVPI, Monte
  Carlo, Bayesian updating, plus two robustness checks: `weight_robustness`
  (how far each MCDA criterion's weight would have to move, holding the
  rest renormalized, before the recommendation flips) and
  `probability_breakeven` (for a two-option/two-outcome decision tree, the
  exact probability at which the two options' EMVs cross). Also flags
  over-concentrated weights and EVPI that's large relative to the best
  option's expected value.
- **evidence_research** — ingest text, retrieve via Postgres native
  full-text search (no pgvector, no embedding API). Returns exact-excerpt
  citations, never paraphrases.
- **recommendation_synthesis** — `DecisionRationale`: fuses a quant
  analysis with cited evidence into one auditable record, supports
  analyst overrides (original never deleted, reason mandatory), can
  generate a grounded executive narrative on demand via Groq, and exports
  a board-ready one-page PDF memo (`GET
  /recommendation-synthesis/rationales/{id}/one-pager`, reportlab-based).
- **problem_framing** — guided methodology templates (Five Forces, SWOT)
  as structured section lists with guiding questions
  (`GET /problem-framing/templates/{framework}`); fill one in via
  `POST /problem-framing/analyses`. `completion_ratio` tells you how much
  of the framework you've actually worked through.
- **workspace** — the orchestration seam. `Engagement` references
  artifacts from all five other contexts by opaque ID and validates each
  one actually exists before linking it. `status` is computed from
  whatever's linked so far, not a rigid stage gate — see "Workspace
  orchestration" below.
- **workspace** — the orchestration seam. `Engagement` references
  artifacts from the other five contexts by opaque ID, validating each
  link actually exists (`POST /workspace/engagements/{id}/link-*`).
  `status` is computed from whatever's linked so far, not gated to a
  strict order — see `workspace/domain/entities.py` for the reasoning.

## Testing & CI

- `tests/unit/` — 86 tests, pure domain logic, no I/O.
- `tests/integration/` — 18 tests, real Postgres round-trips, each
  wrapped in a rolled-back transaction, skip cleanly if `SDIE_DATABASE_URL`
  doesn't resolve.
- `.github/workflows/ci.yml` — both suites + ruff + frontend typecheck/build
  on GitHub's own runners (their Docker, not yours).

## Frontend

```
cd frontend
npm install
npm run dev     # http://localhost:3000
```

Every backend context now has a working UI, orchestrated by `/dashboard/workspace` — the front
door to the product. Start an engagement there and it walks you through problem framing,
evidence, quant analysis, and synthesis, auto-linking each artifact back to the engagement as
you create it (no manual ID pasting). Each tool is also directly reachable on its own:
financial modeling, decision analysis (MCDA, Monte Carlo, decision tree), evidence research,
recommendation synthesis (including narrative generation and one-pager PDF export), and problem
framing.

## Layout

```
backend/src/sdie/<context>/
  domain/          entities, value objects, pure calculation logic
  application/      use cases + ports (interfaces)
  infrastructure/    SQLAlchemy repos, ORM models
  interface/          FastAPI router + Pydantic schemas

backend/migrations/   0001 (financial + decision analysis)
                      0002 (evidence research + recommendation synthesis)
                      0003 (industry benchmarks + problem framing)
                      0004 (workspace engagements)
```

## Workspace orchestration

`workspace` is the sixth bounded context: an `Engagement` aggregate that references artifacts
from the other five contexts by opaque ID (never a foreign key — same pattern as
`recommendation_synthesis`'s `QuantSourceRef`). Status (`framing` → `evidence_gathering` →
`quant_analysis` → `synthesis` → `complete`) is computed from whatever's been linked, in
whatever order it happened — no rigid stage-gating, since real case teams don't work in a
strict sequence. `COMPLETE` is the one enforced rule: it requires both a rationale and at
least one quant analysis backing it. See the docstring on `Engagement` in
`workspace/domain/entities.py` for the full reasoning.

## What's next

Real auth (OIDC/JWT replacing the header stub) is the biggest remaining gap before this
could face real users.

## Case studies

`case-studies/blockbuster-netflix-2000.md` — a hindcast validation: the real 2000
Blockbuster/Netflix acquisition decision, run through SDIE's live MCDA and
recommendation-synthesis APIs using only publicly cited facts, with the actual generated
one-pager PDF as the deliverable. Useful as a worked example of the full pipeline
(quant analysis → evidence-grounded rationale → board-ready export) end to end.
