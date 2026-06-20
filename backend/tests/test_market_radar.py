from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.api.routes import market_radar as market_radar_route
from app.api.routes.market_radar import (
    _ALPHA_FAILURE_CACHE,
    _ALPHA_VALUE_CACHE,
    _alpha_refresh_specs,
    _cached_alpha_values,
    _CachedAlphaValue,
    _fred_latest_value,
)
from app.connectors.alpha_vantage import AlphaMarketValue, _provider_message, alpha_series_latest
from app.connectors.bbc import BbcArticle, parse_bbc_rss
from app.connectors.gdelt import GdeltArticle
from app.main import app
from app.market_radar.service import (
    build_morning_radar,
    build_overnight_risk,
    build_snapshots,
    hydrate_overnight_risk_with_alpha,
    hydrate_snapshots_with_alpha,
    popular_news_from_bbc,
    popular_news_from_gdelt,
)

client = TestClient(app)


def test_market_radar_endpoint_contract() -> None:
    resp = client.get("/market-radar")
    assert resp.status_code == 200
    body = resp.json()

    assert body["timezone"] == "Asia/Taipei"
    assert body["headline"]
    assert len(body["summary_points"]) == 3
    assert len(body["market_clock"]) >= 6
    assert all(item["source_status"] != "planned" for item in body["snapshots"])
    assert len(body["popular_news"]) >= 4
    assert "top_indices" not in body
    assert all(item["source_status"] != "planned" for item in body["overnight_risk"])
    assert any(item["term"] == "費半" for item in body["glossary"])
    assert "投資建議" in body["disclaimer"]


def test_market_radar_labels_unlicensed_bbc_as_latest_not_most_read() -> None:
    body = client.get("/market-radar").json()
    bbc_items = [item for item in body["popular_news"] if item["source"] == "BBC"]

    assert bbc_items
    assert all(item["rank_kind"] == "latest" for item in bbc_items)
    assert all("Most Read" in item["rights_note"] for item in bbc_items)


def test_gdelt_news_rows_are_not_labeled_most_read() -> None:
    radar = build_morning_radar(
        datetime(2026, 6, 15, 8, 30, tzinfo=ZoneInfo("Asia/Taipei")),
        popular_news=popular_news_from_gdelt(
            last_hour=[
                GdeltArticle(
                    title="Global stocks rise as chip shares gain",
                    url="https://example.com/markets",
                    domain="example.com",
                    seendate="20260615001500",
                    source_country="US",
                    language="English",
                )
            ],
            last_day=[
                GdeltArticle(
                    title="Oil prices move higher after supply warning",
                    url="https://example.com/oil",
                    domain="example.com",
                    seendate="20260614230000",
                    source_country="GB",
                    language="English",
                )
            ],
        ),
    )
    rows = radar.popular_news

    assert rows[0].rank_kind == "trending"
    assert rows[0].source_status == "official_api"
    assert rows[0].url == "https://example.com/markets"
    assert rows[1].rank_kind == "most_covered"
    assert {row.rank_kind for row in rows}.isdisjoint({"most_read", "most_viewed"})


def test_bbc_rss_parser_keeps_latest_metadata() -> None:
    articles = parse_bbc_rss(
        b"""<?xml version="1.0" encoding="UTF-8" ?>
        <rss><channel>
          <item>
            <title>Markets brace for central bank decision</title>
            <link>https://www.bbc.com/news/example</link>
            <pubDate>Mon, 15 Jun 2026 00:10:00 GMT</pubDate>
            <category>Business</category>
          </item>
        </channel></rss>""",
        max_records=5,
    )

    assert len(articles) == 1
    assert articles[0].title == "Markets brace for central bank decision"
    assert articles[0].url == "https://www.bbc.com/news/example"
    assert articles[0].category == "Business"
    assert articles[0].published_at is not None


