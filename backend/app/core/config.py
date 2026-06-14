"""Application settings (pydantic-settings). All secrets come from env, never the repo."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"

    # AuthN (plan §9): OIDC + PKCE at the IdP; API validates Bearer JWTs via JWKS.
    # auth_required MUST be true in any multi-tenant/production deployment.
    auth_required: bool = False
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""

    # Rate limiting (per client, per minute)
    rate_limit_per_minute: int = 120

    # Database
    database_url: str = "postgresql+psycopg://cited_market_brief_agent:cited_market_brief_agent@localhost:5432/cited_market_brief_agent"

    # Cache / queue
    valkey_url: str = "redis://localhost:6379/0"

    # Object storage
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket_raw: str = "cited-market-brief-agent-raw-sources"

    # SEC EDGAR fair access: declared UA is REQUIRED; hard ceiling 10 req/s.
    # https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
    sec_user_agent: str = ""
    sec_max_requests_per_second: float = 8.0  # stay under the 10 req/s ceiling

    # FRED
    fred_api_key: str = ""

    # GDELT news discovery. This is not readership data; use for trending/coverage only.
    gdelt_enabled: bool = False
    gdelt_base_url: str = "https://api.gdeltproject.org/api/v2/doc/doc"
    gdelt_request_timeout_seconds: float = 8.0

    # BBC RSS is latest-headline discovery only. BBC does not expose public read-rank data.
    bbc_rss_enabled: bool = False
    bbc_rss_url: str = "https://feeds.bbci.co.uk/news/rss.xml"
    bbc_request_timeout_seconds: float = 8.0

    # Alpha Vantage pilot feed for FX, commodities, and rates. Use only where terms permit.
    alpha_vantage_enabled: bool = False
    alpha_vantage_api_key: str = ""
    alpha_vantage_base_url: str = "https://www.alphavantage.co/query"
    alpha_vantage_request_timeout_seconds: float = 8.0
    alpha_vantage_cache_ttl_seconds: int = 900
    alpha_vantage_cache_max_age_seconds: int = 43200
    alpha_vantage_max_refreshes_per_request: int = 2
    alpha_vantage_failure_cooldown_seconds: int = 600

    # LLM providers (LiteLLM library mode; two providers at MVP)
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Models (LiteLLM identifiers) and prompt versioning (audit log requires both)
    generation_model: str = "anthropic/claude-sonnet-4-6"
    translation_model: str = "openai/gpt-4o-mini"
    embedding_model: str = "openai/text-embedding-3-small"
    prompt_version: str = "p1.0"
    translation_request_timeout_seconds: int = 90

    # Embeddings
    embedding_dimensions: int = 1536

    # Local paths (dev). Production uses S3 raw store (RAW_STORE_BACKEND=s3).
    raw_store_backend: str = "local"  # local | s3
    raw_store_path: str = ".data/raw"
    exports_path: str = ".data/exports"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
