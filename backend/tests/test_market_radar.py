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
from app.connectors.nyt import NytArticle, parse_nyt_most_popular
from app.main import app
from app.market_radar.service import (
    _market_category,
    build_morning_radar,
    build_overnight_risk,
    build_snapshots,
    hydrate_overnight_risk_with_alpha,
    hydrate_snapshots_with_alpha,
    popular_news_from_bbc,
    popular_news_from_gdelt,
    popular_news_from_nyt,
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
    assert isinstance(body["popular_news"], list)
    assert all(item["url"] for item in body["popular_news"])
    assert "top_indices" not in body
    assert all(item["source_status"] != "planned" for item in body["overnight_risk"])
    assert any(item["term"] == "費半" for item in body["glossary"])
    assert "投資建議" in body["disclaimer"]


def test_market_radar_labels_unlicensed_bbc_as_latest_not_most_read() -> None:
    bbc_items = popular_news_from_bbc(
        now=datetime(2026, 6, 15, 8, 30, tzinfo=ZoneInfo("Asia/Taipei")),
        articles=[
            BbcArticle(
                title="Markets brace for central bank decision",
                url="https://www.bbc.com/news/example",
                published_at=datetime(2026, 6, 15, 0, 10, tzinfo=ZoneInfo("UTC")),
                category="Business",
            )
        ],
    )

    assert bbc_items
    assert all(item.rank_kind == "latest" for item in bbc_items)
    assert all("Most Read" in item.rights_note for item in bbc_items)


def test_gdelt_news_rows_are_not_labeled_most_read() -> None:
    radar = build_morning_radar(
        datetime(2026, 6, 15, 8, 30, tzinfo=ZoneInfo("Asia/Taipei")),
        popular_news=popular_news_from_gdelt(
            last_day=[
                GdeltArticle(
                    title="Global stocks rise as chip shares gain",
                    url="https://example.com/markets",
                    domain="example.com",
                    seendate="20260615001500",
                    source_country="US",
                    language="English",
                ),
                GdeltArticle(
                    title="Oil prices move higher after supply warning",
                    url="https://example.com/oil",
                    domain="example.com",
                    seendate="20260614230000",
                    source_country="GB",
                    language="English",
                ),
            ],
        ),
    )
    rows = radar.popular_news

    assert rows[0].rank_kind == "most_covered"
    assert rows[0].source_status == "official_api"
    assert rows[0].window == "1d"
    assert rows[0].url == "https://example.com/markets"
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


def test_bbc_news_rows_keep_finance_only() -> None:
    now = datetime(2026, 6, 21, 8, 30, tzinfo=ZoneInfo("Asia/Taipei"))
    rows = popular_news_from_bbc(
        now=now,
        articles=[
            BbcArticle(
                title="Nine people in critical condition after train crash",
                url="https://www.bbc.com/news/train",
                published_at=datetime(2026, 6, 20, 23, 30, tzinfo=ZoneInfo("UTC")),
                category="UK",
            ),
            BbcArticle(
                title="Why an AI company cleaned my New York City apartment for free",
                url="https://www.bbc.com/news/ai-apartment",
                published_at=datetime(2026, 6, 20, 23, 40, tzinfo=ZoneInfo("UTC")),
                category="Technology",
            ),
            BbcArticle(
                title="Why Harry Kane is different at this tournament",
                url="https://www.bbc.com/sport/football",
                published_at=datetime(2026, 6, 20, 23, 45, tzinfo=ZoneInfo("UTC")),
                category="Sport",
            ),
            BbcArticle(
                title="Oil prices rise as Strait of Hormuz tensions grow",
                url="https://www.bbc.com/news/oil",
                published_at=datetime(2026, 6, 20, 23, 50, tzinfo=ZoneInfo("UTC")),
                category="World",
            ),
            BbcArticle(
                title="Chip earnings lift Asian markets",
                url="https://www.bbc.com/news/chips",
                published_at=datetime(2026, 6, 20, 23, 55, tzinfo=ZoneInfo("UTC")),
                category="Business",
            ),
        ],
    )

    urls = {row.url for row in rows}
    # Finance-only: non-market headlines are dropped, market ones kept and categorised.
    assert "https://www.bbc.com/news/train" not in urls
    assert "https://www.bbc.com/news/ai-apartment" not in urls
    assert "https://www.bbc.com/sport/football" not in urls
    assert "https://www.bbc.com/news/oil" in urls
    assert "https://www.bbc.com/news/chips" in urls
    by_url = {row.url: row for row in rows}
    assert by_url["https://www.bbc.com/news/oil"].category == "商品"
    assert by_url["https://www.bbc.com/news/chips"].category == "半導體"


def test_finance_rss_windows_dedupes_and_keeps_source_and_summary() -> None:
    from app.connectors.finance_rss import RssArticle
    from app.market_radar.service import popular_news_from_finance_rss

    now = datetime(2026, 6, 15, 8, 30, tzinfo=ZoneInfo("Asia/Taipei"))
    rows = popular_news_from_finance_rss(
        now=now,
        articles=[
            RssArticle(
                source="CNBC",
                title="Stocks fall as Treasury yields rise",
                url="https://www.cnbc.com/a",
                published_at=datetime(2026, 6, 15, 0, 10, tzinfo=ZoneInfo("UTC")),
                category="markets",
                summary="Equities dropped as yields climbed.",
            ),
            RssArticle(
                source="MarketWatch",
                title="Old oil headline",
                url="https://www.marketwatch.com/b",
                published_at=datetime(2026, 6, 12, 0, 0, tzinfo=ZoneInfo("UTC")),
                category=None,
                summary=None,
            ),
        ],
    )

    sources = {row.source for row in rows}
    assert "CNBC" in sources
    assert "https://www.marketwatch.com/b" not in {row.url for row in rows}  # >24h, dropped
    cnbc = next(row for row in rows if row.source == "CNBC")
    assert cnbc.rank_kind == "latest"
    assert cnbc.source_status == "rss"
    assert cnbc.summary == "Equities dropped as yields climbed."


def test_nyt_most_popular_parser_keeps_headline_and_link_and_dedupes() -> None:
    articles = parse_nyt_most_popular(
        {
            "status": "OK",
            "results": [
                {
                    "title": "Markets rally as inflation cools",
                    "url": "https://www.nytimes.com/a",
                    "published_date": "2026-06-21",
                    "section": "Business",
                },
                {"title": "", "url": "https://www.nytimes.com/blank", "section": "U.S."},
                {"title": "Duplicate url", "url": "https://www.nytimes.com/a", "section": "World"},
            ],
        },
        max_records=10,
    )

    assert len(articles) == 1
    assert articles[0].title == "Markets rally as inflation cools"
    assert articles[0].url == "https://www.nytimes.com/a"
    assert articles[0].section == "Business"


def test_popular_news_from_nyt_labels_most_viewed_and_skips_lifestyle() -> None:
    rows = popular_news_from_nyt(
        articles=[
            NytArticle(
                title="Fed signals patience on rate cuts",
                url="https://www.nytimes.com/fed",
                published_at="2026-06-21",
                section="Business",
            ),
            NytArticle(
                title="A great new pasta recipe",
                url="https://www.nytimes.com/food",
                published_at="2026-06-21",
                section="Food",
            ),
        ]
    )

    assert len(rows) == 1
    assert rows[0].rank_kind == "most_viewed"
    assert rows[0].source == "NYT"
    assert rows[0].source_status == "official_api"
    assert rows[0].url == "https://www.nytimes.com/fed"
    assert {row.rank_kind for row in rows}.isdisjoint({"latest", "trending", "most_covered"})


def test_today_overview_is_none_without_llm_key() -> None:
    from app.market_radar.service import generate_today_overview

    items = popular_news_from_nyt(
        articles=[
            NytArticle(
                title="Markets steady as inflation cools",
                url="https://www.nytimes.com/a",
                published_at="2026-06-21",
                section="Business",
            )
        ]
    )
    # conftest blanks the Anthropic key, so the overview is skipped (no network).
    assert generate_today_overview(items) is None


def test_nyt_rows_carry_the_abstract_as_summary() -> None:
    rows = popular_news_from_nyt(
        articles=[
            NytArticle(
                title="Fed holds rates",
                url="https://www.nytimes.com/fed",
                published_at="2026-06-21",
                section="Business",
                summary="The central bank kept its benchmark rate unchanged.",
            )
        ]
    )

    assert rows[0].summary == "The central bank kept its benchmark rate unchanged."


def test_market_category_does_not_match_ai_inside_words() -> None:
    assert _market_category("Nine people in critical condition after train crash") == "市場"
    assert _market_category("AI chip earnings lift Asian markets") == "半導體"
    assert _market_category("Why an AI company cleaned my apartment for free") == "市場"


def test_bbc_news_rows_do_not_duplicate_one_hour_items_in_day_bucket() -> None:
    now = datetime(2026, 6, 21, 8, 30, tzinfo=ZoneInfo("Asia/Taipei"))
    rows = popular_news_from_bbc(
        now=now,
        articles=[
            BbcArticle(
                title="Oil prices rise as Strait of Hormuz tensions grow",
                url="https://www.bbc.com/news/oil",
                published_at=datetime(2026, 6, 21, 0, 0, tzinfo=ZoneInfo("UTC")),
                category="World",
            ),
            BbcArticle(
                title="Central bank keeps interest rates unchanged",
                url="https://www.bbc.com/news/rates",
                published_at=datetime(2026, 6, 20, 18, 0, tzinfo=ZoneInfo("UTC")),
                category="Business",
            ),
        ],
    )

    by_url = {}
    for row in rows:
        by_url.setdefault(row.url, []).append(row.window)

    assert by_url["https://www.bbc.com/news/oil"] == ["1h"]
    assert by_url["https://www.bbc.com/news/rates"] == ["24h"]


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
