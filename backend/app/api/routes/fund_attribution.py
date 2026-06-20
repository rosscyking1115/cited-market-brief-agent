"""Fund-vs-benchmark attribution endpoints."""

from fastapi import APIRouter

from app.fund_attribution.schemas import (
    FundAttributionOut,
    FundAttributionPlanOut,
    FundAttributionRequest,
)
from app.fund_attribution.service import analyze_fund_attribution, attribution_plan

router = APIRouter(prefix="/fund-attribution", tags=["fund-attribution"])


@router.get("/plan", response_model=FundAttributionPlanOut)
def get_fund_attribution_plan() -> FundAttributionPlanOut:
    return attribution_plan()


@router.post("/analyze", response_model=FundAttributionOut)
def analyze(request: FundAttributionRequest) -> FundAttributionOut:
    return analyze_fund_attribution(request)
