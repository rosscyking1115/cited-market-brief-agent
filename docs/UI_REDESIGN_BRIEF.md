# UI Redesign Brief — Morning Market Radar (Taiwan consumer edition)

This is a **visual redesign** brief: improve hierarchy, polish, density, and the
data displays. Do **not** change data contracts, copy meaning, or component logic —
only styling, layout, and hierarchy. Follow the *process* in §5.

---

## 1. Product & user

A daily **morning market radar + ETF/fund attribution** tool. The primary user is a
**Taiwan-based finance professional/investor** who opens it every morning before
work to:
1. catch up on the most important **finance/market news** (decision-relevant only), and
2. see how her actively-managed Taiwan ETF (主動摩根台灣鑫收益, code `00401A`) is doing
   **vs the TAIEX (加權指數)** — at **stock** *and* **sector (產業)** level — to inform
   decisions and client conversations.

She is **not** highly technical, reads in **Traditional Chinese**, and values
**clarity, trust, and speed** over flash. She uses both **desktop and phone**.

## 2. Tech & design system (work within these — non-negotiable)

- **Next.js 16 (App Router/RSC) + React 19 + Tailwind v4.** No new UI dependencies
  (no shadcn, no component kit, no GSAP).
- **In-house tokens** in `frontend/app/globals.css` (CSS variables). Keep the variable
  **names**; you may change their **values**. Tokens include: `--color-page/bar/card/
  hairline/elevated`, `--color-neutral-30..90`, semantic `--color-up` (green) /
  `--color-down` (red) / `--color-flag` (amber) / `--color-action` (blue `#2670a9`),
  `--radius-ctl: 4px` / `--radius-card: 8px`, soft shadow tokens, and reader text
  utilities (`th-label`, `reader-body`, `reader-meta`, `reader-heading`).
- **Fonts:** Source Serif (display/headlines), IBM Plex Mono (numbers/data), Inter (body).
- **Themes:** light (default) **and** dark must both work. **Region editions**
  (TW/KR/UK/EU) share components — TW is the focus here but the others must still render.

## 3. Current screens (TW edition, top → bottom)

1. **Header bar** — product name + "TAIWAN MORNING · EVIDENCE-BACKED"; region select; theme toggle; text-size toggle (A / A+ / A++).
2. **市場新聞 (news)** — an AI **今日重點** overview card; tabs (**最多瀏覽 / 1 小時 / 24 小時**); category filter chips (市場 / 半導體 / 宏觀 …); a list of news cards, each: rank number, source chip (BBC/CNBC/MarketWatch/NYT/Guardian), rank-kind chip, category chip, headline (link), 2-line summary, timestamp, source-status, one-line "why".
3. **ETF 歸因分析 (fund tool)** — title + use-case; **input grid** (基金名稱, 基金/ETF 代號, 比較基準, 日期, 來源名稱, 基金當日漲跌幅, 台灣加權指數漲跌幅); **action buttons** (解析持股, 用 TWSE 補全部漲跌幅, 分析差異, 設為每日自動更新, 立即更新); Excel upload + CSV/TSV paste textarea; **解析結果** panel; **analysis result** = 分析結論 sentence + 3 stat tiles (相對表現 / 持股解釋 / 無法解釋殘差) + 3 lists (最大正貢獻 / 最大拖累 / 缺少漲跌幅).
4. **產業配置比較 (sector)** — a table: **產業 | 基金 | 指數 | 差異 | 當日 | 配置效果** + a collapsible editor to set the TAIEX sector weights once.
5. **Footer** — compliance disclaimer (not investment advice).

## 4. Problems to fix ("not perfect")

