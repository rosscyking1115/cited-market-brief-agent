# Claim ledger — Cited Market Brief Agent

Public wording is allowed only when the evidence in this table remains present and passing. The radar reports scheduled weekday sessions, not holiday-aware live market status.

## How to read the citation-accuracy numbers

- **Unit:** one claim.
- **Positive:** the system marks a claim *supported*.
- **Ground truth:** a human label, recorded independently of the system's output, answering "does the cited span support this claim?".
- **Population:** every labelled claim in the named corpus.
- **precision** — of the claims the system accepted, the share the cited span really supports.
- **recall** — of the claims the cited span really supports, the share the system accepted.

Every public statement of citation precision or recall must carry that definition inline, and it must come *before* the number, not after it. A bare figure is uninterpretable — a reader cannot tell whether a precision of 0.400 means 40% of accepted claims are supported or 40% of rejections were correct, and those are opposite readings of the same system. Quoting one without the definition is a claim-ledger violation, not a style preference.

The figure that describes the system is **precision 0.400 on the held-out corpus**. 0.579 is the development corpus, which the rules were built against, and is never quoted on its own.

| # | Public claim | Surface | Retained evidence | Status |
|---|---|---|---|---|
| 1 | “One workbench with two routes: the market radar at `/` and the company research workspace at `/brief`.” | README, demo, diagram | `frontend/lib/route-contract.test.ts`; `frontend/e2e/regional-workspaces.spec.ts` | Supported |
| 2 | “A valid `?region=tw\|kr\|uk\|eu` value overrides the saved edition; otherwise the app uses local storage and then the chooser.” | README, demo | `frontend/lib/regional-behaviour.test.ts`; `frontend/e2e/regional-workspaces.spec.ts` | Supported |
| 3 | “Taiwan, Korea, UK and EU localise the existing sourced global radar; the product does not claim complete local-market coverage.” | README, radar scope note | `frontend/lib/radar-i18n.ts`; region filtering tests in `frontend/lib/regional-behaviour.test.ts` | Supported |
| 4 | “Taiwan-specific USD/TWD and ETF attribution appear only in Taiwan.” | README, radar | `visibleRiskSymbols` regression; `ShowOnTaiwan` route implementation; browser route matrix | Supported |
| 5 | “The market clock covers seven separate scheduled regular/core sessions, calculated in each exchange’s IANA time zone.” | README, radar | `backend/tests/test_market_radar.py` schedule, weekend and DST tests; `backend/app/market_radar/service.py` | Supported |
| 6 | “Scheduled session status is not exchange-holiday aware and is not live market status.” | README, radar | Persistent caveat in `frontend/lib/radar-i18n.ts`; browser matrix | Supported limitation |
| 7 | “Current regular/core hours follow the exchanges’ published schedules.” | README, claim ledger | [JPX](https://www.jpx.co.jp/english/systems/equities-trading/), [KRX](https://global.krx.co.kr/contents/GLB/06/0602/0602010201/GLB0602010201T1.jsp), [TWSE](https://www.twse.com.tw/en/products/system/trading.html), [HKEX](https://www.hkex.com.hk/Global/Exchange/FAQ/Securities-Market/Trading/CAS?sc_lang=en), [LSE](https://www.londonstockexchange.com/personal-investing/faqs), [Deutsche Börse](https://www.cashmarket.deutsche-boerse.com/cash-en/trading/trading-calendar-and-trading-hours), [NYSE](https://www.nyse.com/partial/trade/trading-hours); accessed 19 July 2026 | Supported |
| 8 | “News translation is one cached batch for Traditional Chinese and Korean. Without a configured model key, the English headline remains and is labelled as original-language content.” | README, radar | `backend/tests/test_market_radar.py`; `frontend/lib/regional-behaviour.test.ts` | Supported |
| 9 | “The company brief opens in English as the audited source of record; Traditional Chinese and Korean are reading aids.” | README, `/brief` | `frontend/app/components/BriefCanvas.tsx`; route and browser tests | Supported |
| 10 | “Claim-level validation checks that each cited span exists and that the quoted evidence appears verbatim in it, and flags claims that fail either check.” | README, `/brief` | `backend/app/briefs/validator.py`; `backend/tests/test_evals.py` | Supported |
| 10a | “The validator checks citation provenance plus two consistency rules (numeric and temporal); it does not check entailment. Of the claims it accepts on the held-out corpus, 0.400 are genuinely supported by the span they cite (precision; 0.579 on the development corpus), and it accepted every genuinely supported claim, rejecting none (recall 1.000, zero false negatives on both). Unit: one claim; positive: the system marks a claim supported; population: every labelled claim in the named corpus.” | README, `docs/EVAL_METHODOLOGY.md` | `backend/app/briefs/consistency.py`; `backend/app/evals/grounded.py`; `backend/app/evals/corpus/`; `backend/scripts/run_evals.py` | Supported limitation — measured 2026-07-27, corpus v1.0.0 / v1.0.0-holdout |
| 10b | “The evaluation gate is scored against ground-truth labels assigned independently of the generator, with negative controls that must score badly, and is ratcheted at the measured level so any regression fails CI.” | `docs/EVAL_METHODOLOGY.md` | `backend/app/evals/controls.py`; `backend/tests/test_eval_mutations.py`; `RATCHET` in `backend/scripts/run_evals.py` | Supported when `python scripts/run_evals.py` passes |
| 10c | “The consistency rules were validated on a corpus the author attests was written after they were frozen and scored once — no commit ordering corroborates that, and the corpus and rules share an author — over sources the development corpus largely did not use (three of eight spans share a document and section; excluding the claims citing them raises precision to 0.429 from 0.400). On the shapes they target they generalise (numeric 3/3, temporal 3/3 on unseen filings); on semantic defects — modal strength, causal attribution, superlatives, spelled-out quantities, entity substitution, vintage attribution — they catch none.” | `docs/EVAL_METHODOLOGY.md` | `backend/app/evals/corpus/holdout_claims.json`; `backend/tests/test_grounded_evals.py` | Supported — measured once, 2026-07-27 |
| 10d | “Removing every evidence quote leaves the measured score completely unchanged, because an empty quote skips the provenance check and the consistency rules read the claim text rather than the quote.” | `docs/EVAL_METHODOLOGY.md` | `KNOWN_HOLE_PROBES` in `backend/app/evals/controls.py`; `backend/tests/test_grounded_evals.py` | Supported limitation — open defect, pinned by test |
| 12 | “A narrow mypy gate runs at strict over the citation validator, the eval scoring path and the script that prints the figures. The rest of the backend is annotated but unchecked.” | `docs/EVAL_METHODOLOGY.md` | `[tool.mypy]` in `backend/pyproject.toml`; `backend/tests/test_type_gate.py`; `.github/workflows/ci.yml` | Supported |
| 11 | “The retained browser gate covers all four editions and `/brief` at desktop, mobile and a 200%-zoom-equivalent width, in light/dark and reduced-motion modes, with no serious/critical axe findings or horizontal overflow.” | README, testing | `frontend/e2e/regional-workspaces.spec.ts` | Supported when `npm run test:e2e` passes |

## Prohibited wording

- “Live open/closed market status” — the clock is schedule-derived and not holiday-aware.
- “Fully local UK/EU/Korea market data” — these editions localise sourced global indicators.
- “Korean or Traditional Chinese source brief” — the English brief is the audited source of record.
- “Trading terminal”, “investment advice” or “buy/sell signal”.
- “Citation precision ≥0.95” as a statement of achieved performance. That is the target; the measured figures are 0.579 (dev) and 0.400 (holdout) (`docs/EVAL_METHODOLOGY.md`).
- **Any precision or recall figure stated without the definition above.** What is being classified, what counts as a positive, and over what population must travel with the number, every time. Enforced by `backend/tests/test_public_claims.py`.
- The dev-corpus figure quoted alone. Any public citation-accuracy number must be the holdout figure, or both together — the dev corpus is the one the rules were built against.
- The per-shape generalisation result (`numeric_alteration` 3/3, `temporal_shift` 3/3 on unseen filings) presented as the headline. It is supporting detail explaining *why* the holdout figure lands where it does; the headline is 0.400.
- “Verified/checked that claims are supported by their sources”, or any use of “entailment”, “fact-checked” or “validated against the source” for what the validator does. It checks where a quote came from, plus whether the claim asserts a quantity or period the evidence lacks. Semantic support is not checked.
- Any citation-accuracy figure sourced from `generate_deterministic`. That path is citation-perfect by construction and its precision/recall are not measurements.
- “The evidence quote is verified” without qualification — an empty `evidence_quote` skips the check entirely (claim 10d).
