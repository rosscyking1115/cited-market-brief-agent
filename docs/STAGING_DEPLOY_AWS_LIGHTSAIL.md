# Staging Deploy: AWS Lightsail Singapore

Goal: a password-protected staging URL for the family/domain-user pilot, balanced
for UK and Taiwan users while starting the AWS learning path. The app runs on one
AWS Lightsail Ubuntu instance in Singapore with Docker Compose, Caddy TLS,
Postgres/pgvector, and the 07:00 Taiwan scheduler.

This is Stage A staging. It is intentionally simpler than the later production
AWS target of ECS/RDS/S3/Secrets Manager.

## 1. What To Create In AWS

Create an AWS account or sign in:

```text
https://aws.amazon.com/
```

Then open Lightsail:

```text
https://lightsail.aws.amazon.com/
```

Create an instance:

- Region: Asia Pacific, Singapore
- Platform: Linux/Unix
- Blueprint: OS Only, Ubuntu 24.04 LTS
- Plan: 4 GB RAM / 2 vCPU / 80 GB SSD, currently listed by AWS Lightsail at
  $24/month for Linux/Unix with public IPv4
- Name: `cmb-staging-sg`

Networking:

- Keep the default SSH port `22`
- Add/confirm firewall ports:
  - `80` TCP
  - `443` TCP
- Create and attach a static IP to the instance

DNS:

- If your domain is in Route 53, create an `A` record pointing to the static IP.
- If your domain is elsewhere, create the `A` record at that registrar/DNS host.

Example:

```text
staging.example.com -> 203.0.113.10
```

## 2. SSH Into The Instance

In the Lightsail console:

1. Open the instance page.
2. Use **Connect using SSH** for the first setup.

Or use your local terminal if you download the SSH key:

```bash
ssh ubuntu@YOUR_STATIC_IP
```

Become root for setup commands:

```bash
sudo -i
```

## 3. Bootstrap The Server

Clone the staging branch:

```bash
git clone --branch codex/staging-deploy https://github.com/rosscyking1115/cited-market-brief-agent.git /opt/cited-market-brief-agent
cd /opt/cited-market-brief-agent
```

Install Docker, firewall rules, and swap:

```bash
bash infra/staging/bootstrap_ubuntu.sh
```

If the repo is private, use one of these instead:

- Temporarily make the repo private-visible through a GitHub deploy key
- Use `gh auth login` on the instance
- Upload a zip/tarball manually

## 4. Create The Staging Env File

```bash
cd /opt/cited-market-brief-agent
cp .env.staging.example .env.staging
```

Generate a Caddy password hash:

```bash
docker run --rm caddy:2.10-alpine caddy hash-password --plaintext "CHOOSE_A_STRONG_PASSWORD"
```

Edit `.env.staging`:

```bash
nano .env.staging
```

Fill:

```text
STAGING_DOMAIN=staging.example.com
BASIC_AUTH_USER=pilot
BASIC_AUTH_HASH=<paste caddy hash>
POSTGRES_PASSWORD=<new long random password>
SEC_USER_AGENT=Cited Market Brief Agent staging your-email@example.com
FRED_API_KEY=<your key>
ANTHROPIC_API_KEY=<your key>
OPENAI_API_KEY=<your key>
```

Optional market-radar feeds:

```text
BBC_RSS_ENABLED=true
GDELT_ENABLED=true

# Alpha Vantage free keys are tiny-volume pilot keys. Keep the refresh budget low.
ALPHA_VANTAGE_ENABLED=true
ALPHA_VANTAGE_API_KEY=<your key>
ALPHA_VANTAGE_MAX_REFRESHES_PER_REQUEST=1
ALPHA_VANTAGE_CACHE_TTL_SECONDS=21600
ALPHA_VANTAGE_CACHE_MAX_AGE_SECONDS=604800

# FRED carries EOD macro/oil/rates/gold-style values and is cached separately.
FRED_MARKET_CACHE_TTL_SECONDS=3600
FRED_MARKET_MAX_REFRESHES_PER_REQUEST=3
MARKET_RADAR_VALUE_CACHE_PATH=/srv/.data/cache/market_radar_values.json
MARKET_RADAR_VALUE_CACHE_MAX_AGE_SECONDS=604800
```

The radar intentionally does not scrape Yahoo/StockQ/LSEG Workspace-style pages.
Free Alpha Vantage covers only a very small pilot volume; for production-grade
index/futures quotes, use a licensed/delayed market-data provider with display
rights.

For the first family pilot, keep:

```text
AUTH_REQUIRED=false
```

Caddy basic auth protects the whole site. Before broader external sharing, switch
to OIDC/JWKS app auth.

## 5. Build And Start

```bash
docker compose --env-file .env.staging -f docker-compose.staging.yml build
docker compose --env-file .env.staging -f docker-compose.staging.yml up -d db valkey
docker compose --env-file .env.staging -f docker-compose.staging.yml --profile tools run --rm bootstrap
docker compose --env-file .env.staging -f docker-compose.staging.yml up -d
```

Check health:

```bash
curl -I https://$STAGING_DOMAIN
curl -u pilot:YOUR_PASSWORD https://$STAGING_DOMAIN/api/healthz
```

If TLS is not issued yet, check:

```bash
docker compose --env-file .env.staging -f docker-compose.staging.yml logs -f caddy
```

The most common cause is DNS not yet pointing at the Lightsail static IP.

## 6. Install The Morning Scheduler

Watchlists are seeded with:

```text
0 23 * * *
```

That is 23:00 UTC, or 07:00 Taiwan time.

Install the host cron:

```bash
bash infra/staging/install_cron.sh /opt/cited-market-brief-agent
```

Run one immediate pilot brief:

```bash
docker compose --env-file .env.staging -f docker-compose.staging.yml --profile scheduler run --rm scheduler
```

Watch logs:

```bash
tail -f .data/logs/scheduler.log
docker compose --env-file .env.staging -f docker-compose.staging.yml logs -f backend frontend caddy
```

## 7. Share With Testers

Send:

```text
https://staging.example.com
username: pilot
password: <the password you chose>
```

Ask testers to try:

- Light and dark theme
- Original / 繁中 / 한국어 reader modes
- Clicking evidence chips
- Whether the top of the brief answers "what changed this morning?"
- Whether the language feels natural enough for a daily habit

## 8. Current Limits

This is staging, not production:

- Single Lightsail instance
- Single Docker Postgres volume
- Caddy basic auth instead of OIDC
- Local Docker volumes instead of managed RDS/S3
- No external pen test yet

Production AWS later:

- ECS/Fargate or App Runner alternative chosen by current AWS posture
- RDS Postgres with pgvector
- S3 for raw sources and exports
- Secrets Manager
- CloudWatch/OpenTelemetry
- Proper OIDC and tenant-isolation tests