- **Flat hierarchy** — every section reads at the same weight; there is no clear "look here first."
- **Chip noise** — news cards carry 4–5 tiny chips of similar styling; hard to scan.
- **Form-heaviness** — the fund tool shows 7 inputs + 5 buttons even after it's set up; the everyday state should lead with the *result*, not the setup.
- **Plain tables** — the sector table and the attribution lists are visually undifferentiated; the numbers don't pop or encode direction strongly enough.
- **Weak "today" moment** — the most valuable things (today's market gist + her fund vs the index) aren't visually elevated above the machinery.
- **Mobile** — dense rows/tables need a deliberate small-screen layout.

## 5. Process to follow (from anthropic frontend-design)

1. **Brainstorm a compact token system** for *this* brief: 4–6 named colors, a display+body+mono type pairing, a layout system, and a **single signature element**.
2. **Critique the plan** against this brief. Reject anything that is a default choice you'd make for *any* finance app. In particular: the current light theme uses a **warm cream/bone palette (#F4F1EA) + serif headlines** — frontend-design lists this exact combo as a "default cluster." **Either justify it** (calm, low-stress, document-like daily read for a non-technical user — a legitimate reason) **or propose a more distinctive palette grounded in Taiwan markets/finance.** Make this an explicit, reasoned decision, not an inherited default.
3. **Build** to the revised plan.
4. **Self-critique** with screenshots at 375 / 768 / 1024 / 1440; verify reduced-motion and dark mode.

## 6. The signature element (pick ONE; spend boldness here, keep the rest quiet)

Recommended candidates, in priority order:
- **A "today" lead block** that fuses the AI **今日重點** market gist with **her fund's headline number vs the TAIEX** (e.g. a large, confident relative-return figure + one line of plain-language context). This is the most characteristic thing in her world.
- **The sector allocation comparison** as a distinctive **diverging bar** (ETF weight vs index weight per sector, tinted by today's sector return) — her unique need, and visually ownable.

Choose one as the hero; the other becomes strong support. Everything else (news list, forms) stays disciplined and quiet.

## 7. Direction by section

- **Header** — calmer, smaller; it's chrome, not content. Region/theme/size controls grouped and de-emphasised. Drop the "evidence-backed" tagline weight.
- **News** — collapse the 4–5 chips to **at most two** (source + one tag); make the **headline** the dominant element and the **summary** comfortably readable; tabs and category chips should look like controls, not badges. Consider a compact "today's top finance reads" treatment for the 今日重點 + first items.
- **Fund tool** — **two states**: (a) *configured / everyday* → lead with the latest result (the 3 stats + contributors/drags), setup collapsed behind a "設定 / 更新持股" affordance; (b) *first-time setup* → the inputs/upload. Don't show all 5 buttons at once in the everyday state.
- **Stat tiles** — make 相對表現 the hero stat (big mono number, directional color); 持股解釋 / 殘差 secondary.
- **Contributors / drags / sector table** — turn into scannable rows with strong number alignment, directional color, and small inline weight/return context; the **配置效果** column is the punchline — make it read instantly.
- **Sector comparison** — consider the diverging-bar viz (§6); keep the table as the detailed/secondary view; the TAIEX-weights editor stays tucked away (set-once).
- **Empty / loading / error states** — give them a calm, intentional look (not raw text).

## 8. Acceptance checklist (from ui-ux-pro-max — all must pass)

- [ ] **SVG icons**, never emoji-as-icon.
- [ ] `cursor-pointer` on every clickable; visible **hover** (150–300ms transition) and **focus** states.
- [ ] Light-mode text contrast **≥ 4.5:1**; semantic up/down never color-only (pair with sign/glyph) — WCAG AA.
- [ ] Respect **`prefers-reduced-motion`**; motion is subtle and purposeful (no scroll spectacle).
- [ ] Responsive and verified at **375 / 768 / 1024 / 1440**; tables degrade gracefully on mobile.
- [ ] **Finance tone:** no neon, no AI purple/pink gradients, no playful/brutalist styling. Trust + clarity.
- [ ] Type scale **12 / 14 / 16 / 20 / 24 / 32**; **8pt** spacing grid; radii 4/8px.

## 9. Deliverables

- Updated **`globals.css` token values** + component styling (Tailwind classes), light **and** dark.
- A short **rationale** for the palette, type pairing, and chosen signature element (per §5.2).
- Before/after **screenshots** at the four breakpoints.
- No changes to data fetching, props, copy meaning, or compliance text.