def test_bbc_news_rows_are_latest_and_time_filtered() -> None:
    now = datetime(2026, 6, 15, 8, 30, tzinfo=ZoneInfo("Asia/Taipei"))
    rows = popular_news_from_bbc(
        now=now,
        articles=[
            BbcArticle(
                title="Fresh market headline",
                url="https://www.bbc.com/news/fresh",
                published_at=datetime(2026, 6, 15, 0, 5, tzinfo=ZoneInfo("UTC")),
                category="Business",
            ),
            BbcArticle(
                title="Old market headline",
                url="https://www.bbc.com/news/old",
                published_at=datetime(2026, 6, 13, 0, 5, tzinfo=ZoneInfo("UTC")),
                category="Business",
            ),
        ],
    )

    assert rows
    assert all(row.source == "BBC" for row in rows)
    assert all(row.rank_kind == "latest" for row in rows)
    assert all("Most Read" in row.rights_note for row in rows)
    assert all(row.url != "https://www.bbc.com/news/old" for row in rows)


def test_market_clock_taiwan_preopen_sequence() -> None:
    radar = build_morning_radar(datetime(2026, 6, 15, 8, 30, tzinfo=ZoneInfo("Asia/Taipei")))
    statuses = {item.market: item.status for item in radar.market_clock}

    assert statuses["日本"] == "open"
    assert statuses["韓國"] == "open"
    assert statuses["台灣"] == "not_open"


def test_overnight_risk_is_separate_from_cash_indices() -> None:
    body = client.get("/market-radar").json()
    risk_symbols = {item["symbol"] for item in body["overnight_risk"]}

    assert {"ES", "NQ", "NK", "HSI-F", "TX"}.isdisjoint(risk_symbols)
    assert "top_indices" not in body
    assert all(item["source_status"] != "planned" for item in body["overnight_risk"])


def test_alpha_series_latest_uses_latest_and_previous_numeric_values() -> None:
    value = alpha_series_latest(
        symbol="WTI",
        source_status="eod",
        payload={
            "name": "WTI",
            "data": [
                {"date": "2026-06-12", "value": "78.25"},
                {"date": "2026-06-11", "value": "."},
                {"date": "2026-06-10", "value": "77.10"},
            ],
        },
    )

    assert value is not None
    assert value.symbol == "WTI"
    assert value.value == 78.25
    assert value.previous_value == 77.10
    assert round(value.change or 0, 2) == 1.15
    assert value.updated_at == "2026-06-12"


def test_alpha_provider_message_detects_rate_limit_payload() -> None:
    message = _provider_message({"Note": "standard API call frequency is 5 calls per minute"})

    assert message == "standard API call frequency is 5 calls per minute"


def test_alpha_cache_returns_existing_values_and_refreshes_missing_first() -> None:
    now = datetime(2026, 6, 14, 16, 0, tzinfo=UTC)
    _ALPHA_VALUE_CACHE.clear()
    _ALPHA_FAILURE_CACHE.clear()
    _ALPHA_VALUE_CACHE["USD/TWD"] = _CachedAlphaValue(
        value=AlphaMarketValue(
            symbol="USD/TWD",
            value=31.1234,
            previous_value=None,
            updated_at="2026-06-14 16:00:00",
            source_status="delayed",
        ),
        fetched_at=now,
    )

    values = _cached_alpha_values(now=now)
    specs = _alpha_refresh_specs(values=values, now=now)

    assert values["USD/TWD"].value == 31.1234
    assert [spec.symbol for spec in specs[:2]] == ["USD/JPY", "USD/CNY"]
    _ALPHA_VALUE_CACHE.clear()
    _ALPHA_FAILURE_CACHE.clear()


def test_alpha_refresh_skips_recent_failures() -> None:
    now = datetime(2026, 6, 14, 16, 0, tzinfo=UTC)
    _ALPHA_VALUE_CACHE.clear()
    _ALPHA_FAILURE_CACHE.clear()
    _ALPHA_FAILURE_CACHE["USD/JPY"] = now
    _ALPHA_FAILURE_CACHE["USD/CNY"] = now

    specs = _alpha_refresh_specs(values={}, now=now)

    assert [spec.symbol for spec in specs[:1]] == ["USD/TWD"]
    _ALPHA_FAILURE_CACHE.clear()


