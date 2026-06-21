from datetime import date

from fastapi.testclient import TestClient

from app.connectors.twse import twse_daily_return_from_payload
from app.fund_attribution.schemas import FundAttributionRequest, HoldingsParseRequest
from app.fund_attribution.service import analyze_fund_attribution, parse_holdings_text
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


def test_parse_holdings_text_accepts_chinese_table_headers() -> None:
    result = parse_holdings_text(
        HoldingsParseRequest(
            source_name="jpm paste",
            text=(
                "日期,股票代號,股票名稱,持股比重,漲跌幅\n"
                "2026-06-18,2330,台積電,20.5%,1.2%\n"
                "2026-06-18,2454,聯發科,5.25,-0.4\n"
                "2026-06-18,,缺權重,,0.1\n"
            ),
        )
    )

    assert result.parsed_count == 2
    assert result.skipped_rows == 1
    assert result.holdings[0].symbol == "2330"
    assert result.holdings[0].name == "台積電"
    assert result.holdings[0].weight_pct == 20.5
    assert result.holdings[0].return_pct == 1.2
    assert result.holdings[1].return_pct == -0.4


def test_parse_holdings_text_accepts_tsv_and_english_headers() -> None:
    result = parse_holdings_text(
        HoldingsParseRequest(
            text=(
                "Ticker\tSecurity Name\tWeight (%)\tDaily Return\n"
                "2882\tCathay Financial\t4.0%\t-1.0%\n"
                "CASH\tCash\t3\t0\n"
            ),
        )
    )

    assert result.parsed_count == 2
    assert result.detected_columns == ["Ticker", "Security Name", "Weight (%)", "Daily Return"]
    assert result.holdings[0].symbol == "2882"
    assert result.holdings[0].weight_pct == 4.0
    assert result.holdings[1].symbol == "CASH"


def test_parse_holdings_endpoint() -> None:
    response = client.post(
        "/fund-attribution/parse-holdings",
        json={
            "source_name": "unit test paste",
            "text": "代號,名稱,權重\n2330,台積電,20.5%\n",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["parsed_count"] == 1
    assert body["holdings"][0]["symbol"] == "2330"


def test_twse_daily_return_parser_uses_latest_available_close() -> None:
    result = twse_daily_return_from_payload(
        symbol="2330",
        as_of=date(2026, 6, 18),
        payload={
            "fields": ["日期", "成交股數", "收盤價", "漲跌價差"],
            "data": [
                ["115/06/16", "1,000", "1,000.00", "+10.00"],
                ["115/06/17", "1,100", "1,020.00", "+20.00"],
                ["115/06/18", "1,200", "1,040.40", "+20.40"],
                ["115/06/19", "1,300", "1,030.00", "-10.40"],
            ],
        },
    )

    assert result is not None
    assert result.symbol == "2330"
    assert result.trade_date == "2026-06-18"
    assert result.return_pct == 2.0


def test_fill_returns_endpoint_rejects_bad_date_without_network() -> None:
    response = client.post(
        "/fund-attribution/fill-returns/twse",
        json={
            "as_of": "bad-date",
            "holdings": [{"symbol": "2330", "name": "台積電", "weight_pct": 20.5}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["filled_count"] == 0
    assert body["missing_symbols"] == ["2330"]
    assert "YYYY-MM-DD" in body["warnings"][0]
