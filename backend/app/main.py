"""Cited Market Brief Agent API entrypoint.

Compliance posture (plan §9): factual, cited, non-personalized. No buy/sell/hold,
no portfolio advice, no performance presentation. Advice-boundary guardrails wrap
all generation endpoints (Phase 2).
"""

import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import (
    briefs,
    changes,
    exports,
    feedback,
    fund_attribution,
    health,
    market_radar,
    watchlists,
)
from app.core.config import settings
from app.core.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from app.core.security import require_auth


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Warm the morning-radar news cache off the request path so the first page
    # render is live, not the demo fallback, even on a freshly started container.
    threading.Thread(target=market_radar.prewarm_news, daemon=True).start()
    yield


app = FastAPI(
    title="Cited Market Brief Agent API",
    version=__version__,
    description="Audit-ready public-data brief engine. Internal research drafts only; not investment advice.",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

if settings.environment == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3010"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

_authed = [Depends(require_auth)]

app.include_router(health.router)  # liveness stays public
app.include_router(watchlists.router, dependencies=_authed)
app.include_router(briefs.router, dependencies=_authed)
app.include_router(feedback.router, dependencies=_authed)
app.include_router(changes.router, dependencies=_authed)
app.include_router(market_radar.router, dependencies=_authed)
app.include_router(fund_attribution.router, dependencies=_authed)
app.include_router(exports.router, dependencies=_authed)
