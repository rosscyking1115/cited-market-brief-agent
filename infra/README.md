# Infra (Phase 5)

Terraform/OpenTofu for AWS lands here in Phase 5 (production hardening): ECS/Fargate services, RDS Postgres 18 (pgvector ≥0.8.2), S3 with per-tenant prefixes + IAM conditions, ElastiCache (Valkey), Secrets Manager, CloudWatch, egress proxy subnet for source fetchers (SSRF control).

Do not use AWS App Runner (maintenance mode) or OpenSearch Serverless (idle-cost floor) — see `docs/EVALUATION_REPORT.md` §2.

Local development uses `docker-compose.yml` at the repo root.
