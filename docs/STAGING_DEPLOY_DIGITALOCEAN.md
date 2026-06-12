# Staging Deploy: DigitalOcean Singapore VM

Goal: a password-protected staging URL for the family/domain-user pilot, balanced
for UK and Taiwan users. The app runs on one DigitalOcean Droplet in Singapore
with Docker Compose, Caddy TLS, Postgres/pgvector, and the 07:00 Taiwan scheduler.

## 1. What You Need To Create

Create a DigitalOcean Droplet:

- Region: Singapore
- Image: Ubuntu 24.04 LTS
- Size: Basic, 4 GB RAM / 2 vCPU / 80 GB SSD as the starting point
- Authentication: SSH key, not password
- Firewall: allow SSH, HTTP, HTTPS

Point a DNS record at the Droplet:

- Type: `A`
- Name: `staging` or your chosen subdomain
- Value: the Droplet public IPv4 address

Example domain:

```text
staging.example.com -> 203.0.113.10
```

## 2. Bootstrap The Server

SSH into the Droplet:

```bash
ssh root@YOUR_DROPLET_IP
```

Install Docker, firewall rules, and swap:

```bash
git clone https://github.com/YOUR_GITHUB_USER/YOUR_REPO.git /opt/cited-market-brief-agent
cd /opt/cited-market-brief-agent
bash infra/staging/bootstrap_ubuntu.sh
```

If you are copying the repo manually instead of cloning, put it at:

```text
/opt/cited-market-brief-agent
```

## 3. Create The Staging Env File

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

For the first family pilot, keep:

```text
AUTH_REQUIRED=false
```

Caddy basic auth protects the whole site. Before broader external sharing, switch
to OIDC/JWKS app auth.

## 4. Build And Start

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

## 5. Install The Morning Scheduler

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

## 6. Share With Testers

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

## 7. Current Limits

This is staging, not production:

- Single VM, single Postgres volume
- Caddy basic auth instead of OIDC
- Local Docker volumes instead of managed RDS/S3
- No external pen test yet

Move to the AWS/RDS/S3 production path only after the pilot proves the morning
brief is actually useful.
