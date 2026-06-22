import base64
from datetime import date
from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.connectors.twse import twse_benchmark_return_from_payload, twse_daily_return_from_payload
from app.fund_attribution.schemas import (
    FundAttributionRequest,
    HoldingsFileParseRequest,
    HoldingsParseRequest,
)
from app.fund_attribution.service import (
    _normalize_twse_fund_symbol,
    analyze_fund_attribution,
    parse_holdings_text,
    parse_holdings_workbook,
)
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


def test_parse_jpm_workbook_accepts_downloaded_shape() -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "基金資產 - 股票"
    sheet.append(["基金資產 - 股票 (2026-06-18)", None, None, None, None])
    sheet.append(["摩根台灣鑫收益主動式ETF基金", None, None, None, None])
    sheet.append([None, None, None, None, None])
    sheet.append(["股票代碼", "股票名稱", "股數", "金額", "權重(%)"])
    sheet.append(["2330", "台灣積體電路製造", "122,000", "294,020,000", "8.36%"])
    sheet.append(["2454", "聯發科技", "54,000", "237,060,000", "6.74%"])
    output = BytesIO()
    workbook.save(output)

    result = parse_holdings_workbook(
        HoldingsFileParseRequest(
            filename="JPMAM-投資組合(TW00000401A1).xlsx",
            content_base64=base64.b64encode(output.getvalue()).decode("ascii"),
        )
    )

    assert result.as_of == "2026-06-18"
    assert result.fund_name == "摩根台灣鑫收益主動式ETF基金"
    assert result.parsed_count == 2
    assert result.detected_columns == ["股票代碼", "股票名稱", "股數", "金額", "權重(%)"]
    assert result.holdings[0].symbol == "2330"
    assert result.holdings[0].weight_pct == 8.36


def test_parse_holdings_file_endpoint_rejects_bad_base64() -> None:
    response = client.post(
        "/fund-attribution/parse-holdings-file",
        json={"filename": "bad.xlsx", "content_base64": "not base64"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["parsed_count"] == 0
    assert "base64" in body["warnings"][0]


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


def test_twse_benchmark_parser_reads_taiex_return() -> None:
    result = twse_benchmark_return_from_payload(
        symbol="TAIEX",
        name="台灣加權指數",
        as_of=date(2026, 6, 18),
        payload={
            "tables": [
                {
                    "fields": ["指數", "收盤指數", "漲跌(+/-)", "漲跌點數", "漲跌百分比"],
                    "data": [
                        ["寶島股價指數", "40,000.00", "+", "100.00", "0.25"],
                        ["發行量加權股價指數", "41,000.00", "+", "410.00", "1.01"],
                    ],
                }
            ]
        },
    )

    assert result is not None
    assert result.symbol == "TAIEX"
    assert result.name == "台灣加權指數"
    assert result.return_pct == 1.01
    assert result.close == 41000.0


def test_benchmark_return_endpoint_rejects_bad_date_without_network() -> None:
    response = client.post(
        "/fund-attribution/benchmark-return/twse",
        json={"as_of": "bad-date", "benchmark": "TAIEX"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["benchmark"] == "TAIEX"
    assert body["return_pct"] is None
    assert "YYYY-MM-DD" in body["warnings"][0]


def test_normalize_twse_fund_symbol_keeps_active_etf_letter() -> None:
    # Active ETF codes carry a trailing letter; plain stocks/ETFs do not.
    assert _normalize_twse_fund_symbol("00982A") == "00982A"
    assert _normalize_twse_fund_symbol(" 00982a ") == "00982A"
    assert _normalize_twse_fund_symbol("00982A 主動摩根台灣鑫收益") == "00982A"
    assert _normalize_twse_fund_symbol("2330") == "2330"
    assert _normalize_twse_fund_symbol("0050.TW") == "0050"
    assert _normalize_twse_fund_symbol("無代號") == ""


def test_fund_return_endpoint_rejects_bad_date_without_network() -> None:
    response = client.post(
        "/fund-attribution/fund-return/twse",
        json={"as_of": "bad-date", "symbol": "00982A"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "00982A"
    assert body["return_pct"] is None
    assert "YYYY-MM-DD" in body["warnings"][0]


def test_latest_endpoint_reports_unconfigured_when_empty(tmp_path, monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "fund_attribution_store_path", str(tmp_path / "fa"))
    response = client.get("/fund-attribution/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is False
    assert body["result"] is None


def test_fund_config_round_trips_through_the_store(tmp_path, monkeypatch) -> None:
    from app.core.config import settings
    from app.fund_attribution.schemas import FundConfig
    from app.fund_attribution.store import load_config, save_config

    monkeypatch.setattr(settings, "fund_attribution_store_path", str(tmp_path / "fa"))
    save_config(
        FundConfig(
            fund_name="主動摩根台灣鑫收益ETF",
            fund_symbol="00982A",
            holdings=[{"symbol": "2330", "name": "台積電", "weight_pct": 20.5}],
        )
    )

    loaded = load_config()
    assert loaded is not None
    assert loaded.fund_symbol == "00982A"
    assert loaded.holdings[0].symbol == "2330"


def test_refresh_is_noop_without_config(tmp_path, monkeypatch) -> None:
    from app.core.config import settings
    from app.fund_attribution.service import refresh_latest_attribution

    monkeypatch.setattr(settings, "fund_attribution_store_path", str(tmp_path / "empty"))
    assert refresh_latest_attribution() is None
