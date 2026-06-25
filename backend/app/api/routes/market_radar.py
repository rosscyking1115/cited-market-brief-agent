"""Morning market radar endpoints."""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from fastapi import APIRouter

from app.connectors.alpha_vantage import AlphaMarketValue, AlphaVantageClient
from app.connectors.finance_rss import fetch_finance_feeds
from app.connectors.gdelt import GdeltClient
from app.connectors.nyt import NytMostPopularClient
from app.core.config import settings
from app.market_radar.schemas import MorningRadarOut, OvernightRiskItem, PopularNewsItem
from app.market_radar.service import (
    build_morning_radar,
    build_overnight_risk,
    build_snapshots,
    generate_news_overview,
    normalize_popular_news_ranks,
    popular_news_from_finance_rss,
    popular_news_from_gdelt,
    popular_news_from_nyt,
    translate_news_items_zh,
)

router = APIRouter(prefix="/market-radar", tags=["market-radar"])
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _CachedAlphaValue:
    value: AlphaMarketValue
    fetched_at: datetime


_ALPHA_VALUE_CACHE: dict[str, _CachedAlphaValue] = {}
_ALPHA_FAILURE_CACHE: dict[str, datetime] = {}
_PERSISTED_CACHE_LOADED = False


@dataclass
class _NewsCache:
    items: list[PopularNewsItem]
    overviews: tuple[str | None, str | None, str | None]  # today, week, month
    fetched_at: datetime


_NEWS_CACHE: _NewsCache | None = None


@router.get("", response_model=MorningRadarOut)
def get_market_radar() -> MorningRadarOut:
    now = datetime.now(UTC)
    popular_news, (today_ov, week_ov, month_ov) = _cached_news(now=now)

    snapshots = None
    overnight_risk: list[OvernightRiskItem] | None = None
    market_values = _market_values()
    if market_values:
        snapshots = build_snapshots(market_values)
        overnight_risk = build_overnight_risk(market_values)

    return build_morning_radar(
        popular_news=popular_news or None,
        snapshots=snapshots,
        overnight_risk=overnight_risk,
        today_overview=today_ov,
        week_overview=week_ov,
        month_overview=month_ov,
    )


def prewarm_news() -> None:
    """Populate the news cache off the request path (called at app startup), so the
    first page render shows live news instead of the demo fallback on a cold start."""
    try:
        _cached_news(now=datetime.now(UTC))
    except Exception as exc:  # noqa: BLE001 - startup warmup must never crash the app.
        logger.info("News prewarm failed: %s", exc)


def _cached_news(
    *, now: datetime
) -> tuple[list[PopularNewsItem], tuple[str | None, str | None, str | None]]:
    """Serve assembled + translated news and the day/week/month overviews from a
    short-lived cache. The endpoint blocks on live fetches + LLM translation/overview
    calls that can exceed the frontend server-render timeout; a brief TTL keeps the
    page fast and a transient empty result falls back to the last good set."""
    global _NEWS_CACHE
    ttl = timedelta(seconds=max(settings.news_cache_ttl_seconds, 0))
    if _NEWS_CACHE is not None and now - _NEWS_CACHE.fetched_at <= ttl:
        return _NEWS_CACHE.items, _NEWS_CACHE.overviews
    fetched = _fetch_popular_news()
    if fetched:
        fetched = translate_news_items_zh(fetched)
        # Windows are cumulative time ranges: this week's report covers today + the
        # week's most-read finance, this month's covers all of it. A single
        # publisher's week-only most-read finance is often empty, so summarizing the
        # rolling window keeps the weekly/monthly digests substantive.
        day_items = [i for i in fetched if i.window == "1d"]
        week_items = [i for i in fetched if i.window in ("1d", "1w")]
        overviews = (
            generate_news_overview(day_items, "今日"),
            generate_news_overview(week_items, "本週"),
            generate_news_overview(fetched, "本月"),
        )
        _NEWS_CACHE = _NewsCache(items=fetched, overviews=overviews, fetched_at=now)
        return fetched, overviews
    if _NEWS_CACHE is not None:
        return _NEWS_CACHE.items, _NEWS_CACHE.overviews
    return [], (None, None, None)


