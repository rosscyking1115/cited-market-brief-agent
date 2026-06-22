"""Fund-vs-benchmark attribution endpoints."""

from fastapi import APIRouter

from app.fund_attribution.schemas import (
    BenchmarkReturnOut,
    BenchmarkReturnRequest,
    FundAttributionOut,
    FundAttributionPlanOut,
    FundAttributionRequest,
    FundReturnOut,
    FundReturnRequest,
    HoldingReturnFillOut,
    HoldingReturnFillRequest,
    HoldingsFileParseRequest,
    HoldingsParseOut,
    HoldingsParseRequest,
)
from app.fund_attribution.service import (
    analyze_fund_attribution,
    attribution_plan,
    benchmark_return_from_twse,
    fill_holding_returns_from_twse,
    fund_return_from_twse,
    parse_holdings_text,
    parse_holdings_workbook,
)

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
