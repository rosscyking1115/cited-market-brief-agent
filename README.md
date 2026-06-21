# Cited Market Brief Agent

Audit-ready public-data brief engine for investment research teams. Every material claim in a generated brief is deterministically validated against a stored source span, and the proof ships as an exportable evidence ledger.

> **What the live app leads with.** The web surface (`frontend/`) is a region-aware **Morning Market Radar**: the Asia→US market clock, a FRED-backed overnight-risk rail (VIX, FX, commodities, rates), and source-backed headlines (BBC RSS / GDELT — labeled *latest/trending*, never *most read*) — plus a Taiwan **ETF/fund vs. benchmark attribution** tool. The cited-brief engine described below is a **secondary, evidence-backed module** on the same page. See `docs/TAIWAN_MORNING_MARKET_RADAR_PLAN.md` and `docs/FUND_ATTRIBUTION_PLAN.md`.

**Status**: Phase 6 (pilot-ready) — pilot kit in `pilot/` (runbook with daily/weekly rituals, error log with failure-mode taxonomy, case-study template), `scripts/seed_watchlists.py` (Semis/Megabanks/Energy templates), resilient scheduled runner (per-watchlist failure isolation + audit), `scripts/pilot_metrics.py` (weekly scorecard → `pilot/METRICS_SNAPSHOT.md`), and the product demo deck at `docs/Cited_Market_Brief_Agent_Demo.pptx`. Start: seed → `run_scheduled.py --force` → daily ritual. Phase 5 (hardening) underneath — Postgres RLS tenant isolation with a CI coverage guard (`scripts/apply_rls.py`, fail-closed GUC policies inherited by vector/FTS queries), OIDC bearer-token enforcement with JWKS validation (`AUTH_REQUIRED=true`), sliding-window rate limiting, security headers + CSP, expanded red-team guardrails (prompt-manipulation and URL-exfiltration quarantine, even when perfectly cited), CI security job (pip-audit, npm audit, CycloneDX SBOM), incident-response draft and runbooks in `docs/SECURITY.md`, and a backup/restore drill script. Remaining before external launch (tracked in SECURITY.md): staging deploy, live cross-tenant leakage test, IdP setup, external pen test, privacy docs with counsel. Phase 4 underneath — full export suite. PDF (self-contained escaped HTML rendered by sandboxed Playwright: JavaScript off, all network aborted), editable PPTX morning pack, XLSX workbook (brief/ledger/sources/macro-data tabs with formula-injection escaping), all review-state-aware: rejected sections excluded, analyst edits exported, watermark tied to approval, Art. 50 AI marking embedded in every format, and the manifest↔export consistency check is a tested invariant. Phase 3 underneath — change detection and analyst review. Filing diffs (risk-factor/MD&A paragraph diffs between same-form filings, blocks mapped to stored chunk spans so change claims stay citable), vintage-aware macro deltas with ALFRED-style revision detection, "since last brief" comparison, per-section accept/edit/reject/needs-source review with approval gating, and a schedule runner. Changed spans lead the evidence pack, so generated briefs literally answer "what changed". On top of Phase 2 (evidence ledger UI, feedback, guardrails, CI eval gate) and Phase 1 (cited generation pipeline with deterministic claim→span validation). See `docs/PRODUCTION_PLAN.md` (v2).

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

Phase 3: `GET /watchlists/{id}/changes` (filing diffs, macro deltas, new sources) ·
`PATCH /briefs/{id}/sections/{n} {action: accept|edit|reject|needs_source}` ·
`POST /briefs/{id}/approve` (blocked until every section is resolved) ·
`python scripts/run_scheduled.py` (cron-due watchlists; Hatchet takes over in Phase 5).

Phase 4: `GET /briefs/{id}/export/{pdf|pptx|xlsx}` — review-state-aware downloads
(rejected sections excluded, edits applied, approval watermark, Art. 50 marking).
PDF needs `pip install -e ".[exports]" && playwright install chromium`; PPTX/XLSX
work out of the box.

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
