# Claim ledger — Cited Market Brief Agent

Public wording is allowed only when the evidence in this table remains present and passing. The radar reports scheduled weekday sessions, not holiday-aware live market status.

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
| 10 | “Claim-level validation maps supported statements to stored source spans and flags unsupported statements for review; the evaluation gate requires citation precision ≥0.95, recall ≥0.90 and zero advice leaks.” | README, `/brief` | `backend/app/briefs/validator.py`; `backend/tests/test_evals.py`; `backend/scripts/run_evals.py` | Supported when the evaluation command passes |
| 11 | “The retained browser gate covers all four editions and `/brief` at desktop, mobile and a 200%-zoom-equivalent width, in light/dark and reduced-motion modes, with no serious/critical axe findings or horizontal overflow.” | README, testing | `frontend/e2e/regional-workspaces.spec.ts` | Supported when `npm run test:e2e` passes |

## Prohibited wording

- “Live open/closed market status” — the clock is schedule-derived and not holiday-aware.
- “Fully local UK/EU/Korea market data” — these editions localise sourced global indicators.
- “Korean or Traditional Chinese source brief” — the English brief is the audited source of record.
- “Trading terminal”, “investment advice” or “buy/sell signal”.
