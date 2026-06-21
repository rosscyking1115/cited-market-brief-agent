from typing import Literal

from pydantic import BaseModel, Field


class HoldingInput(BaseModel):
    symbol: str = Field(min_length=1)
    name: str = Field(min_length=1)
    weight_pct: float = Field(ge=0)
    return_pct: float | None = None


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
    parsed_count: int
    skipped_rows: int
    detected_columns: list[str]
    holdings: list[HoldingInput]
    warnings: list[str]
    source_notes: list[str]