def _fetch_popular_news() -> list[PopularNewsItem]:
    popular_news: list[PopularNewsItem] = []

    if settings.bbc_rss_enabled:
        try:
            popular_news.extend(popular_news_from_finance_rss(articles=fetch_finance_feeds()))
        except Exception as exc:
            logger.info("Finance RSS fetch failed: %s", exc)

    if settings.gdelt_enabled:
        client = GdeltClient()
        try:
            popular_news.extend(
                popular_news_from_gdelt(last_day=client.article_list(timespan="24h", max_records=80)),
            )
        except Exception as exc:
            logger.info("GDELT news discovery fetch failed: %s", exc)
        finally:
            client.close()

    if settings.nyt_enabled and settings.nyt_api_key.strip():
        client = NytMostPopularClient()
        try:
            # Most-viewed over the day / week / month (NYT Most Popular periods 1/7/30).
            for period, window in ((1, "1d"), (7, "1w"), (30, "1m")):
                popular_news.extend(
                    popular_news_from_nyt(
                        articles=client.most_viewed(period=period, max_records=20),
                        window=window,
                    ),
                )
        except Exception as exc:
            logger.info("NYT Most Popular fetch failed: %s", exc)
        finally:
            client.close()

    return normalize_popular_news_ranks(popular_news) if popular_news else []


def _market_values() -> dict[str, AlphaMarketValue]:
    now = datetime.now(UTC)
    values = _cached_market_values(now=now)
    values.update(_fred_market_values(values=values, now=now))

    if settings.alpha_vantage_enabled and settings.alpha_vantage_api_key.strip():
        values.update(_alpha_vantage_values(values=values, now=now))
    return values


def _alpha_vantage_values(
    *,
    values: dict[str, AlphaMarketValue],
    now: datetime,
) -> dict[str, AlphaMarketValue]:
    refresh_specs = _alpha_refresh_specs(values=values, now=now)
    refresh_budget = max(settings.alpha_vantage_max_refreshes_per_request, 0)
    if not refresh_specs or refresh_budget == 0:
        return values

    client = AlphaVantageClient()
    try:
        for spec in refresh_specs[:refresh_budget]:
            _collect_alpha_value(
                values,
                label=spec.label,
                fetch=spec.fetch_factory(client),
                fetched_at=now,
            )
    finally:
        client.close()
    return values


@dataclass(frozen=True)
class _AlphaFetchSpec:
    symbol: str
    label: str
    fetch_factory: Callable[[AlphaVantageClient], Callable[[], AlphaMarketValue | None]]


def _alpha_fetch_plan() -> list[_AlphaFetchSpec]:
    return [
        _AlphaFetchSpec(
            symbol="USD/TWD",
            label="USD/TWD",
            fetch_factory=lambda client: lambda: client.exchange_rate(
                from_currency="USD",
                to_currency="TWD",
            ),
        ),
        _AlphaFetchSpec(
            symbol="USD/JPY",
            label="USD/JPY",
            fetch_factory=lambda client: lambda: client.exchange_rate(
                from_currency="USD",
                to_currency="JPY",
            ),
        ),
        _AlphaFetchSpec(
            symbol="USD/CNY",
            label="USD/CNY",
            fetch_factory=lambda client: lambda: client.exchange_rate(
                from_currency="USD",
                to_currency="CNY",
            ),
        ),
    ]


def _cached_alpha_values(*, now: datetime) -> dict[str, AlphaMarketValue]:
    max_age = timedelta(seconds=max(settings.alpha_vantage_cache_max_age_seconds, 0))
    _load_persisted_market_cache()
    values: dict[str, AlphaMarketValue] = {}
    expired: list[str] = []
    for symbol, cached in _ALPHA_VALUE_CACHE.items():
        if now - cached.fetched_at <= max_age:
            values[symbol] = cached.value
        else:
            expired.append(symbol)
    for symbol in expired:
        _ALPHA_VALUE_CACHE.pop(symbol, None)
    return values


