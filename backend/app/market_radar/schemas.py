from typing import Literal

from pydantic import BaseModel, Field

MarketStatus = Literal["not_open", "open", "lunch", "closed", "weekend"]
SnapshotTone = Literal["up", "down", "flat", "pending"]
NewsRankKind = Literal["most_read", "most_viewed", "most_covered", "trending", "latest"]
SourceStatus = Literal["official_api", "rss", "licensed", "planned", "manual_reference"]


class MarketClockItem(BaseModel):
    market: str
    label: str
    window: str
    status: MarketStatus
    note: str


class MarketSnapshotItem(BaseModel):
    label: str
    local_name: str
    value: str
    change: str
    tone: SnapshotTone
    source: str
    source_status: Literal["live", "delayed", "eod", "planned"] = "planned"


class MarketStoryItem(BaseModel):
    title: str
    why: str
    tag: str


class PopularNewsItem(BaseModel):
    rank: int
    title: str
    title_zh_hant: str
    source: str
    url: str | None = None
    published_at: str | None = None
    window: Literal["1h", "24h"]
    rank_kind: NewsRankKind
    source_status: SourceStatus
    category: str
    why: str
    rights_note: str
    summary: str | None = None


class OvernightRiskItem(BaseModel):
    rank: int
    symbol: str
    name: str
    local_name: str
    group: Literal["futures", "volatility", "fx", "commodities", "rates"]
    value: str
    change: str
    tone: SnapshotTone
    source: str
    source_status: Literal["live", "delayed", "eod", "planned"] = "planned"
    why: str
    rights_note: str


class GlossaryItem(BaseModel):
    term: str
    english: str
    meaning: str


class MorningRadarOut(BaseModel):
    generated_at: str
    timezone: str = "Asia/Taipei"
    headline: str
    today_overview: str | None = None
    summary_points: list[str] = Field(min_length=3, max_length=3)
    current_focus: str
    market_clock: list[MarketClockItem]
    snapshots: list[MarketSnapshotItem]
    popular_news: list[PopularNewsItem]
    overnight_risk: list[OvernightRiskItem]
    stories: list[MarketStoryItem]
    glossary: list[GlossaryItem]
    disclaimer: str
