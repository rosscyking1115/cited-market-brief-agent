from fastapi.testclient import TestClient

from app.fund_attribution.schemas import FundAttributionRequest
from app.fund_attribution.service import analyze_fund_attribution
from app.main import app

client = TestClient(app)


def test_fund_attribution_calculates_contributors_drags_and_residual() -> None:
    result = analyze_fund_attribution(
        FundAttributionRequest(
            fund_name="主動摩根台灣鑫收益ETF",
            benchmark_name="台灣加權指數",
            as_of="2026-06-18",
            fund_return_pct=0.42,
            benchmark_return_pct=0.18,
            holdings=[
                {"symbol": "2330", "name": "台積電", "weight_pct": 20.0, "return_pct": 1.0},
                {"symbol": "2454", "name": "聯發科", "weight_pct": 5.0, "return_pct": 2.0},
                {"symbol": "2882", "name": "國泰金", "weight_pct": 4.0, "return_pct": -1.0},
                {"symbol": "CASH", "name": "現金", "weight_pct": 3.0, "return_pct": 0.0},
            ],
            source_notes=["manual unit test"],
        )
    )

    assert result.active_return_pct == 0.24
    assert result.explained_return_pct == 0.26
    assert result.residual_pct == 0.16
    assert result.contributors[0].symbol == "2330"
    assert result.contributors[0].contribution_pct == 0.2
    assert result.drags[0].symbol == "2882"
    assert "贏過基準" in result.summary_zh_hant


def test_fund_attribution_tracks_missing_returns() -> None:
    result = analyze_fund_attribution(
        FundAttributionRequest(
            fund_name="Example Fund",
            benchmark_name="Example Benchmark",
            as_of="2026-06-18",
            fund_return_pct=-0.1,
            benchmark_return_pct=0.2,
            holdings=[
                {"symbol": "ABC", "name": "Missing Co", "weight_pct": 10.0},
            ],
        )
    )

    assert result.active_return_pct == -0.3
    assert result.missing_returns[0].symbol == "ABC"
    assert result.missing_returns[0].contribution_pct is None
    assert "落後基準" in result.summary_zh_hant


def test_fund_attribution_plan_endpoint_documents_automation_policy() -> None:
    response = client.get("/fund-attribution/plan")

    assert response.status_code == 200
    body = response.json()
    assert body["first_region"] == "Taiwan"
    assert any(item["status"] == "manual_first" for item in body["automation_policy"])
    assert any("TWSE" in item["label"] for item in body["automation_policy"])


def test_fund_attribution_analyze_endpoint() -> None:
    response = client.post(
        "/fund-attribution/analyze",
        json={
            "fund_name": "主動摩根台灣鑫收益ETF",
            "benchmark_name": "台灣加權指數",
            "as_of": "2026-06-18",
            "fund_return_pct": 0.42,
            "benchmark_return_pct": 0.18,
            "holdings": [
                {"symbol": "2330", "name": "台積電", "weight_pct": 20.0, "return_pct": 1.0},
                {"symbol": "2882", "name": "國泰金", "weight_pct": 4.0, "return_pct": -1.0},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["active_return_pct"] == 0.24
    assert body["contributors"][0]["symbol"] == "2330"
