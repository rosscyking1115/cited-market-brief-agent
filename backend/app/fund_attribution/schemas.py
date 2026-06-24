from typing import Literal

from pydantic import BaseModel, Field


class HoldingInput(BaseModel):
    symbol: str = Field(min_length=1)
    name: str = Field(min_length=1)
    weight_pct: float = Field(ge=0)
    return_pct: float | None = None
    sector: str | None = None


class FundAttributionRequest(BaseModel):
    fund_name: str = Field(min_length=1)
    benchmark_name: str = Field(min_length=1)
    as_of: str = Field(min_length=1)
    fund_return_pct: float
    benchmark_return_pct: float
    holdings: list[HoldingInput] = Field(min_length=1)
    source_notes: list[str] = Field(default_factory=list)


class HoldingsParseRequest(BaseModel):
    text: str = Field(min_length=1)
    source_name: str = "manual paste"


class HoldingsFileParseRequest(BaseModel):
    filename: str = Field(min_length=1)
    content_base64: str = Field(min_length=1)
    source_name: str | None = None


class HoldingReturnFillRequest(BaseModel):
    as_of: str = Field(min_length=1)
    holdings: list[HoldingInput] = Field(min_length=1)


class BenchmarkReturnRequest(BaseModel):
    as_of: str = Field(min_length=1)
    benchmark: Literal["TAIEX"] = "TAIEX"


class FundReturnRequest(BaseModel):
    as_of: str = Field(min_length=1)
    symbol: str = Field(min_length=1)


class SectorWeight(BaseModel):
    sector: str = Field(min_length=1)
    weight_pct: float = Field(ge=0)


class SectorConfig(BaseModel):
    """Set-once references for sector attribution: the TAIEX's (slowly-changing)
    sector weights, and an optional stock→sector map to fill holdings whose file
    didn't carry a 產業 column."""

    taiex_weights: list[SectorWeight] = Field(default_factory=list)
    sector_map: dict[str, str] = Field(default_factory=dict)  # symbol -> sector


class SectorAttributionRow(BaseModel):
    sector: str
    etf_weight_pct: float
    benchmark_weight_pct: float | None
    weight_diff_pct: float | None
    sector_return_pct: float | None
    etf_contribution_pct: float | None  # etf_weight * sector_return
    allocation_effect_pct: float | None  # (etf_weight - bm_weight) * sector_return


class SectorAttributionOut(BaseModel):
    as_of: str
    fund_name: str
    benchmark_name: str
    has_benchmark: bool
    rows: list[SectorAttributionRow]
    allocation_total_pct: float | None  # sum of allocation effects (active from allocation)
    unmapped_weight_pct: float  # ETF weight with no sector assigned
    summary_zh_hant: str
    source_notes: list[str]
    disclaimer: str


class FundConfig(BaseModel):
    """Saved holdings + fund metadata so the daily job can recompute without an
    upload. Holdings carry weights; returns are refilled from TWSE each run."""

    fund_name: str = Field(min_length=1)
    fund_symbol: str | None = None
    benchmark_name: str = "台灣加權指數"
    holdings: list[HoldingInput] = Field(min_length=1)
    source_notes: list[str] = Field(default_factory=list)


class AttributionRow(BaseModel):
    symbol: str
    name: str
    weight_pct: float
    return_pct: float | None
    contribution_pct: float | None
    direction: Literal["positive", "negative", "flat", "missing"]


class AutomationPolicyItem(BaseModel):
    label: str
    status: Literal["allowed", "manual_first", "needs_review", "blocked"]
    note: str


class FundAttributionOut(BaseModel):
    fund_name: str
    benchmark_name: str
    as_of: str
    fund_return_pct: float
    benchmark_return_pct: float
    active_return_pct: float
    explained_return_pct: float
    residual_pct: float
    holdings_count: int
    contributors: list[AttributionRow]
    drags: list[AttributionRow]
    missing_returns: list[AttributionRow]
    source_notes: list[str]
    automation_policy: list[AutomationPolicyItem]
    summary_zh_hant: str
    disclaimer: str


class LatestAttributionOut(BaseModel):
    configured: bool
    as_of: str | None = None
    result: FundAttributionOut | None = None


class FundAttributionPlanOut(BaseModel):
    title: str
    target_use_case: str
    first_region: str
    daily_trigger: str
    required_inputs: list[str]
    first_supported_workflow: list[str]
    automation_policy: list[AutomationPolicyItem]
    disclaimer: str


class HoldingsParseOut(BaseModel):
    source_name: str
    as_of: str | None = None
    fund_name: str | None = None
    parsed_count: int
    skipped_rows: int
    detected_columns: list[str]
    holdings: list[HoldingInput]
    warnings: list[str]
    source_notes: list[str]


class HoldingReturnFillOut(BaseModel):
    as_of: str
    filled_count: int
    missing_symbols: list[str]
    holdings: list[HoldingInput]
    warnings: list[str]
    source_notes: list[str]


class BenchmarkReturnOut(BaseModel):
    as_of: str
    benchmark: str
    name: str
    return_pct: float | None
    close: float | None
    previous_close: float | None
    warnings: list[str]
    source_notes: list[str]


class FundReturnOut(BaseModel):
    as_of: str
    symbol: str
    name: str
    return_pct: float | None
    close: float | None
    previous_close: float | None
    warnings: list[str]
    source_notes: list[str]
