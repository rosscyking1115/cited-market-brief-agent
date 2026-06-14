# Taiwan Morning Market Radar Plan

Current as of 2026-06-14. This plan captures family-pilot feedback from a
Traditional Chinese reader who wants one morning page instead of opening BBC,
StockQ, Yahoo Finance, LSEG/Workspace-style news views, exchange pages, and
market-data sites.

## Goal

Make the product genuinely useful for a Taiwan-time morning reader:

> In one page, answer: what were the most important global news stories, what
> changed in major markets, what opens next in Asia, and what should I observe
> today?

The page must remain factual, cited, source-labeled, and non-advisory. It may
say `需要觀察什麼`, `可能影響`, and `風險`, but not `可以買`, `推薦買進`, or
personalized portfolio guidance.

## Feedback To Product Requirements

| Feedback | Requirement |
|---|---|
| `閱讀量最大的新聞 within 1 hour and 24 hour, start from BBC` | Add a `Popular News` module with 1h and 24h tabs. Use official/licensed popularity endpoints only. If a publisher does not expose readership ranking, label it as `latest` or `editorial/trending`, not `most read`. |
| `指數 not all investor want to see them all, maybe top 20` | Add a default Top 20 cash-equity index list, with pin/hide/reorder later. Keep futures, FX, rates, oil/gold, and volatility in a separate overnight-risk rail. |
| `ensure all sources and data are within policy and regulation` | Every data row must carry source, timestamp, delay/realtime/EOD status, license tier, and display rights note. No scraping behind logins/paywalls. No redistributing provider text/tables unless explicitly licensed. |
| Screenshots show TOPNEWS filters: content type, 1h/24h, most read/latest, source filters | Add compact controls: time window, ranking mode, source, region/topic, content type. Keep list dense but readable on mobile. |

## Popular News Module

### UX

Default placement: under the 3-sentence morning summary and before company
details.

Tabs:

- `1 小時`
- `24 小時`
- `重要 + 最新`
- Later: `BBC`, `市場`, `台灣`, `亞洲`, `公司`, `商品`

Each item:

- Rank
- Headline in Traditional Chinese
- Original headline/source link
- Source name
- Published time and retrieved time
- Why it matters in one sentence
- Category: `宏觀`, `市場`, `公司`, `商品`, `地緣政治`, `台灣`
- Source status: `official_api`, `rss`, `licensed`, `manual_reference`, or `not_allowed`

### Source Policy

BBC is a good editorial starting point, but do not scrape BBC `Most read` pages
unless BBC provides an official API/feed or written permission. Use BBC RSS or
public article links only for headline discovery if terms allow. If no official
readership endpoint is available, the label must be `BBC 最新新聞` or
`BBC 編輯焦點`, not `BBC 閱讀最多`.

Safer source options:

- Licensed terminal/news provider: LSEG/Reuters or equivalent, if contract
  permits display and redistribution.
- NYT Most Popular API for true most-viewed/most-shared style signals, subject
  to NYT developer terms.
- GDELT for open web discovery and clustering; not true readership.
- NewsAPI paid plan for headline/link discovery only; its developer plan is not
  for staging/production and terms restrict reproducing/republishing
  copyrighted content.
- Guardian Open Platform for Guardian content under its API terms.

Never:

- Copy full article text.
- Show provider usage statistics unless the provider explicitly allows it.
- Scrape paywalled/logged-in systems.
- Call a custom ranking `most read` unless it is actually readership data.

### Phases

Phase N1 - Contract and UI shell:

- Add `popular_news` to `/market-radar`.
- Show 1h/24h tabs with source-status labels.
- Start with policy-safe placeholder/news-discovery rows.

Phase N2 - BBC/latest discovery:

- Add BBC RSS/headline ingestion if terms are acceptable.
- Label as `latest`, not `most read`, unless an official popularity source is
  approved.
- Filter BBC RSS items by publication time for `1 小時` and `24 小時` freshness
  windows; if timestamps are missing or outside the window, do not include them
  in that window.

Phase N3 - True popularity:

- Add licensed `most viewed/most read` provider such as NYT Most Popular or
  LSEG/Reuters if contract permits.
- Store source, rights, retrieved_at, and provider rank.

Phase N4 - Ranking engine:

- Cluster duplicate headlines.
- Score by source trust, freshness, market relevance, entity/ticker overlap,
  and Taiwan-morning relevance.
- Clearly label as `市場雷達排序`, not readership.

## Top 20 Indices Module

Default Top 20 should be cash-equity indices only:

1. S&P 500
2. Nasdaq-100
3. Dow Jones Industrial Average
4. Russell 2000
5. PHLX Semiconductor Index
6. STOXX Europe 600
7. Euro Stoxx 50
8. DAX 40
9. FTSE 100
10. Nikkei 225
11. TOPIX
12. KOSPI
13. KOSDAQ
14. TAIEX
15. FTSE TWSE Taiwan 50
16. TPEx / Taiwan OTC Index
17. Hang Seng Index
18. Hang Seng Tech
19. CSI 300
20. Shanghai Composite

Separate overnight-risk rail:

- S&P 500 futures
- Nasdaq-100 futures
- Nikkei futures
- Hang Seng futures
- TAIFEX TAIEX futures
- VIX
- USD/TWD
- USD/JPY
- USD/CNY via FRED where acceptable; CNH requires a market-data feed
- Broad U.S. dollar index via FRED where acceptable; literal ICE DXY requires a market-data feed
- WTI/Brent
- Gold
- US 10Y

Keep this separate from `Top 20 指數` because the risk rail mixes futures,
volatility, FX, commodities, and rates. These instruments may trade in different
hours and have different licensing/display rules from cash equity indices.

### Phases

Phase I1 - Editorial default:

- Add `top_indices` to `/market-radar`.
- Show top 20 as grouped regions with source/delay placeholders.

Phase I2 - Personalization:

- Add pin/hide/reorder.
- Presets: `台股開盤前`, `半導體供應鏈`, `全球 ETF 投資人`,
  `中國/香港觀察`, `匯率與利率`.

Phase I3 - Data provider:

- Internal beta: Twelve Data business tier or Alpha Vantage only if rights fit.
- Taiwan: TWSE/TIP/TAIFEX official or contracted vendors.
- Public/professional: LSEG/direct exchange contracts with display rights.

Phase I4 - Compliance hardening:

- Store per-symbol license metadata.
- Show realtime/delayed/EOD label.
- Confirm caching, redistribution, and derived-data rights before alerts or
  saved history.

## Immediate Build Order

1. Add data contract: `popular_news`, `top_indices`, `overnight_risk`.
2. Render compact rails in the morning dashboard.
3. Keep placeholder labels honest: `planned`, `latest`, `licensed required`.
4. Add source policy table before ingesting BBC/Yahoo/StockQ/LSEG-like data.
5. Wire one compliant source at a time.

## Source Policy Registry

Code should keep a source-policy registry for every feed. At minimum, each
policy records:

- display name
- source status: `official_api`, `rss`, `licensed`, `planned`, or
  `manual_reference`
- allowed label, such as `Latest from BBC`
- forbidden label, such as `BBC Most Read`
- rights note shown or available in the UI

Initial policies:

- `bbc_rss`: latest-headline RSS only; not readership data.
- `gdelt_doc`: trending/most-covered discovery; not readership data.
