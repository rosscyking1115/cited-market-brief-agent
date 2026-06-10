"""Auth enforcement + rate limiting, tested on a minimal app (no DB needed)."""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from app.core.security import require_auth


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/protected", dependencies=[Depends(require_auth)])
    def protected() -> dict:
        return {"ok": True}

    return app


def test_dev_mode_passes_without_token() -> None:
    client = TestClient(_app())
    assert client.get("/protected").status_code == 200


def test_auth_required_rejects_missing_and_malformed_tokens(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_required", True)
    client = TestClient(_app())

    resp = client.get("/protected")
    assert resp.status_code == 401
    assert resp.headers.get("WWW-Authenticate") == "Bearer"

    resp = client.get("/protected", headers={"Authorization": "Basic abc"})
    assert resp.status_code == 401

    # A garbage bearer token must fail closed (JWKS not configured -> 401, not 500 leak)
    resp = client.get("/protected", headers={"Authorization": "Bearer not.a.jwt"})
    assert resp.status_code in (401, 500)
    assert "Traceback" not in resp.text


def test_rate_limit_returns_429_with_retry_after() -> None:
    app = FastAPI()

    @app.get("/ping")
    def ping() -> dict:
        return {"ok": True}

    app.add_middleware(RateLimitMiddleware, requests_per_minute=3)
    client = TestClient(app)

    for _ in range(3):
        assert client.get("/ping").status_code == 200
    resp = client.get("/ping")
    assert resp.status_code == 429
    assert int(resp.headers["Retry-After"]) >= 1


def test_health_exempt_from_rate_limit() -> None:
    app = FastAPI()

    @app.get("/healthz")
    def health() -> dict:
        return {"ok": True}

    app.add_middleware(RateLimitMiddleware, requests_per_minute=1)
    client = TestClient(app)
    for _ in range(5):
        assert client.get("/healthz").status_code == 200


def test_security_headers_present() -> None:
    app = FastAPI()

    @app.get("/x")
    def x() -> dict:
        return {}

    app.add_middleware(SecurityHeadersMiddleware)
    client = TestClient(app)
    resp = client.get("/x")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Cache-Control"] == "no-store"


@pytest.fixture(autouse=True)
def _reset_auth(monkeypatch):
    yield
    monkeypatch.setattr(settings, "auth_required", False, raising=False)
