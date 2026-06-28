# Cited Market Brief Agent

A region-aware **Morning Market Radar** for everyday investors, plus an audit-ready
**evidence-backed brief engine** for research teams — in one app. Market context and
news are surfaced in plain language (with Traditional-Chinese key points for the Taiwan
edition), and every claim in a generated research brief is deterministically validated
against a stored source span before it ships.

> **Two surfaces, one page.**
> 1. **Morning Market Radar** (primary, consumer) — Asia→US market clock, a FRED-backed
>    overnight-risk rail, most-read finance news with day/week/month windows and AI
>    summaries, and a Taiwan **ETF-vs-benchmark attribution** tool.
> 2. **Evidence-backed company brief** (secondary, professional) — SEC filing changes and
>    macro deltas, validated claim-by-claim against primary sources, with an exportable
>    evidence ledger.
>
> The radar leads; the brief engine is a separate module on the same page (hidden on the
> Taiwan consumer edition).

---

## Features

### Morning Market Radar
- **Region-aware editions** — Taiwan (繁中), Korea (한국어), UK & EU (English). Region
  selects language, market anchor, and copy automatically (`frontend/lib/regions.ts`,
  `frontend/lib/radar-i18n.ts`).
- **Market clock** — Japan → Korea → Taiwan → HK/China → Europe → US, with live open /
  lunch / closed status so you know what's driving the tape right now.
- **Overnight-risk rail** — VIX, USD/TWD·JPY·CNY, a broad-dollar index, WTI, and the US
  10Y, sourced from **FRED** (EOD) and **Alpha Vantage** (FX), cached and persisted.
- **Most-read finance news** — genuine readership from the **NYT Most Popular** API over
  **1-day / 1-week / 1-month** windows, plus finance RSS (BBC Business, CNBC, MarketWatch,
  NYT Business, Guardian) and **GDELT** for coverage. Finance-only filtering keeps it on
  topic. Windows are cumulative (this week includes today).
- **Plain-language digests (Taiwan)** — each headline is translated to Traditional-Chinese
  **key points** (not full text), and the app generates **today / this-week / this-month**
  AI report summaries. All best-effort and cached; falls back to English on failure.
- **Glossary** of market terms for non-specialist readers.

### ETF / fund attribution (Taiwan)
- Paste or upload a holdings list; fill missing daily returns automatically from **TWSE**.
- **Fund vs. TAIEX**: active return, top contributors, biggest drags, and a full
  all-holdings table sorted by contribution.
- **Sector (產業) attribution** — fund vs. index sector weights with a diverging-bar view,
  per-sector daily return, and allocation effect. Industries auto-classified from TWSE.
- **Daily auto-refresh** — a scheduled job recomputes the latest attribution so the page
  is ready each morning.

### Evidence-backed brief engine
- **Cited generation** — SEC EDGAR filings + FRED/ALFRED macro series → a brief where every
  material claim links to a validated source span. No validated span → the claim doesn't ship.
- **Evidence ledger UI** — click any claim to see the quote, document, section, accession,
  checksum, and retrieval time.
- **Change detection** — risk-factor / MD&A paragraph diffs between same-form filings and
  vintage-aware macro deltas, so the brief literally answers "what changed since yesterday".
- **Analyst review + approval gating** — per-section accept / edit / reject / needs-source;
  approval is blocked until every section is resolved.
- **Exports** — Markdown, PDF (sandboxed render, JS off, network blocked), editable PPTX,
  and XLSX. All review-state-aware, watermarked to the approval, with an EU AI-Act Art. 50
  AI marking embedded.

---

## Stack

- **Frontend** — Next.js 16 (App Router, RSC) · React 19 · TypeScript · Tailwind v4
  (CSS-variable design tokens).
- **Backend** — FastAPI (Python 3.13) · SQLAlchemy 2.0 · Alembic · Postgres 18 + pgvector
  (hybrid FTS + vector retrieval, RRF).
- **AI** — LiteLLM (library mode): Anthropic for generation/summaries, OpenAI for optional
  embeddings. Defaults: `GENERATION_MODEL=anthropic/claude-sonnet-4-6`.
- **Infra** — Docker Compose · Caddy reverse proxy · Valkey · S3/MinIO for raw source storage.

