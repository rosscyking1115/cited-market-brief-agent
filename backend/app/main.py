"""LedgerBrief API entrypoint.

Compliance posture (plan §9): factual, cited, non-personalized. No buy/sell/hold,
no portfolio advice, no performance presentation. Advice-boundary guardrails wrap
all generation endpoints (Phase 2).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import briefs, feedback, health, watchlists
from app.core.config import settings

app = FastAPI(
    title="LedgerBrief API",
    version=__version__,
    description="Audit-ready public-data brief engine. Internal research drafts only; "
    "not investment advice.",
)

if settings.environment == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health.router)
app.include_router(watchlists.router)
app.include_router(briefs.router)
app.include_router(feedback.router)
