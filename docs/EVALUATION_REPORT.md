# Cited Market Brief Agent — Plan Evaluation Report

Evaluation of `PRODUCTION_DEVELOPMENT_PLAN.md` (dated 2026-06-05), performed 2026-06-10 by four parallel review agents: currency/credibility, tech stack, security/compliance, and design/performance. This report drove the revisions in `PRODUCTION_PLAN.md` (v2).

## Overall Verdict

The plan is fundamentally sound, credible, and close to current. It required four classes of correction before build start: reframing the competitive wedge around audit artifacts rather than citations alone, de-engineering the MVP stack, closing five architecture-level security gaps, and adopting a concrete JPM-grade design system with enforceable performance budgets. All corrections are incorporated in `PRODUCTION_PLAN.md` v2.

---

## 1. Currency and Credibility — verdict: largely current, two substantive gaps

### Confirmed

- SEC EDGAR fair access unchanged: max 10 requests/second, declared User-Agent required. Plan assumptions hold. (sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
- EDGAR APIs (data.sec.gov) still keyless and free; FRED API overview/terms live and unchanged — API key required, attribution and third-party copyright restrictions apply to brief exports.
- FINRA 2026 Annual Regulatory Oversight Report GenAI section is live and maps almost one-to-one to the plan's audit-log and review features — strong validation of the no-go gates.
- NIST AI RMF 1.0 and FINRA 2210 anchors unchanged.

### Corrections applied

- **Competitor framing was stale.** All four incumbents moved past "AI search/summaries" to agentic AI: Bloomberg ASKB (agentic interface with transparent attribution, Feb 2026), FactSet AI for Banking with Finster AI multi-agent research (Mar 2026), LSEG×Microsoft MCP server + Copilot agents (Oct 2025), AlphaSense Deep Research agent (June 2025) and agentic Generative Search (Jan 2026). Cited AI research alone is commoditized (also Fintool, Rogo at ~$2B valuation, Hebbia, Brightwave). **The defensible wedge is narrower and sharper: deterministic claim→span validation in the application layer, an exportable JSON evidence ledger/citation manifest, FINRA-aligned audit trails, and change detection with data-vintage awareness (ALFRED). None of the incumbents sell an audit artifact.**
- **Stale URLs fixed**: EDGAR fair-access page moved; SEC IA Marketing guide moved; OWASP LLM Top 10 anchor pointed to the legacy 2023 v1.1 page — current 2025 list lives at genai.owasp.org/llm-top-10/.
- **EU AI Act developments**: the May 7, 2026 "AI omnibus" agreement deferred high-risk (Annex III) rules to Dec 2027/Aug 2028, but **Article 50 transparency applies Aug 2, 2026** — see Security section.
- **SEC posture (new)**: predictive-data-analytics proposal withdrawn June 2025; Dec 2025 Investor Advisory Committee AI-disclosure recommendations; principles-based stance under Chair Atkins. Added FINRA Reg Notice 24-09 and NIST GenAI Profile (AI 600-1) as anchors.

---

## 2. Tech Stack — verdict: sound and current, three over-engineered choices

No proposed component is deprecated. Corrections target MVP right-sizing (single dev + agents), one supply-chain caution, and removal of undecided "or"s that cause agent thrash.

### Decisions (replacing "X or Y" ambiguity)

| Component | Decision | Version target | Rationale |
|---|---|---|---|
| Frontend | Next.js (keep) | 16.2.x LTS, React 19.2.x, TS 5.x | App Router + RSC stable. Note: `middleware.ts` → `proxy.ts` in Next 16; Turbopack is default build |
| API | FastAPI (keep) | Python 3.13, FastAPI 0.136.x, Pydantic 2.13 | 3.13 is the max-compatibility choice for a dependency-heavy RAG stack |
| ORM | **SQLAlchemy 2.0 + Alembic** (decided, drop SQLModel option) | 2.0.x | Claims/citations/audit domain is complex; use the battle-tested layer directly |
| Database | Postgres + pgvector (keep) | Postgres 18.x, **pgvector ≥0.8.2** | 0.8.2 fixes CVE-2026-3172 (HNSW parallel-build overflow) — pin it. HNSW + halfvec |
| Search | **OpenSearch dropped at MVP** | — | Postgres FTS + pgvector + RRF fusion covers hybrid retrieval at MVP corpus size. Dual indexing doubled the write path and added sync-drift risk. OpenSearch Serverless was a cost trap (~$350/mo idle 2-OCU floor). Re-introduce only when relevance metrics prove FTS insufficient |
| Workflows | **Hatchet replaces self-hosted Temporal** | Hatchet (MIT, Postgres-backed) | Self-hosted Temporal is K8s-grade ops burden for one dev. Fallback: Temporal Cloud Essentials ($100/mo) if durable execution proves non-negotiable |
| LLM gateway | LiteLLM **in library mode, hash-pinned** | ≥1.88.1 | March 2026 PyPI supply-chain attack compromised 1.82.7/1.82.8 — pin + scan. No separate proxy service at MVP. Two providers (Anthropic + OpenAI), not four |
| Parsing | **edgartools (EDGAR) + Docling (PDFs)** (decided, drop Unstructured option) | latest | EDGAR filings are HTML/XBRL — edgartools is EDGAR-native and typed; Docling (Linux Foundation, Granite-Docling) is the better-maintained OSS parser for IR PDFs, ~97.9% table-cell accuracy |
| PDF render | Playwright (decided, drop WeasyPrint option) | latest | Brief canvas is HTML/JS; WeasyPrint can't execute JS, 48–75x slower without warm mode |
| PPTX/XLSX | python-pptx (flagged low-maintenance, acceptable) + openpyxl 3.1.5 | 1.0.x / 3.1.5 | Avoids a Node sidecar; openpyxl actively maintained |
| Cache/queue | **Valkey** (BSD-3) over Redis (AGPL tri-license) | Valkey 8.x | ElastiCache default, ~20% cheaper |
| LLM observability | **Langfuse** (decided over LangSmith) | latest | MIT, OTel-native, framework-agnostic. Watch: ClickHouse acquired Langfuse Jan 2026. OTel GenAI semconv still Development status — instrument behind own wrapper |
| Deploy | AWS ECS/Fargate + RDS + S3 (keep); GitHub Actions; Terraform/OpenTofu | — | App Runner in maintenance mode — avoid. No OpenSearch Serverless |

### Over-engineering removed

Dual chunk indexing (pgvector + OpenSearch), self-hosted Temporal, LiteLLM as a deployed proxy, four configurable LLM providers, and two undecided parser/ORM "or"s.

---

## 3. Security and Compliance — verdict: conditionally adequate, not launch-ready as written

### Adequate as written

Advice-boundary + review flow (aligns with FINRA 2210 / SEC Marketing Rule), source strategy (allowlists, EDGAR fair-access UA), privacy baseline (DPA, DSAR, retention, no-training clause), SOC 2 trajectory, and coverage of OWASP LLM01/05/06/09/10.

### Critical gaps (fixes incorporated into v2 plan)

1. **Tenant isolation had no enforcement pattern.** Fix: Postgres Row-Level Security on every org-scoped table keyed by `org_id` session variable; S3 prefix-per-tenant with IAM conditions; never query-side filters alone for vector search (OWASP LLM08); cross-tenant leakage test in CI.
2. **SSRF in IR/RSS fetchers.** Workers fetch customer-configured URLs. Fix: fetch-time allowlist; DNS resolution rejecting private/link-local ranges (incl. 169.254.169.254) with rebinding protection; egress proxy in isolated subnet; IMDSv2-only; capped redirects re-validated per hop.
3. **XSS + export injection.** LLM output → HTML → PDF is an XSS and renderer-SSRF vector; XLSX raw-data tabs invite formula injection. Fix: server-side allowlist sanitizer (nh3) + DOMPurify client-side; Playwright PDF rendering sandboxed with JS and network disabled; strict nonce-based CSP on the Next.js app; escape `= + - @` cell prefixes in openpyxl; strip remote-image exfiltration channels from rendered briefs.
4. **OWASP LLM list was the 2023 version.** Mapped to 2025 IDs; added controls for LLM07 system-prompt leakage, LLM08 vector/embedding weaknesses, LLM04 RAG-corpus poisoning (quarantine tier for non-government sources), LLM02 output-side PII/secret filtering. Prompt-injection defense made architectural (privileged/quarantined model separation, spotlighting untrusted source text), not test-only.
5. **No ASVS target.** Adopted ASVS 5.0 (May 2025): Level 2 across the app; Level 3 for authn, session, authorization/multi-tenancy, audit-logging chapters.
6. **Authn underspecified.** OIDC Authorization Code + PKCE; MFA default-on for all users (phishing-resistant WebAuthn for admins); SCIM deprovisioning; hashed per-tenant API keys; HMAC-signed webhooks; short-expiry signed export URLs.
7. **Supply chain was scan-only.** Lockfile + hash-pinned deps, SHA-pinned GitHub Actions, CycloneDX SBOM per release, signed images (cosign).

### Regulatory updates

- **EU AI Act Art. 50 applies Aug 2, 2026**: AI-generated text must carry machine-readable marking (systems on market before that date get until Dec 2, 2026). Art. 50(4) deployer disclosure is exempted where human review + editorial responsibility exist — the approval flow is the compliance asset; embed provenance metadata in PDF/PPTX/JSON exports.
- **FINRA 2026**: Rule 2210 applies fully to AI-generated communications; expects pre-deployment compliance assessment, GenAI governance in WSPs, hallucination controls, books-and-records retention of AI outputs.
- **SEC**: Marketing Rule FAQs updated Jan 2026; Dec 2025 Risk Alert on testimonials/ratings. Also block extracted/hypothetical performance presentation in briefs, not just recommendations.

### No-go gate additions (now in v2 plan)

Cross-tenant isolation test passes; SSRF egress controls verified; sanitization + CSP + XLSX formula-escaping verified with sandboxed PDF renderer; MFA enforced with OIDC+PKCE and 24h offboarding; EU AI Act Art. 50 marking in exports (if EU users); SBOM per release with pinned deps/actions; external pen test + indirect prompt-injection/RAG-poisoning red-team pass; SOC 2 Type I evidence set (risk assessment, policies, access review, vendor register, change-management, monitoring).

---

## 4. Design and Loading Efficiency — verdict: adopted Salt-derived system

Key finding: **JP Morgan's actual open-source design system is Salt** (saltdesignsystem.com, by JPMorgan Chase). The design system below uses token values extracted from the published `@salt-ds/theme` package — this palette is literally what JPM ships. Full spec in `docs/DESIGN_SYSTEM.md`; implemented in `frontend/app/globals.css`.

- **Palette**: institutional navy #00477B; action blue #2670A9 (≥4.5:1 with white); dark surfaces #161616/#242526/#2A2C2F; semantic up/down #24874B/#E32B16 (light) and #309C5A/#ED412A (dark), always paired with ▲/▼ glyphs and signs (never color-only, WCAG 1.4.1); amber accent #EA7319 for flagged claims.
- **Typography**: Inter (UI/data, `tabular-nums`), Source Serif 4 (editorial brief headlines — research-memo gravitas), IBM Plex Mono (tickers, CIKs, accession numbers, timestamps). Body 13–14px, medium density default, high density for the evidence-ledger grid.
- **Tables**: right-aligned tabular numerals, ruled 1px hairlines (no zebra at high density), 32px rows, sticky 11px uppercase headers, signed deltas.
- **Component stack**: Tailwind CSS v4 + shadcn/ui (vendored, audit-friendly) on Next 16/React 19; TanStack Table v8; charts: TradingView lightweight-charts v5 (~45KB, Apache-2.0 — **requires attribution; flag to legal**) + Recharts 3.x for sparklines.
- **Performance budgets (CI-enforced)**: Core Web Vitals p75 LCP ≤2.5s / INP ≤200ms / CLS ≤0.1; initial route JS ≤200KB gzipped; fonts ≤100KB woff2 self-hosted via next/font; RSC-first with Cache Components (`use cache`, tag briefs by watchlist-run); Suspense skeletons matching final layout; AI content streamed section-by-section with per-claim citation chips appearing as validated; fixed-height claim rows to prevent layout shift while streaming.
- **Accessibility**: WCAG 2.2 AA including Focus Not Obscured (sticky headers) and ≥24px target size for dense-table icon buttons; 2px focus ring; `prefers-reduced-motion`.

---

## Sources

Competitive: professional.bloomberg.com/products/bloomberg-terminal/ai/ · investor.factset.com (AI for Banking, Mar 2026) · lseg.com (Microsoft MCP, Oct 2025) · alpha-sense.com (Deep Research). Data: sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data · sec.gov/search-filings/edgar-application-programming-interfaces · fred.stlouisfed.org/docs/api/. Stack: nextjs.org/blog/next-16 · postgresql.org (pgvector 0.8.2) · github.com/hatchet-dev/hatchet · github.com/dgunning/edgartools · ibm.com (Granite-Docling). Security: genai.owasp.org/llm-top-10/ · github.com/OWASP/ASVS (5.0.0) · artificialintelligenceact.eu/article/50/ · finra.org (2026 GenAI oversight) · sec.gov (Marketing FAQ). Design: saltdesignsystem.com · web.dev/articles/vitals · w3.org/TR/WCAG22/.