def _cached_market_values(*, now: datetime) -> dict[str, AlphaMarketValue]:
    _load_persisted_market_cache()
    max_age = timedelta(seconds=max(settings.market_radar_value_cache_max_age_seconds, 0))
    values: dict[str, AlphaMarketValue] = {}
    expired: list[str] = []
    for symbol, cached in _ALPHA_VALUE_CACHE.items():
        if now - cached.fetched_at <= max_age:
            values[symbol] = cached.value
        else:
            expired.append(symbol)
    for symbol in expired:
        _ALPHA_VALUE_CACHE.pop(symbol, None)
    return values


def _alpha_refresh_specs(
    *,
    values: dict[str, AlphaMarketValue],
    now: datetime,
) -> list[_AlphaFetchSpec]:
    ttl = timedelta(seconds=max(settings.alpha_vantage_cache_ttl_seconds, 0))
    missing: list[_AlphaFetchSpec] = []
    stale: list[_AlphaFetchSpec] = []
    for spec in _alpha_fetch_plan():
        if _alpha_recently_failed(spec.symbol, now=now):
            continue
        cached = _ALPHA_VALUE_CACHE.get(spec.symbol)
        if spec.symbol not in values or cached is None:
            missing.append(spec)
        elif now - cached.fetched_at > ttl:
            stale.append(spec)
    return [*missing, *stale]


def _alpha_recently_failed(symbol: str, *, now: datetime) -> bool:
    failed_at = _ALPHA_FAILURE_CACHE.get(symbol)
    if failed_at is None:
        return False
    cooldown = timedelta(seconds=max(settings.alpha_vantage_failure_cooldown_seconds, 0))
    if now - failed_at <= cooldown:
        return True
    _ALPHA_FAILURE_CACHE.pop(symbol, None)
    return False


def _collect_alpha_value(
    values: dict[str, AlphaMarketValue],
    *,
    label: str,
    fetch: Callable[[], AlphaMarketValue | None],
    fetched_at: datetime,
) -> None:
    try:
        value = fetch()
    except Exception as exc:
        _ALPHA_FAILURE_CACHE[label] = fetched_at
        logger.warning("Alpha Vantage %s fetch failed: %s", label, exc)
        return
    if value is None:
        _ALPHA_FAILURE_CACHE[label] = fetched_at
        logger.warning("Alpha Vantage %s returned no usable value", label)
        return
    values[value.symbol] = value
    _ALPHA_FAILURE_CACHE.pop(value.symbol, None)
    _remember_market_value(value=value, fetched_at=fetched_at)


@dataclass(frozen=True)
class _FredFetchSpec:
    symbol: str
    series_id: str


def _fred_fetch_plan() -> list[_FredFetchSpec]:
    return [
        _FredFetchSpec(symbol="USD/JPY", series_id="DEXJPUS"),
        _FredFetchSpec(symbol="USD/CNY", series_id="DEXCHUS"),
        _FredFetchSpec(symbol="USD-BROAD", series_id="DTWEXBGS"),
        _FredFetchSpec(symbol="VIX", series_id="VIXCLS"),
        _FredFetchSpec(symbol="WTI", series_id="DCOILWTICO"),
        _FredFetchSpec(symbol="US10Y", series_id="DGS10"),
    ]


def _fred_market_values(
    *,
    values: dict[str, AlphaMarketValue],
    now: datetime,
) -> dict[str, AlphaMarketValue]:
    if not settings.fred_api_key.strip():
        return {}

    refreshed: dict[str, AlphaMarketValue] = {}
    refresh_specs = _fred_refresh_specs(values=values, now=now)
    refresh_budget = max(settings.fred_market_max_refreshes_per_request, 0)
    if not refresh_specs or refresh_budget == 0:
        return refreshed

    with httpx.Client(timeout=8.0) as client:
        for spec in refresh_specs[:refresh_budget]:
            try:
                value = _fred_latest_value(
                    client=client,
                    symbol=spec.symbol,
                    series_id=spec.series_id,
                )
            except Exception as exc:
                logger.warning("FRED %s fetch failed: %s", spec.symbol, exc)
                continue
            if value is not None:
                refreshed[value.symbol] = value
                _remember_market_value(value=value, fetched_at=now)
    return refreshed