Design tokens are derived from Salt (JPMorgan Chase's open-source design system); see
`docs/DESIGN_SYSTEM.md`.

---

## Quickstart (local dev)

```bash
cp .env.example .env          # see "Configuration" below — SEC_USER_AGENT + FRED_API_KEY at minimum
docker compose up -d db valkey minio

# Backend
cd backend
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python scripts/bootstrap_db.py                   # pgvector extension + tables
uvicorn app.main:app --reload                    # http://localhost:8000/docs

# Frontend
cd ../frontend
npm install
npm run dev                                       # http://localhost:3000
```

With both running, http://localhost:3000 shows live data; without the backend it renders
demo data so the UI always works. The frontend proxies `/api/*` to the backend
(`frontend/next.config.ts`), so no CORS setup is needed in dev.

### Run the brief vertical slice

```bash
cd backend && python scripts/demo_brief.py
```

Ingests recent NVDA/AMD/AVGO filings plus CPI and 10Y series, generates a cited brief,
validates every claim, and exports `brief_<id>.md` + `.manifest.json` to `.data/exports/`.
Graceful degradation: no FRED key → filings only; no LLM key → deterministic extractive
brief (citation-perfect by construction); no OpenAI key → FTS-only retrieval.

---

## Staging deploy (Docker Compose + Caddy)

The staging stack (`docker-compose.staging.yml`) runs Caddy, the Next.js frontend, the
FastAPI backend, a scheduler, a one-shot DB bootstrap, Postgres, and Valkey. Caddy serves
the frontend and reverse-proxies `/api/*` to the backend.

```bash
# on the server, in the repo root
dc() { docker compose --env-file .env.staging -f docker-compose.staging.yml "$@"; }
git pull origin codex/staging-deploy
dc build backend frontend && dc up -d
dc logs -f backend          # tail logs
```

Put real keys in `.env.staging` (gitignored). The news pipeline is prewarmed at startup
and refreshed in the background (stale-while-revalidate), so pages never block on the
live fetch + LLM translation.

---

## Configuration

Key environment variables (full list in `.env.example`):

| Variable | Purpose |
| --- | --- |
| `SEC_USER_AGENT` | **Required** by SEC EDGAR — a declared identifying User-Agent. |
| `FRED_API_KEY` | Overnight-risk rail (VIX, rates, FX, commodities) + macro series. |
| `NYT_ENABLED`, `NYT_API_KEY` | Most-read finance news (1d/1w/1m most-viewed). |
| `BBC_RSS_ENABLED`, `GDELT_ENABLED` | Finance RSS feeds and coverage discovery. |
| `ALPHA_VANTAGE_ENABLED`, `ALPHA_VANTAGE_API_KEY` | Live FX rates. |
| `ANTHROPIC_API_KEY`, `GENERATION_MODEL` | Brief generation + news report summaries. |
| `TRANSLATION_MODEL` | Traditional-Chinese key-point translation. |
| `OPENAI_API_KEY` | Optional embeddings for hybrid retrieval. |
| `DATABASE_URL`, `VALKEY_URL`, `S3_*` | Postgres, cache, raw source storage. |
| `AUTH_REQUIRED`, `OIDC_*`, `RATE_LIMIT_PER_MINUTE` | Multi-tenant hardening (off by default). |

Everything degrades gracefully: missing data-source keys disable that source rather than
breaking the page.

---

## Data sources & compliance

- **SEC EDGAR** — declared User-Agent, ≤10 req/s, enforced in `backend/app/connectors/sec_edgar.py`.
- **FRED / ALFRED** — macro series and revisions (this product uses the FRED® API but is
  not endorsed or certified by the Federal Reserve Bank of St. Louis).
- **NYT Most Popular** — headline + link only, linked back to nytimes.com per the developer
  terms; article body text is never reproduced.
- **TWSE** — end-of-day prices and industry classification for ETF attribution.
- **GDELT / finance RSS** — coverage and latest headlines (labeled as such, never "most read").

---

## Non-negotiables

- **No buy / sell / hold output, no portfolio advice.** Advice-boundary guardrails run
  before any external use; the eval gate fails on advice leaks. Everything is educational /
  informational only.
- **Citations are application-layer** — a claim without a validated source span does not ship.
- **Postgres RLS** on all org-scoped tables before any multi-tenant deployment.
- Launch no-go gates in `docs/PRODUCTION_PLAN.md` are blocking.

---

## Tests & eval gate

```bash
cd backend && python -m pytest -q        # unit + integration
cd backend && python scripts/run_evals.py # citation precision ≥0.95, recall ≥0.90, zero advice leaks
cd frontend && npx tsc --noEmit && npx next build
```

---

## Layout

```
docs/        product & security plans, design system, demo deck
backend/
  app/
    api/routes/        health, watchlists, ingest, briefs, market-radar, fund-attribution
    connectors/        SEC EDGAR, FRED, NYT, GDELT, finance RSS, TWSE, Alpha Vantage
    ingestion/         structure-aware filing parser (char spans), pipeline
    rag/               embeddings (optional), hybrid FTS+vector retrieval, RRF
    briefs/            cited generator + offline fallback, claim→span validator, exports
    market_radar/      clock, overnight risk, news assembly + translation + summaries
    fund_attribution/  holdings parsing, fund/sector attribution, daily refresh
    storage/ db/ services/   raw source store, SQLAlchemy models, append-only audit log
  scripts/             bootstrap_db, demo_brief, refresh_fund_attribution, run_scheduled, run_evals
  tests/               parser, validator, RRF, market radar, fund attribution, exports
frontend/
  app/components/      radar dashboard, ETF tool, evidence ledger, brief canvas
  lib/                 api client, region profiles, radar i18n
infra/                 Terraform placeholder
pilot/                 runbook, metrics, case-study template
```

---

## Status

Personal/pilot-ready. The Taiwan Morning Market Radar (news + ETF attribution) is the
actively-used consumer surface; the evidence-backed brief engine is a mature secondary
module retained for professional/B2B use. See `docs/` for the full plan history.

> **Disclaimer.** Factual, cited, non-personalized. Not investment advice, not a
> recommendation, and not an offer to buy or sell any security. AI-assisted content —
> human review required before external use.
