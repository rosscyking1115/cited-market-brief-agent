# LedgerBrief

Audit-ready public-data brief engine for investment research teams. Every material claim in a generated brief is deterministically validated against a stored source span, and the proof ships as an exportable evidence ledger.

**Status**: Phase 2 — evidence ledger UI (click a claim → exact source span, validator status, checksum), feedback capture, advice-boundary guardrails (cited recommendations still quarantine), and a CI eval gate (citation precision ≥0.95, recall ≥0.90, zero advice leaks, prompt-injection case). Phase 1 pipeline underneath: EDGAR/FRED ingestion → structure-aware parsing → hybrid retrieval (FTS + pgvector, RRF) → cited generation → deterministic claim→span validation → Markdown + JSON citation-manifest export, audit events end to end. See `docs/PRODUCTION_PLAN.md` (v2).

## Stack

Next.js 16 (App Router, RSC) + React 19 + TypeScript + Tailwind v4 · FastAPI (Python 3.13) + SQLAlchemy 2.0 + Alembic · Postgres 18 + pgvector ≥0.8.2 (hybrid FTS + vector, RRF) · Hatchet workflows · Valkey · LiteLLM (library mode, Anthropic + OpenAI) · edgartools + Docling · S3/MinIO.

Design system derived from Salt (JPMorgan Chase's open-source design system) — see `docs/DESIGN_SYSTEM.md`.

## Quickstart

```bash
cp .env.example .env          # fill in SEC_USER_AGENT (required) and FRED_API_KEY
docker compose up -d db valkey minio

# Backend
cd backend
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python scripts/bootstrap_db.py                 # pgvector extension + tables
                                               # (or: alembic revision --autogenerate + upgrade)
uvicorn app.main:app --reload                  # http://localhost:8000/docs

# Frontend
cd ../frontend
npm install
npm run dev                                     # http://localhost:3000
```

### Run the vertical slice end to end

```bash
cd backend
python scripts/demo_brief.py
```

Ingests recent NVDA/AMD/AVGO filings (fair-access throttled) plus CPI and 10Y series,
generates a cited brief, validates every claim against stored source spans, and exports
`brief_<id>.md` + `brief_<id>.manifest.json` (the audit artifact) to `.data/exports/`.

Graceful degradation: no FRED key → filings only; no LLM key → deterministic extractive
brief (citation-perfect by construction); no OpenAI key → FTS-only retrieval (no vectors).

Or via API: `POST /watchlists` → `POST /watchlists/{id}/ingest` →
`POST /watchlists/{id}/briefs` → `GET /briefs/{id}/evidence` (ledger payload) →
`GET /briefs/{id}/markdown`. Feedback: `POST /feedback {claim_id, kind}`.

With backend + frontend running, http://localhost:3000 shows the latest brief **LIVE**
with the clickable evidence ledger; without the backend it renders demo data.

### Eval gate

```bash
cd backend && python scripts/run_evals.py     # runs in CI on every push
```

Gates: citation precision ≥0.95 · citation recall ≥0.90 · zero advice-boundary leaks.
Cases include a prompt-injection filing whose embedded "recommend buying / price target /
guaranteed return" text must be quarantined even when perfectly cited.

## Layout

```
docs/        plan v2, evaluation report, design system
backend/
  app/
    api/         routes: health, watchlists, ingest + briefs
    connectors/  SEC EDGAR (fair-access throttled), FRED/ALFRED
    ingestion/   structure-aware filing parser (char spans), pipeline
    rag/         embeddings (optional), hybrid FTS+vector retrieval, RRF
    briefs/      generator (LLM + offline fallback), citation validator,
                 markdown + citation-manifest export, orchestration service
    storage/     raw source store (local FS dev / S3 prod), per-tenant keys
    db/          SQLAlchemy 2.0 models (15 tables, RLS-ready)
    services/    append-only audit log
  scripts/       bootstrap_db.py, demo_brief.py
  tests/         parser, validator, RRF, markdown, offline generator
frontend/    Next.js app: Salt-derived tokens in app/globals.css, dashboard shell in app/page.tsx
infra/       Terraform placeholder (Phase 5)
```

## Non-negotiables (from the plan)

- SEC EDGAR: declared User-Agent, ≤10 req/s — enforced in `backend/app/connectors/sec_edgar.py`.
- No buy/sell/hold output, no portfolio advice — advice-boundary guardrails before any external use.
- Citations are application-layer: claims without a validated source span do not ship.
- Postgres RLS on all org-scoped tables before any multi-tenant deployment (Phase 5 gate).
- Launch no-go gates in `docs/PRODUCTION_PLAN.md` §9 are blocking.
