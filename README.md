# Cited Market Brief Agent

**When a generated sentence cites a source, does that source actually say it?**

This project builds cited company research briefs from SEC filings and FRED macro
data, and then tries to answer that question about its own output honestly. The
answer is not flattering, and reporting it is the point: a deterministic checker
that verifies where a quote came from catches fabricated and misfiled citations
reliably, and still accepts more unsupported claims than supported ones.

![Python 3.13](https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](https://github.com/rosscyking1115/cited-market-brief-agent/blob/main/LICENSE)
[![CI](https://github.com/rosscyking1115/cited-market-brief-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/rosscyking1115/cited-market-brief-agent/actions/workflows/ci.yml)

![English evidence-backed company brief workspace with audit status, source tape and reader editions](docs/screenshots/brief-workspace.png)

> **Status: working demonstration, actively developed, not a product.** It is a
> research and portfolio project, not a trading terminal. There is no support
> commitment. Outputs are AI-assisted and require human review before external
> use; they are factual and non-personalised, and are not investment advice, not
> a recommendation and not an offer to buy or sell any security. Released under
> the [MIT Licence](https://github.com/rosscyking1115/cited-market-brief-agent/blob/main/LICENSE).

## Who this is for

Anyone building retrieval-grounded generation who needs to know what a citation
check is worth. The interesting artifact here is not the brief — it is the
labelled corpus, the confusion matrix and the negative controls that measure the
checker, including the cases it cannot see.

## What the citation check does and does not do

The validator checks **provenance** — the cited span exists, and the quoted text
appears verbatim inside it — plus two **consistency** rules: the claim may not
assert a number or a period that the cited evidence does not contain. It does
**not** check entailment. A claim whose defect is semantic is still accepted:
"the government granted licences that would allow us to ship" read as "we
shipped", a real effect given an invented cause, an all-time high inferred from a
three-week series.

**How to read these numbers.** Unit: one claim. Positive: the system marks a
claim *supported*. Ground truth: a human label, recorded independently of the
system's output, answering "does the cited span support this claim?".
Population: every labelled claim in the named corpus.

- **precision** — of the claims the system accepted, the share the cited span really supports
- **recall** — of the claims the cited span really supports, the share the system accepted

Measured against claims labelled independently of the generator, built from real
10-Q and 8-K filings and real FRED vintages:

| | development corpus | held-out corpus |
|---|---|---|
| citation precision | 0.579 | **0.400** |
| citation recall | 1.000 | 1.000 |
| false negatives | 0 | 0 |
| true-but-unsupported caught | 6/8 | 2/6 |

**The figure that describes this system is precision 0.400 on the held-out
corpus** — of the claims it accepts, 40% are genuinely supported by the span they
cite, so 60% are not. Recall 1.000 means it accepted every claim that was
genuinely supported, rejecting none of them.

The held-out corpus was authored after the consistency rules were frozen and
scored once. It draws on sources the development corpus did not use — two 8-Ks,
the second vintage of each FRED series and unused 10-Q sections — with one
qualification: three holdout spans share a document *and section* with dev spans.
Excluding the 8 claims citing them gives precision 0.429 rather than 0.400, so
the overlap depresses the headline figure rather than flattering it. 0.579 is the
development corpus, which the rules were built against, and is not quoted on its
own. Supporting detail: on the two shapes the rules target they generalise
cleanly to unseen filings (`numeric_alteration` 3/3, `temporal_shift` 3/3); on
semantic defects they catch none.

Method, per-trap breakdown, negative controls, the open empty-quote defect and
the full limits: [`docs/EVAL_METHODOLOGY.md`](docs/EVAL_METHODOLOGY.md).

The gate is a **ratchet** at the measured level, so any regression fails CI while
progress stays possible; ≥0.95 precision remains the target, not an achieved
figure. Also blocking: the negative controls and a zero advice-boundary leak
count.

## The English brief is the only thing measured

Traditional Chinese and Korean versions of the brief exist and are offered as
reading aids. They are **unevaluated**. Nothing measures their fidelity to the
English source, whether every claim survives translation, or whether a citation
still supports its claim once both are read in the target language — and that
last failure mode is real, because the check that gives a claim its support is
performed on the English text only. Treat the English brief as the source of
record in the strict sense: it is the only version any number on this page
describes.

## Getting started

```bash
cp .env.example .env
docker compose up -d db valkey minio
```

```bash
cd backend
pip install -e ".[dev]"
python scripts/bootstrap_db.py
uvicorn app.main:app --reload
```

Reproduce the figures above without a database or a network:

```bash
cd backend
python scripts/run_evals.py
```

Full setup, configuration, the verification suite and the project map are in
[`docs/DEVELOPING.md`](docs/DEVELOPING.md).

## The second route

`/brief` is the cited research workspace described above. `/` is the **Morning
Market Radar**, a region-aware scanning view of the trading day built on the same
connectors and the same source-boundary rules — four editions, seven scheduled
exchange sessions, a sourced global risk rail. It is a different job: the brief
is read carefully once, the radar is glanced at. Details, regional scope and
captures: [`docs/MARKET_RADAR.md`](docs/MARKET_RADAR.md).

The [public demo](https://cited-market-brief-agent.vercel.app) is frontend-only
and may trail this repository.

![Cited Market Brief Agent — two-route architecture](docs/assets/overview.svg)

## Related work

Retrieval-grounded generation with citations is well covered; what is thin is
public, adversarially-labelled evidence about how much a citation check actually
buys you. This repository is one small, honest data point in a single domain —
US large-cap semiconductor filings and two macro series — and generalises to
nothing else.

Part of a responsible-fintech cluster alongside
[responsible-neobank-growth](https://github.com/rosscyking1115/responsible-neobank-growth)
and [cashflow-risk](https://github.com/rosscyking1115/cashflow-risk).

## Sources and boundaries

SEC EDGAR (declared user agent, rate-limited), FRED/ALFRED (this project uses the
FRED API but is not endorsed or certified by the Federal Reserve Bank of
St. Louis), NYT Most Popular (headline and link only), TWSE, GDELT and finance
RSS. The exact sources, public wording and retained evidence are in the
[public claim ledger](docs/claims/claim-ledger.md).

The code is available under the
[MIT licence](https://github.com/rosscyking1115/cited-market-brief-agent/blob/main/LICENSE).
