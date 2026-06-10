"""API request/response schemas (Pydantic v2)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WatchlistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    tickers: list[str] = Field(default_factory=list, max_length=50)
    sectors: list[str] = Field(default_factory=list)
    macro_series: list[str] = Field(default_factory=list, description="FRED series IDs")
    schedule_cron: str | None = None
    template: str = "morning_brief"


class WatchlistUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    tickers: list[str] | None = None
    sectors: list[str] | None = None
    macro_series: list[str] | None = None
    schedule_cron: str | None = None
    template: str | None = None


class WatchlistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    tickers: list[str]
    sectors: list[str]
    macro_series: list[str]
    schedule_cron: str | None
    template: str
    created_at: datetime


class HealthOut(BaseModel):
    status: str
    version: str
