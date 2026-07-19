# Cited Market Brief Agent design system

The interface is Salt-derived: dense, restrained and built for scan-and-review work. It is implemented directly with Tailwind v4 and CSS variables in `frontend/app/globals.css`; no shadcn, TanStack Table, TradingView or chart package is installed.

## Foundations

- **Type:** Inter for interface/body text, Source Serif 4 for editorial headings and IBM Plex Mono for identifiers and times. Fonts are loaded through `next/font`.
- **Density:** 8px base rhythm, with 4px controls and compact evidence rows where the information benefits from it.
- **Shape:** 4px controls, 8px cards and 12px native dialogs. Cards use restrained borders and short shadows rather than decorative depth.
- **Colour:** cool porcelain surfaces in light mode and blue-charcoal surfaces in dark mode. The action colour is harbour blue. Quiet text tokens still meet 4.5:1 on their intended surfaces.
- **Market direction:** Western editions use green for up and red for down. Taiwan reverses that convention. Every direction also carries a sign, label or arrow, so colour is never the only signal.

The theme-specific action foreground is a separate token: white on the darker light-theme action and dark ink on the brighter dark-theme action. This avoids assuming one foreground works on both.

## Route hierarchy

- `/` is the region-aware Morning Market Radar. Its header contains the edition control.
- `/brief` is the English source-of-record company research workspace. It has no edition control; Traditional Chinese and Korean appear only inside the brief reader as labelled aids.
- `WorkspaceHeader` owns route navigation and shared theme/text-size controls.

## Interaction and accessibility

- A skip link targets `#main-content` on both routes.
- Edition and onboarding flows use native `<dialog>` elements. The edition chooser cannot be dismissed without a choice and wraps keyboard focus explicitly.
- Translation state uses a polite live region.
- Focus uses a visible 2px action-colour outline with a 2px offset.
- All motion has a `prefers-reduced-motion` fallback in the global stylesheet.
- Controls remain keyboard-operable, content avoids horizontal overflow, and the retained Playwright/axe matrix covers all four radar editions plus `/brief`.

## Radar-specific rules

- Structural copy, status labels, categories, disclaimers and control labels come from the typed `tw`/`ko`/`en` catalogue in `frontend/lib/radar-i18n.ts`.
- Product names and linked source headlines can remain in their original language. An unavailable Korean/Traditional-Chinese translation receives an explicit original-language label.
- Market times are formatted from machine-readable sessions into the selected edition’s IANA time zone. Status is always labelled as scheduled and paired with the exchange-holiday caveat.
- Taiwan-only FX and ETF attribution do not appear in Korea, UK or EU.

## Evidence-workspace rules

- English is the audited source of record and the default reader mode.
- Citation chips, support state, source span, document metadata and review state remain visible together.
- Translations do not replace the underlying English review or approval state.
- Export controls stay disabled in demo mode rather than presenting a dead action as available.

## Verification budgets

- WCAG 2.2 AA contrast: 4.5:1 for normal text and 3:1 for large text/non-text controls.
- No critical or serious axe findings on retained routes/themes.
- No horizontal overflow at desktop, mobile or the 720px 200%-zoom-equivalent viewport.
- Production TypeScript build and browser matrix must pass before screenshots are recaptured.
