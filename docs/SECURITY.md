# Cited Market Brief Agent Security Posture

Engineering reference for the controls in `docs/PRODUCTION_PLAN.md` §9. Status legend: ✅ implemented · 🔶 implemented, needs production wiring · ⏳ pending.

## Control status vs launch no-go gates

| Gate | Status | Where |
|---|---|---|
| Citation validator (claims → stored spans) | ✅ | `app/briefs/validator.py`, CI eval gate |
| Advice-boundary guardrails | ✅ | `app/briefs/guardrails.py` (recommendation, target price, allocation, performance promises, prompt manipulation, URL exfiltration) |
| Audit log: prompts, sources, outputs, exports, approvals | ✅ | `app/services/audit.py` — append-only; model/provider/prompt version on LLM events |
| EDGAR fair access (UA + ≤10 req/s) | ✅ | `app/connectors/sec_edgar.py` — refuses to run without declared UA |
| Export review flow + watermark | ✅ | approval-gated; rejected sections never export; `INTERNAL RESEARCH DRAFT` until approved |
| EU AI Act Art. 50 machine-readable marking | ✅ | manifest `ai_generated`, PDF/PPTX/XLSX metadata + visible disclosure |
| Output sanitization (XSS) | ✅ | `html_report.py` escapes all dynamic text; zero external resources |
| Sandboxed PDF renderer | ✅ | `app/exports/pdf.py` — JavaScript disabled, all network aborted |
| XLSX formula-injection escaping | ✅ | `xlsx_export.py` `_safe_cell` (`= + - @ \t \r`) |
| Cross-tenant isolation (RLS) | 🔶 | `app/db/rls.py` + `scripts/apply_rls.py`; coverage enforced by `tests/test_rls_coverage.py`; **live cross-tenant leakage test against staging Postgres pending** |
| AuthN: OIDC + PKCE, MFA | 🔶 | JWT/JWKS validation in `app/core/security.py` (`AUTH_REQUIRED=true`); IdP setup (MFA default-on, WebAuthn for admins, SCIM ≤24h offboarding) pending |
| Rate + cost limits | 🔶 | API sliding-window limiter (`app/core/middleware.py`); per-tenant LLM cost ceilings in gateway config pending |
| Dependency scanning + SBOM | ✅ | CI `security` job: pip-audit, npm audit, CycloneDX SBOM artifact |
| Hash-pinned deps / SHA-pinned Actions / signed images | ⏳ | before external launch |
| SSRF egress controls (IR/RSS fetchers) | ⏳ | required before enabling customer-configured URLs (MVP sources are EDGAR/FRED allowlist only — SSRF surface currently closed) |
| Privacy notice, DPA, DSAR workflow | ⏳ | counsel review required |
| External pen test + red team | ⏳ | scheduled pre-launch; internal suite: `app/evals/fixtures.py` injection cases |
| Backups + restore test | 🔶 | `scripts/backup_restore_test.sh` (local/staging); RDS snapshot policy pending |

## Tenant isolation (RLS)

```bash
python scripts/apply_rls.py --apply
```

Every table with `org_id` (plus `organizations` keyed by `id`) gets `ENABLE` + `FORCE ROW LEVEL SECURITY` and a policy reading the `app.current_org_id` GUC. Unset GUC ⇒ zero rows (fail closed). `get_db` sets the GUC from the authenticated token's `org_id` claim. Vector + FTS queries inherit policies (OWASP LLM08). CI fails if a new org-scoped table lacks coverage.

## Authentication

Set `AUTH_REQUIRED=true`, `OIDC_ISSUER`, `OIDC_AUDIENCE`, `OIDC_JWKS_URL`. The API validates RS256/ES256 bearer JWTs against the IdP JWKS, requires `exp/iat/sub`, and takes the tenant from the `org_id` claim. PKCE, MFA, SSO, and SCIM deprovisioning are IdP responsibilities — document the chosen IdP config before launch. `/healthz` stays public.

## LLM security model (OWASP LLM Top 10 2025)

Untrusted source text is delimited in prompts and never executed; citations are validated application-side (LLM01/09). Guardrails quarantine advice, prompt-manipulation artifacts, and embedded URLs even when perfectly cited (defense in depth against indirect injection and markdown-image exfiltration). Non-government sources land in a quarantine trust tier before promotion (LLM04). Output-side PII/secret scanning: ⏳ Phase 5 follow-up. Rate/cost ceilings per tenant (LLM10).

## Incident response (draft)

1. **Detect/Report** — alerting on audit-log anomalies, rate-limit spikes, CI security failures; security@ inbox.
2. **Triage** — severity: SEV1 cross-tenant data exposure / credential compromise · SEV2 injection bypassing guardrails into an exported brief · SEV3 dependency CVE in prod · SEV4 other. Incident commander assigned on SEV1–2.
3. **Contain** — revoke tokens (IdP), disable affected tenant exports, rotate secrets (Secrets Manager), block source in allowlist if poisoning suspected.
4. **Eradicate/Recover** — patch, re-run eval + red-team suite, restore from backup if integrity is in question (see runbook below).
5. **Notify** — counsel determines regulatory notification duties (GDPR 72h, state breach laws, customer DPAs).
6. **Post-mortem** — blameless, within 5 business days; new eval/red-team case for every guardrail bypass.

## Backup / restore runbook

Local/staging: `bash scripts/backup_restore_test.sh` — dumps the database, restores into a scratch database, and compares per-table row counts. Production: RDS automated snapshots (≥7 days PITR) + quarterly restore drill into an isolated VPC; record evidence in the audit folder for SOC 2.

## Red-team suite

`python scripts/run_evals.py` runs the injection cases (advice-laced filing, system-prompt-leak + markdown-image exfiltration) on every CI push. Gate: zero forbidden strings in supported claims; quarantine must trigger. Extend `app/evals/fixtures.py` with a new case for every bypass found — bypasses become permanent regression tests.
