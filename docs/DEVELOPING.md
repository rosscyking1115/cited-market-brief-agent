# Developing

Setup, configuration and the full verification suite. The [README](../README.md)
carries the short version; this is everything else.

## Prerequisites

Docker, Python 3.13 and Node 20+.

SEC EDGAR requires a declared `SEC_USER_AGENT` — the connector refuses to run
without one, and throttles to 8 requests per second against EDGAR's 10 req/s
ceiling. The FRED rail requires `FRED_API_KEY`. Every other integration degrades
gracefully when its key is absent.

## Running it

```bash
cp .env.example .env
docker compose up -d db valkey minio
```

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
python scripts/bootstrap_db.py
uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
npm run dev
```

The frontend is at `http://localhost:3000`; FastAPI documentation at
`http://localhost:8000/docs`. With no backend running, the frontend falls back to
labelled demo data.

## The brief vertical slice

```bash
cd backend
python scripts/demo_brief.py
```

This ingests the configured filing and macro sources, generates a cited draft,
validates its claims and writes review-aware export artefacts under
`.data/exports/`.

## Configuration

The full list is in [`.env.example`](../.env.example). The main controls:

| Variable | Purpose |
| --- | --- |
| `SEC_USER_AGENT` | Required identifying user agent for SEC EDGAR. |
| `FRED_API_KEY` | Macro series and the global overnight-risk rail. |
| `NYT_ENABLED`, `NYT_API_KEY` | NYT Most Popular headline and link data. |
| `BBC_RSS_ENABLED`, `GDELT_ENABLED` | Latest-headline and coverage-discovery sources. |
| `ALPHA_VANTAGE_ENABLED`, `ALPHA_VANTAGE_API_KEY` | Optional market-data pilot, including Taiwan FX context. |
| `GENERATION_MODEL` | LiteLLM model identifier for brief generation and summaries. |
| `TRANSLATION_MODEL` | LiteLLM model identifier for the Traditional Chinese and Korean reading aids. |
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` | Provider keys selected according to the configured model. OpenAI also supports optional embeddings. |
| `DATABASE_URL`, `VALKEY_URL`, `S3_*` | Database, cache and raw-source storage. |
| `NEXT_PUBLIC_DEMO_MODE=1` | Builds the deterministic, backend-free frontend demo. |

## Verification

```bash
cd backend
ruff check .
ruff format --check .
mypy
pytest -q
python scripts/run_evals.py
```

```bash
cd frontend
npm test
npm run typecheck
npm run test:e2e
```

The demo build, which the documentation captures depend on:

```bash
# PowerShell
$env:NEXT_PUBLIC_DEMO_MODE="1"; npm run build
```

```bash
# macOS/Linux
NEXT_PUBLIC_DEMO_MODE=1 npm run build
```

`run_evals.py` is three blocking gates, not one: the grounded precision/recall
ratchet over both corpora, the negative controls — each deliberately breaks the
pipeline and must score badly, because a control that passes means the eval has
stopped measuring — and a zero advice-boundary leak count. It also prints the
open known-hole probe, which is a measured defect kept runnable rather than a
failure.

The browser matrix exercises all four radar editions and `/brief` at desktop,
mobile and a 200%-zoom-equivalent width, across light/dark and reduced-motion
modes. It checks route separation, language metadata, keyboard and modal
behaviour, horizontal overflow, and serious or critical accessibility findings.

## Packaging

The backend declares an sdist **allowlist** in `backend/pyproject.toml`. This is
deliberate and the direction matters: an exclude list fails open — the next
local-only directory to appear in the package root is published because nobody
thought to name it — whereas an allowlist fails closed.

`backend/tests/test_sdist_contents.py` enforces it. Its strongest assertion
builds the sdist and requires every member to be tracked by git, which stops the
whole class without needing a list of what anyone's local tooling is called.

## Project map

```text
frontend/
  app/page.tsx             Morning Market Radar route
  app/brief/page.tsx       company research workspace route
  app/components/          shared navigation and route-specific interfaces
  lib/radar-i18n.ts        typed regional catalogue
  lib/demo-data.ts         deterministic demo fixtures
  e2e/                     regional, route and accessibility matrix

backend/app/
  briefs/                  generation, validation, review and reading aids
  evals/                   grounded corpora, negative controls, scoring
  market_radar/            session schedules, risk data, news and translations
  connectors/              SEC, FRED, news, TWSE and optional market data
  fund_attribution/        Taiwan holdings and benchmark attribution
  rag/                     hybrid retrieval

docs/
  EVAL_METHODOLOGY.md      how the citation figures are produced
  MARKET_RADAR.md          the `/` route
  claims/claim-ledger.md   public claims, limitations, sources and evidence
  adr/                     architecture decisions
```

## Data and source boundaries

- **SEC EDGAR:** declared user agent and a maximum request rate enforced by the connector.
- **FRED / ALFRED:** macro series and historical revisions. This project uses the FRED API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.
- **NYT Most Popular:** headline and link only, with links back to the original publisher. Article bodies are not reproduced.
- **TWSE:** end-of-day prices and classifications for the Taiwan attribution workflow.
- **GDELT and finance RSS:** coverage discovery and latest headlines. They are never described as readership data.
- **Exchange schedules:** JPX, KRX, TWSE, HKEX, LSE, Deutsche Börse and NYSE primary documentation, linked from the [claim ledger](claims/claim-ledger.md).

## Technology

- **Frontend:** Next.js 16 App Router, React 19, TypeScript and Tailwind CSS v4.
- **Backend:** FastAPI, Python 3.13, SQLAlchemy 2, Alembic and Postgres with pgvector.
- **Retrieval and generation:** hybrid full-text/vector retrieval with reciprocal-rank fusion; LiteLLM in library mode for configured Anthropic or OpenAI models.
- **Infrastructure:** Docker Compose, Caddy, Valkey and S3/MinIO.
- **Design:** a Salt-derived token system implemented locally. The project does not depend on shadcn, TanStack or TradingView components.