def _fred_refresh_specs(
    *,
    values: dict[str, AlphaMarketValue],
    now: datetime,
) -> list[_FredFetchSpec]:
    ttl = timedelta(seconds=max(settings.fred_market_cache_ttl_seconds, 0))
    missing: list[_FredFetchSpec] = []
    stale: list[_FredFetchSpec] = []
    for spec in _fred_fetch_plan():
        cached = _ALPHA_VALUE_CACHE.get(spec.symbol)
        if spec.symbol not in values or cached is None:
            missing.append(spec)
        elif now - cached.fetched_at > ttl:
            stale.append(spec)
    return [*missing, *stale]


def _fred_latest_value(
    *,
    client: httpx.Client,
    symbol: str,
    series_id: str,
) -> AlphaMarketValue | None:
    resp = client.get(
        "https://api.stlouisfed.org/fred/series/observations",
        params={
            "api_key": settings.fred_api_key,
            "file_type": "json",
            "series_id": series_id,
            "sort_order": "desc",
            "limit": "8",
        },
    )
    resp.raise_for_status()
    observations = resp.json().get("observations", [])
    if not isinstance(observations, list):
        return None

    values: list[tuple[str | None, float]] = []
    for raw in observations:
        if not isinstance(raw, dict):
            continue
        parsed = _parse_float(raw.get("value"))
        if parsed is None:
            continue
        values.append((str(raw.get("date") or "").strip() or None, parsed))
        if len(values) >= 2:
            break
    if not values:
        return None

    latest_date, latest_value = values[0]
    previous_value = values[1][1] if len(values) > 1 else None
    return AlphaMarketValue(
        symbol=symbol,
        value=latest_value,
        previous_value=previous_value,
        updated_at=latest_date,
        source_status="eod",
        source="FRED",
    )


def _parse_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def _remember_market_value(*, value: AlphaMarketValue, fetched_at: datetime) -> None:
    _ALPHA_VALUE_CACHE[value.symbol] = _CachedAlphaValue(value=value, fetched_at=fetched_at)
    _persist_market_cache()


def _load_persisted_market_cache() -> None:
    global _PERSISTED_CACHE_LOADED
    if _PERSISTED_CACHE_LOADED:
        return
    _PERSISTED_CACHE_LOADED = True
    path = Path(settings.market_radar_value_cache_path)
    if not path.exists():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Market radar value cache read failed: %s", exc)
        return
    if not isinstance(payload, dict):
        return
    for symbol, raw in payload.items():
        if not isinstance(raw, dict):
            continue
        value = _market_value_from_cache(symbol=str(symbol), raw=raw)
        if value is None:
            continue
        _ALPHA_VALUE_CACHE[value.value.symbol] = value


def _market_value_from_cache(
    *,
    symbol: str,
    raw: dict[str, object],
) -> _CachedAlphaValue | None:
    value = _parse_float(raw.get("value"))
    if value is None:
        return None
    fetched_at_raw = str(raw.get("fetched_at") or "").strip()
    try:
        fetched_at = datetime.fromisoformat(fetched_at_raw)
    except ValueError:
        return None
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=UTC)
    previous_value = _parse_float(raw.get("previous_value"))
    source_status = str(raw.get("source_status") or "").strip()
    if source_status not in {"delayed", "eod"}:
        return None
    return _CachedAlphaValue(
        value=AlphaMarketValue(
            symbol=symbol,
            value=value,
            previous_value=previous_value,
            updated_at=str(raw.get("updated_at") or "").strip() or None,
            source_status=source_status,  # type: ignore[arg-type]
            source=str(raw.get("source") or "").strip() or "Cached market feed",
        ),
        fetched_at=fetched_at.astimezone(UTC),
    )


def _persist_market_cache() -> None:
    path = Path(settings.market_radar_value_cache_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            symbol: {
                "value": cached.value.value,
                "previous_value": cached.value.previous_value,
                "updated_at": cached.value.updated_at,
                "source_status": cached.value.source_status,
                "source": cached.value.source,
                "fetched_at": cached.fetched_at.astimezone(UTC).isoformat(),
            }
            for symbol, cached in sorted(_ALPHA_VALUE_CACHE.items())
        }
        temp_path = path.with_suffix(f"{path.suffix}.tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(path)
    except OSError as exc:
        logger.warning("Market radar value cache write failed: %s", exc)
