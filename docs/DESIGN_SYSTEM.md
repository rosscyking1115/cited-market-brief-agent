# Cited Market Brief Agent Design System

Derived from Salt — JPMorgan Chase's open-source design system (saltdesignsystem.com) — using token values from the published `@salt-ds/theme` package, adapted for a data-dense research product. Implemented in `frontend/app/globals.css` (Tailwind v4 `@theme`).

## Tokens

### Color — brand and action

| Token | Value | Use |
|---|---|---|
| `navy-700` | `#00477B` | Brand moments, wordmark, header accents |
| `blue-500` | `#2670A9` | Primary actions, links (≥4.5:1 with white) |
| `blue-600` | `#155C93` | Action hover |
| `blue-900` | `#232F38` | Navy chrome surfaces (sidebar) — chrome only, no semantic colors on it |

### Color — surfaces and neutrals

Dark (default): page `#161616`, app bar `#242526`, card `#2A2C2F`, hairline `#2F3136`, elevated `#3B3F46`.
Light: page `#FFFFFF`, subtle `#E0E4E9`, hairline `#D9DDE3`, border `#CED2D9`, disabled `#B4B7BE`, muted text `#84878E`, ink `#161616`.

### Color — semantic (market direction, validation status)

| Meaning | Light mode | Dark mode | Rule |
|---|---|---|---|
| Up / supported | `#24874B` | `#309C5A` | Always pair with `▲` or `+` — never color alone (WCAG 1.4.1) |
| Down / failed | `#E32B16` | `#ED412A` | Always pair with `▼` or `−` |
| Flagged / needs review | `#D65513` | `#EA7319` | Amber claim chips, caution states |

Render P/L and validation columns on charcoal surfaces (`#161616`–`#2A2C2F`) or white — 400-level semantics fail contrast on navy.

## Typography

| Role | Face | Notes |
|---|---|---|
| UI, body, data | **Inter** (variable) | Enable `tnum` + `cv05`; tabular figures mandatory in tables |
| Editorial brief headlines | **Source Serif 4** | Research-memo gravitas (open stand-in for JPM's serif) |
| Tickers, CIKs, accessions, timestamps | **IBM Plex Mono** | Identifier hygiene |

Scale (medium density): display 32/40, h1 24, h2 20, h3 16, h4 14, body 13–14, label 12, notation 11. Weights 400/500/600. ALL-CAPS only for labels/buttons. Line-height ≈1.3.

## Density and spacing

Salt density model: base unit 8px (medium, app default), 4px (high — evidence-ledger grid). Container padding L/M/S = 24/16/8px. Header rhythm: 24px below h1, 16px below h2, 8px below h3.

## Shape and elevation

Radii: 0 tables/cells, 4px inputs/buttons/tags, 8px cards/popovers, 12px modals. Dark mode: prefer 1px borders over shadows. Light: sm `0 1px 2px rgb(0 0 0/.06)`, md `0 2px 8px rgb(0 0 0/.10)`, lg `0 8px 24px rgb(0 0 0/.14)`.

## Data tables

Right-aligned numerals with `font-variant-numeric: tabular-nums`; text left-aligned. Ruled 1px hairlines, **no zebra** at high density. Rows 32px (28px compact). Sticky headers: 11px, uppercase, letter-spaced, muted. Negative values signed and colored (`−1.24%`), deltas get `▲▼` glyphs. Mono face for identifiers.

## Components and charts

Tailwind CSS v4 + shadcn/ui (vendored into repo — audit-friendly, no lock-in). Tables: TanStack Table v8; AG Grid Community only if virtualized 10k-row grids become necessary (Salt ships an AG Grid theme — JPM-aligned). Charts: TradingView lightweight-charts v5 for price/series panes (~45KB canvas; **Apache-2.0 with attribution requirement — `attributionLogo: true`, flag to legal**); Recharts 3.x (MIT) for sparklines and macro deltas.

## Performance budgets (CI-enforced)

- Core Web Vitals p75: **LCP ≤ 2.5s** (2.0s internal stretch), **INP ≤ 200ms**, **CLS ≤ 0.1**
- Initial route JS ≤ **200KB gzipped**; shared chunk ≤ 120KB; charts lazy-loaded per panel
- Fonts ≤ 100KB woff2, self-hosted via `next/font`, `display: swap` + metric fallbacks
- TTFB < 500ms for server-rendered brief headline (LCP element)

Techniques: RSC-first (client components only for editing/approval/charts); Next 16 Cache Components — `use cache` + `cacheTag` per watchlist-run, invalidate on regeneration; Suspense skeletons matching exact final layout (CLS≈0); streamed brief generation section-by-section, citation chips appear as each claim validates; fixed-height claim rows while streaming; optimistic UI on approve/edit/feedback.

## Accessibility (WCAG 2.2 AA)

Text 4.5:1 (3:1 ≥24px or 18.66px bold); non-text UI 3:1. Direction never color-only — glyphs mandatory. 2.4.11 Focus Not Obscured: sticky headers must not hide focused rows. 2.5.8 Target Size: ≥24×24px for dense-table icon buttons. Visible 2px focus ring (`#2670A9` light / `#EA7319` dark). `<th scope>` + captions on data tables; chart text alternatives; respect `prefers-reduced-motion`.
