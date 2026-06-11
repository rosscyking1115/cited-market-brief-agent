# Deployment & Mobile Roadmap

Companion to `docs/PRODUCTION_PLAN.md` §4 (stack) and `docs/SECURITY.md` (gates). Status: everything currently runs locally; this is the path out.

## 0. Where we are

All seven phases are built and tested locally. "Local" means: Postgres/Valkey/MinIO in Docker, FastAPI + Next.js on your machine, real data from SEC EDGAR and FRED. Nothing is deployed; no one but you can reach it. That is correct for the pilot stage — the pilot user can sit next to the machine or use it over a tunnel.

## 1. Testing it today (local)

Prereqs: Docker Desktop, Python 3.13, Node 22.

```powershell
cd "C:\Files\App\Cited Market Brief Agent"
copy .env.example .env        # then edit:
#   SEC_USER_AGENT  = "Cited Market Brief Agent pilot your-email@example.com"   (REQUIRED)
#   FRED_API_KEY    = free key from fred.stlouisfed.org/docs/api/api_key.html (optional)
#   ANTHROPIC_API_KEY = optional — without it briefs are extractive but citation-perfect

docker compose up -d db valkey minio

cd backend
python -m venv .venv ; .venv\Scripts\activate
pip install -e ".[dev]"
python scripts/bootstrap_db.py
python scripts/apply_rls.py --apply

# Smoke test (5 min, hits live EDGAR/FRED, fair-access throttled):
python scripts/demo_brief.py          # → .data/exports/brief_<id>.md + manifest

# Full pilot loop:
python scripts/seed_watchlists.py
python scripts/run_scheduled.py --force
uvicorn app.main:app --reload         # http://localhost:8000/docs

# Second terminal:
cd frontend ; npm install ; npm run dev   # http://localhost:3000 → "● LIVE"
```

Then the daily ritual in `pilot/PILOT_RUNBOOK.md`: review sections, click claims to evidence, approve, export. Quality gates: `pytest -q` and `python scripts/run_evals.py`.

To let a remote pilot user try it without deploying: a Cloudflare Tunnel / Tailscale Funnel in front of localhost:3000 + 8000 is acceptable for a trusted tester on public data. Set `AUTH_REQUIRED=true` first if the tunnel is not access-controlled.

## 2. Deployment plan

### Stage A — Staging on a single VM (days, ~$20–40/mo)

Goal: the pilot reachable at `staging.cited-market-brief-agent.app` for 1–5 trusted users.

- One small VM (EC2 t4g.medium / Lightsail / Hetzner), Docker Compose `--profile full`
- Caddy or Traefik for TLS; `ENVIRONMENT=production`, `AUTH_REQUIRED=true`
- Identity provider: Auth0 / WorkOS / Cognito free tier → fill `OIDC_*` vars; MFA on
- Postgres still in compose with volume backups (`scripts/backup_restore_test.sh` weekly)
- Cron on the VM runs `scripts/run_scheduled.py` (the runner already isolates per-watchlist failures and audits them)
- This is the cheapest credible way to satisfy two SECURITY.md gates: staging environment + live cross-tenant leakage test (create two orgs, verify zero bleed with RLS applied)

### Stage B — Production on AWS (the plan's target, when there are paying users)

Per plan §4, Terraform/OpenTofu in `infra/`:

- ECS Fargate: `api` service + `worker` (scheduled runner → later Hatchet), `web` (Next.js) or Vercel for the frontend
- RDS Postgres 18 + pgvector ≥0.8.2 (HNSW), automated snapshots, PITR ≥7 days
- S3 raw-source bucket (per-tenant prefixes + IAM conditions), ElastiCache Valkey
- Secrets Manager for all keys; egress proxy subnet before customer-configured URL fetching is enabled (SSRF gate)
- CloudWatch + OpenTelemetry → Langfuse for LLM traces
- GitHub Actions deploy job after the existing test/eval/security gates; SHA-pin actions, cosign-sign images (the two remaining supply-chain gates)
- Blocking before external users: the ⏳ rows in `docs/SECURITY.md` — pen test, privacy notice/DPA with counsel, IdP hardening

### Explicitly not: App Runner (maintenance mode) and OpenSearch Serverless (idle-cost floor) — see EVALUATION_REPORT.md §2.

## 3. From "built" to MVP

The engineering MVP scope (plan §3) is implemented. What makes it a *market* MVP:

1. **Pilot exit met** (Phase 6): one analyst keeps the brief in their morning routine; metrics ≥ gates for 2 weeks
2. **Stage A live** with `AUTH_REQUIRED=true` and 2–3 design-partner orgs on public data
3. **Billing-shaped tenancy**: orgs/plans columns already exist; add Stripe + seat limits only when a partner asks to pay
4. **Retrieval upgrade trigger**: introduce OpenSearch/reranker only if RAG-1 errors (retrieval misses) dominate the pilot error log — the metric, not the architecture, decides
5. **LLM mode default-on**: pick the production model via `EVAL_USE_LLM=1` eval runs; deterministic mode stays as the eval floor and fallback

## 4. iOS and Android

Mobile for this product is a **read → spot-check → approve** surface, not an authoring tool. Three stages, cheapest credible first:

- **M0 — PWA (1–2 days, in this repo)**: web manifest + icons + installable Next.js app; the dashboard already renders server-side and is fast. Add Web Push ("Your 06:30 brief is ready — 12 claims, 1 flagged") and approve/feedback work as-is. Analysts get it on iPhone/Android with zero app-store friction. iOS supports installed-PWA push since 16.4.
- **M1 — Expo/React Native (2–4 wks, post-pilot)**: one TypeScript codebase for both stores, talking to the same FastAPI + OIDC. Screens: today's brief, evidence drawer, section approve/reject, push notifications. Ship via TestFlight/internal track to design partners first.
- **M2 — Enterprise distribution (on demand)**: MDM deployment, biometric unlock, offline cache of approved briefs only (never unvalidated drafts), certificate pinning. Build when a customer's security review asks for it, not before.

Rule: no native build until the pilot proves the web brief is wanted daily. A push notification to a PWA delivers 90% of the mobile value at 2% of the cost.

## 5. Order of operations (recommended)

1. Local pilot now (§1) → fill `pilot/CASE_STUDY.md`
2. Stage A VM + IdP + leakage test (§2A) → remote pilot user
3. M0 PWA + push (§4) → morning phone moment
4. Counsel items + pen test → first external design partner
5. Stage B Terraform when revenue or load demands it; M1 app when partners ask
