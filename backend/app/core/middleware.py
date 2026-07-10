"""Rate limiting + security headers (plan §9).

Rate limit: in-process sliding window per client IP. Sufficient for a single
API instance; swap the store for Valkey (same interface) when replicas arrive.
LLM endpoints get the same ceiling — cost control happens per-tenant in the
LLM gateway config as well (LLM10 Unbounded Consumption).
"""

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

_EXEMPT_PATHS = {"/healthz", "/docs", "/openapi.json"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int | None = None) -> None:
        super().__init__(app)
        self.limit = requests_per_minute or settings.rate_limit_per_minute
        self.window = 60.0
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _key(self, request: Request) -> str:
        client = request.client.host if request.client else "unknown"
        # Behind ALB/proxy use the left-most forwarded address
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client = forwarded.split(",")[0].strip()
        return client

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        now = time.monotonic()
        hits = self._hits[self._key(request)]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            retry_after = max(1, int(self.window - (now - hits[0])))
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """API responses are JSON/files — lock down browser interpretation anyway."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")  # briefs/evidence are tenant data — never shared-cache
        if settings.environment == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
        return response
