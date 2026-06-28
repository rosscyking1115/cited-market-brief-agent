# Fund Attribution Plan

Current as of 2026-06-20.

## Goal

Answer the daily after-close question:

> Why did this fund or ETF perform differently from its benchmark today?

First use case:

- Fund: `主動摩根台灣鑫收益ETF`
- Benchmark: `台灣加權指數`
- Timing: after Taiwan market close

## First Version

Manual-first, policy-safe workflow:

1. User downloads JPM holdings from the official fund page.
2. User uploads the holdings file to the app.
3. App gets Taiwan after-close stock prices from official/permitted sources.
4. App calculates holding contribution: `weight % * stock return %`.
5. App compares ETF return vs. TAIEX return.
6. App explains:
   - fund return
   - benchmark return
   - active return
   - top positive contributors
   - top drags
   - residual/unexplained amount

## Automation Policy

- JPM holdings: manual upload first. Automate only after confirming terms and a
  stable machine-access path.
- TWSE prices: after-close only; use official public data where allowed, with
  retrieval timestamp and cache.
- TAIEX benchmark: use official/permitted source; confirm public display rights
  before broader release.
- Intraday attribution: do not build without licensed market-data feeds.

## Regional Expansion

The same attribution model can support:

- UK funds/ETFs vs. FTSE 100, FTSE 250, or FTSE All-Share.
- US funds/ETFs vs. S&P 500, Nasdaq-100, or sector benchmarks.
- Europe UCITS funds/ETFs vs. STOXX Europe 600, Euro Stoxx 50, or country indices.

For every region, the required checks are:

- official/permitted holdings source
- official/permitted security price source
- benchmark display/redistribution rights
- cache and rate limits
- non-advice language
