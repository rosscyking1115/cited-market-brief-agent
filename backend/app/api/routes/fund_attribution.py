"""Fund-vs-benchmark attribution endpoints."""

from fastapi import APIRouter

from app.fund_attribution.schemas import (
    BenchmarkReturnOut,
    BenchmarkReturnRequest,
    FundAttributionOut,
    FundAttributionPlanOut,
    FundAttributionRequest,
    FundConfig,
    FundReturnOut,
    FundReturnRequest,
    HoldingReturnFillOut,
    HoldingReturnFillRequest,
    HoldingsFileParseRequest,
    HoldingsParseOut,
    HoldingsParseRequest,
    LatestAttributionOut,
)
from app.fund_attribution.service import (
    analyze_fund_attribution,
    attribution_plan,
    benchmark_return_from_twse,
    fill_holding_returns_from_twse,
    fund_return_from_twse,
    parse_holdings_text,
    parse_holdings_workbook,
    refresh_latest_attribution,
    save_fund_config,
)
from app.fund_attribution.store import load_config, load_result

router = APIRouter(prefix="/fund-attribution", tags=["fund-attribution"])


@router.get("/plan", response_model=FundAttributionPlanOut)
def get_fund_attribution_plan() -> FundAttributionPlanOut:
    return attribution_plan()


@router.post("/analyze", response_model=FundAttributionOut)
def analyze(request: FundAttributionRequest) -> FundAttributionOut:
    return analyze_fund_attribution(request)


@router.post("/parse-holdings", response_model=HoldingsParseOut)
def parse_holdings(request: HoldingsParseRequest) -> HoldingsParseOut:
    return parse_holdings_text(request)


@router.post("/parse-holdings-file", response_model=HoldingsParseOut)
def parse_holdings_file(request: HoldingsFileParseRequest) -> HoldingsParseOut:
    return parse_holdings_workbook(request)


@router.post("/fill-returns/twse", response_model=HoldingReturnFillOut)
def fill_returns_twse(request: HoldingReturnFillRequest) -> HoldingReturnFillOut:
    return fill_holding_returns_from_twse(request)


@router.post("/benchmark-return/twse", response_model=BenchmarkReturnOut)
def benchmark_return_twse(request: BenchmarkReturnRequest) -> BenchmarkReturnOut:
    return benchmark_return_from_twse(request)


@router.post("/fund-return/twse", response_model=FundReturnOut)
def fund_return_twse(request: FundReturnRequest) -> FundReturnOut:
    return fund_return_from_twse(request)


@router.put("/config", response_model=FundConfig)
def put_config(config: FundConfig) -> FundConfig:
    """Save the fund's holdings + code so the daily job can recompute unattended."""
    return save_fund_config(config)


@router.get("/latest", response_model=LatestAttributionOut)
def get_latest() -> LatestAttributionOut:
    """The most recent pre-computed attribution, ready to show on page load."""
    result = load_result()
    return LatestAttributionOut(
        configured=load_config() is not None,
        as_of=result.as_of if result else None,
        result=result,
    )


@router.post("/refresh", response_model=LatestAttributionOut)
def post_refresh() -> LatestAttributionOut:
    """Recompute now from the saved config (manual trigger / cron)."""
    result = refresh_latest_attribution()
    return LatestAttributionOut(
        configured=load_config() is not None,
        as_of=result.as_of if result else None,
        result=result,
    )
