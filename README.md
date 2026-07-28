# Cited Market Brief Agent

[![CI](https://github.com/rosscyking1115/cited-market-brief-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/rosscyking1115/cited-market-brief-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
![Frontend](https://img.shields.io/badge/Next.js%2016-React%2019-000000?logo=nextdotjs&logoColor=white)
![Backend](https://img.shields.io/badge/FastAPI-Python%203.13-009688?logo=fastapi&logoColor=white)
![Database](https://img.shields.io/badge/Postgres%2018-pgvector-4169E1?logo=postgresql&logoColor=white)

One market-intelligence workbench with two deliberately separate routes:

- `/` is the region-aware **Morning Market Radar** for a quick, sourced view of the trading day.
- `/brief` is the **evidence-backed company research workspace**, where supported claims map to stored source spans and unsupported claims are flagged for human review.

The split matters. The radar is built for scanning; the brief is the project's original cited-AI proof and remains the English audited source of record. Traditional Chinese and Korean versions of the brief are labelled reading aids.

![Cited Market Brief Agent — two-route architecture](docs/assets/overview.svg)

> [!IMPORTANT]
> This is a research and portfolio project, not a trading terminal. It provides factual, non-personalised information and is not investment advice, a recommendation, or an offer to buy or sell a security.

## What is included

### Morning Market Radar — `/`

- Four editions selected with `?region=tw|kr|uk|eu`. A valid URL value wins over the saved preference; otherwise the app uses local storage and then the edition chooser.
- A typed Traditional Chinese, Korean and English catalogue for the radar shell, categories, controls, market labels and limitations.
- Seven separate scheduled regular/core sessions: Japan, Korea, Taiwan, Hong Kong, London, Xetra and New York. Each is calculated in its exchange's IANA time zone and displayed in Taipei, Seoul, London or Brussels time for the chosen edition.
- A sourced global overnight-risk rail and finance-news feed. Korea, UK and EU localise that existing global coverage; they do not claim complete local-market feeds.
- Taiwan-only USD/TWD context and ETF-versus-TAIEX attribution. These modules are not implied for other regions.
- One cached news-translation batch for Traditional Chinese and Korean. If no suitable model key is configured, the English source text remains visible and is clearly marked as original-language content.

The session clock is schedule-derived. It handles local weekdays and daylight-saving changes, but it does **not** account for exchange holidays, exceptional closures or live market state.

### Company research workspace — `/brief`

- SEC filing changes and FRED/ALFRED macro deltas assembled into a cited company brief.
- Claim-level validation checks that each cited span exists and that the quoted evidence appears verbatim in it, with document, section, accession and checksum evidence; claims that fail either check are flagged for review.
- An approval checklist and review states that stop unresolved claims from being presented as approved output.
- English as the audited source of record. Traditional Chinese and Korean are optional reading aids and do not alter the reviewed English wording.
- Markdown, PDF, PPTX and XLSX export paths that preserve review state and provenance.

### What the citation check does and does not do

The validator checks **provenance** — the cited span exists, and the quoted text appears verbatim
inside it — plus two **consistency** rules: the claim may not assert a number or a period that the
cited evidence does not contain. It does **not** check entailment. A claim whose defect is semantic
is still accepted: "the government granted licences that would allow us to ship" read as "we
shipped", a real effect given an invented cause, an all-time high inferred from a three-week series.

**How to read these numbers.** Unit: one claim. Positive: the system marks a claim *supported*.
Ground truth: a human label, recorded independently of the system's output, answering "does the
cited span support this claim?". Population: every labelled claim in the named corpus.

- **precision** — of the claims the system accepted, the share the cited span really supports
- **recall** — of the claims the cited span really supports, the share the system accepted

Measured against claims labelled independently of the generator, built from real 10-Q and 8-K filings
and real FRED vintages:

| | development corpus | held-out corpus |
|---|---|---|
| citation precision | 0.579 | **0.400** |
| citation recall | 1.000 | 1.000 |
| false negatives | 0 | 0 |
| true-but-unsupported caught | 6/8 | 2/6 |

**The figure that describes this system is precision 0.400 on the held-out corpus** — of the claims
it accepts, 40% are genuinely supported by the span they cite, so 60% are not. Recall 1.000 means it
accepted every claim that was genuinely supported, rejecting none of them.

The held-out corpus was authored after the consistency rules were frozen and scored once. It draws
on sources the development corpus did not use — two 8-Ks, the second vintage of each FRED series and
unused 10-Q sections — with one qualification: three holdout spans share a document *and section*
with dev spans (a different passage of the same AVGO 10-Q section, and the two FRED series at a
different vintage). Excluding the 8 claims citing them gives precision 0.429 rather than 0.400, so
the overlap depresses the headline figure rather than flattering it. 0.579 is the development corpus, which the rules
were built against, and is not quoted on its own. Supporting detail: on the two shapes the rules
target they generalise cleanly to unseen filings (`numeric_alteration` 3/3, `temporal_shift` 3/3);
on semantic defects they catch none.

Method, per-trap breakdown, negative controls, the open empty-quote defect and the full limits:
[`docs/EVAL_METHODOLOGY.md`](docs/EVAL_METHODOLOGY.md).

The gate is a **ratchet** at the measured level, so any regression fails CI while progress stays
possible; ≥0.95 precision remains the target, not an achieved figure. Also blocking: the negative
controls and a zero advice-boundary leak count.

## Verified local captures

These images come from the deterministic frontend demo build after the full test and accessibility gates passed. The four route captures are 1440×900.

| UK radar | Korea radar |
| --- | --- |
| ![UK edition of the Morning Market Radar with London time, seven scheduled sessions and global risk indicators](docs/screenshots/radar-uk.png) | ![Korean edition of the Morning Market Radar with Korean structural copy and Seoul session times](docs/screenshots/radar-korea.png) |
| **Taiwan radar** | **Company research workspace** |
| ![Taiwan edition of the Morning Market Radar with Traditional Chinese structural copy and Taiwan-only ETF context](docs/screenshots/radar-taiwan.png) | ![English evidence-backed company brief workspace with audit status, source tape and reader editions](docs/screenshots/brief-workspace.png) |

Static, repeatable Taiwan news capture:

![Taiwan market-news cards with Traditional Chinese summaries and source labels](docs/screenshots/news-taiwan.png)

The existing [public demo](https://cited-market-brief-agent.vercel.app) is a frontend-only demo deployment and may trail this repository until a separate deployment is approved. Deployment instructions are in [docs/DEPLOY_DEMO.md](docs/DEPLOY_DEMO.md).

## Regional scope, without overclaiming

| Edition | Interface and clock | Data scope |
| --- | --- | --- |
| Taiwan | Traditional Chinese; Taipei time | Global radar plus Taiwan-specific USD/TWD and ETF attribution |
| Korea | Korean; Seoul time | Localised view of the sourced global radar |
| UK | English; London time | Localised view of the sourced global radar |
| EU | English; Brussels time | Localised view of the sourced global radar |

Published session hours are checked against the exchanges' primary documentation. The exact sources, public wording and retained tests are recorded in the [public claim ledger](docs/claims/claim-ledger.md).

## Technology

- **Frontend:** Next.js 16 App Router, React 19, TypeScript and Tailwind CSS v4.
- **Backend:** FastAPI, Python 3.13, SQLAlchemy 2, Alembic and Postgres with pgvector.
- **Retrieval and generation:** hybrid full-text/vector retrieval with reciprocal-rank fusion; LiteLLM in library mode for configured Anthropic or OpenAI models.
- **Infrastructure:** Docker Compose, Caddy, Valkey and S3/MinIO.
- **Design:** a Salt-derived token system implemented locally. The project does not depend on shadcn, TanStack or TradingView components.

## Getting started

Prerequisites: Docker, Python 3.13 and Node 20+. SEC EDGAR requires a declared `SEC_USER_AGENT`; the FRED rail requires `FRED_API_KEY`. Other integrations degrade gracefully when their keys are absent.

```bash
cp .env.example .env
docker compose up -d db valkey minio

# Backend
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
python scripts/bootstrap_db.py
uvicorn app.main:app --reload

# Frontend, in another terminal
cd frontend
npm install
npm run dev
```

The frontend is available at `http://localhost:3000`; FastAPI documentation is at `http://localhost:8000/docs`. With no backend, the frontend falls back to labelled demo data.

Run the brief vertical slice:

```bash
cd backend
python scripts/demo_brief.py
```

This ingests the configured filing and macro sources, generates a cited draft, validates its claims and writes review-aware export artefacts under `.data/exports/`.

## Configuration

The full list is in [.env.example](.env.example). The main controls are:

| Variable | Purpose |
| --- | --- |
| `SEC_USER_AGENT` | Required identifying user agent for SEC EDGAR. |
| `FRED_API_KEY` | Macro series and the global overnight-risk rail. |
| `NYT_ENABLED`, `NYT_API_KEY` | NYT Most Popular headline and link data. |
| `BBC_RSS_ENABLED`, `GDELT_ENABLED` | Latest-headline and coverage-discovery sources. |
| `ALPHA_VANTAGE_ENABLED`, `ALPHA_VANTAGE_API_KEY` | Optional market-data pilot, including Taiwan FX context. |
| `GENERATION_MODEL` | LiteLLM model identifier for brief generation and summaries. |
| `TRANSLATION_MODEL` | LiteLLM model identifier for Traditional Chinese and Korean reading aids. |
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` | Provider keys selected according to the configured model. OpenAI also supports optional embeddings. |
| `DATABASE_URL`, `VALKEY_URL`, `S3_*` | Database, cache and raw-source storage. |
| `NEXT_PUBLIC_DEMO_MODE=1` | Builds the deterministic, backend-free frontend demo. |

## Data and source boundaries

- **SEC EDGAR:** declared user agent and a maximum request rate enforced by the connector.
- **FRED / ALFRED:** macro series and historical revisions. This project uses the FRED API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.
- **NYT Most Popular:** headline and link only, with links back to the original publisher. Article bodies are not reproduced.
- **TWSE:** end-of-day prices and classifications for the Taiwan attribution workflow.
- **GDELT and finance RSS:** coverage discovery and latest headlines. They are never described as readership data.
- **Exchange schedules:** JPX, KRX, TWSE, HKEX, LSE, Deutsche Börse and NYSE primary documentation, linked from the [claim ledger](docs/claims/claim-ledger.md).

## Verification

```bash
# Backend
cd backend
ruff check .
ruff format --check .
pytest -q
python scripts/run_evals.py

# Frontend
cd frontend
npm test
npm run typecheck
# PowerShell
$env:NEXT_PUBLIC_DEMO_MODE="1"; npm run build
# macOS/Linux
NEXT_PUBLIC_DEMO_MODE=1 npm run build
npm run test:e2e
```

The retained suite currently covers 122 backend tests, 29 frontend unit tests and 8 Playwright/axe browser cases. The browser matrix exercises all four editions and `/brief` at desktop, mobile and a 200%-zoom-equivalent width, across light/dark and reduced-motion modes. It also checks route separation, language metadata, keyboard/modal behaviour, horizontal overflow and serious/critical accessibility findings.

To reproduce the documentation images after a verified demo-mode build:

```bash
cd frontend
npm run capture:readme
```

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
  market_radar/            session schedules, risk data, news and translations
  briefs/                  generation, validation, review and reading aids
  connectors/              SEC, FRED, news, TWSE and optional market data
  fund_attribution/        Taiwan holdings and benchmark attribution
  rag/                     hybrid retrieval

docs/
  claims/claim-ledger.md   public claims, limitations, sources and retained evidence
  adr/                     architecture decisions
  screenshots/             deterministic README captures
```

## Licence and disclaimer

The code is available under the [MIT licence](LICENSE).

Outputs are AI-assisted and require human review before external use. They are factual and non-personalised, not investment advice, not a recommendation and not an offer to buy or sell any security.