def test_market_value_cache_persists_between_backend_restarts(tmp_path, monkeypatch) -> None:
    now = datetime(2026, 6, 14, 16, 0, tzinfo=UTC)
    cache_path = tmp_path / "market_radar_values.json"
    monkeypatch.setattr(
        market_radar_route.settings,
        "market_radar_value_cache_path",
        str(cache_path),
    )
    market_radar_route._ALPHA_VALUE_CACHE.clear()
    market_radar_route._PERSISTED_CACHE_LOADED = False

    market_radar_route._remember_market_value(
        value=AlphaMarketValue(
            symbol="USD/TWD",
            value=31.1234,
            previous_value=None,
            updated_at="2026-06-14 16:00:00",
            source_status="delayed",
        ),
        fetched_at=now,
    )
    market_radar_route._ALPHA_VALUE_CACHE.clear()
    market_radar_route._PERSISTED_CACHE_LOADED = False

    values = market_radar_route._cached_market_values(now=now + timedelta(minutes=5))

    assert values["USD/TWD"].value == 31.1234
    assert values["USD/TWD"].source == "Alpha Vantage"
    market_radar_route._ALPHA_VALUE_CACHE.clear()
    market_radar_route._PERSISTED_CACHE_LOADED = False


def test_fred_latest_value_maps_observations_to_market_value() -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, list[dict[str, str]]]:
            return {
                "observations": [
                    {"date": "2026-06-13", "value": "."},
                    {"date": "2026-06-12", "value": "4.21"},
                    {"date": "2026-06-11", "value": "4.18"},
                ]
            }

    class FakeClient:
        def get(self, *_args: object, **_kwargs: object) -> FakeResponse:
            return FakeResponse()

    value = _fred_latest_value(client=FakeClient(), symbol="US10Y", series_id="DGS10")

    assert value is not None
    assert value.symbol == "US10Y"
    assert value.value == 4.21
    assert value.previous_value == 4.18
    assert value.updated_at == "2026-06-12"
    assert value.source == "FRED"


def test_alpha_hydration_updates_only_matching_overnight_risk_rows() -> None:
    rows = build_overnight_risk(include_planned=True)
    hydrated = hydrate_overnight_risk_with_alpha(
        rows,
        {
            "USD/TWD": AlphaMarketValue(
                symbol="USD/TWD",
                value=31.1234,
                previous_value=None,
                updated_at="2026-06-12 16:00:00",
                source_status="delayed",
            ),
            "US10Y": AlphaMarketValue(
                symbol="US10Y",
                value=4.21,
                previous_value=4.18,
                updated_at="2026-06-12",
                source_status="eod",
            ),
        },
    )

    fx = next(item for item in hydrated if item.symbol == "USD/TWD")
    rate = next(item for item in hydrated if item.symbol == "US10Y")

    assert fx.value == "31.1234"
    assert fx.change == "latest · 2026-06-12 16:00:00"
    assert fx.source == "Alpha Vantage"
    assert fx.source_status == "delayed"
    assert rate.value == "4.21%"
    assert rate.change.startswith("+0.03")
    assert rate.tone == "up"


def test_alpha_hydration_updates_market_snapshot_cards() -> None:
    rows = build_snapshots(include_planned=True)
    hydrated = hydrate_snapshots_with_alpha(
        rows,
        {
            "USD/TWD": AlphaMarketValue(
                symbol="USD/TWD",
                value=31.1234,
                previous_value=None,
                updated_at="2026-06-12 16:00:00",
                source_status="delayed",
            ),
            "WTI": AlphaMarketValue(
                symbol="WTI",
                value=78.25,
                previous_value=77.10,
                updated_at="2026-06-12",
                source_status="eod",
            ),
            "XAU": AlphaMarketValue(
                symbol="XAU",
                value=3400.50,
                previous_value=3375.50,
                updated_at="2026-06-12",
                source_status="eod",
            ),
            "US10Y": AlphaMarketValue(
                symbol="US10Y",
                value=4.21,
                previous_value=4.18,
                updated_at="2026-06-12",
                source_status="eod",
            ),
        },
    )

    fx = next(item for item in hydrated if item.label == "USD/TWD")
    oil = next(item for item in hydrated if item.label == "Oil / Gold")

    assert fx.value == "31.1234"
    assert fx.source_status == "delayed"
    assert oil.local_name == "WTI 原油 / 黃金"
    assert oil.value == "78.25"
    assert "黃金 +25.00" in oil.change
    assert oil.source_status == "eod"
