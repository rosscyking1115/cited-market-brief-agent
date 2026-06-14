"""Morning market radar endpoints."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import APIRouter

from app.connectors.alpha_vantage import AlphaMarketValue, AlphaVantageClient
from app.connectors.bbc import BbcRssClient
from app.connectors.gdelt import GdeltClient
from app.core.config import settings
from app.market_radar.schemas import MorningRadarOut, OvernightRiskItem, PopularNewsItem
from app.market_radar.service import (
    build_morning_radar,
    build_overnight_risk,
    build_snapshots,
    normalize_popular_news_ranks,
    popular_news_from_bbc,
    popular_news_from_gdelt,
)

router = APIRouter(prefix="/market-radar", tags=["market-radar"])
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _CachedAlphaValue:
    value: AlphaMarketValue
    fetched_at: datetime


_ALPHA_VALUE_CACHE: dict[str, _CachedAlphaValue] = {}
_ALPHA_FAILURE_CACHE: dict[str, datetime] = {}


@router.get("", response_model=MorningRadarOut)
def get_market_radar() -> MorningRadarOut:
    popular_news: list[PopularNewsItem] = []
    snapshots = None
    overnight_risk: list[OvernightRiskItem] | None = None

    if settings.bbc_rss_enabled:
        client = BbcRssClient()
        try:
            popular_news.extend(popular_news_from_bbc(articles=client.latest(max_records=20)))
        except Exception as exc:
            logger.info("BBC RSS latest-headline fetch failed: %s", exc)
        finally:
            client.close()

    if settings.gdelt_enabled:
        client = GdeltClient()
        try:
            popular_news.extend(
                popular_news_from_gdelt(
                    last_hour=client.article_list(timespan="1h", max_records=20),
                    last_day=client.article_list(timespan="24h", max_records=30),
                ),
            )
        except Exception as exc:
            logger.info("GDELT news discovery fetch failed: %s", exc)
        finally:
            client.close()

    if settings.alpha_vantage_enabled and settings.alpha_vantage_api_key.strip():
        alpha_values = _alpha_vantage_values()
        alpha_values.update(_fred_market_values())
        snapshots = build_snapshots(alpha_values)
        overnight_risk = build_overnight_risk(alpha_values)

    return build_morning_radar(
        popular_news=normalize_popular_news_ranks(popular_news) if popular_news else None,
        snapshots=snapshots,
        overnight_risk=overnight_risk,
    )


def _alpha_vantage_values() -> dict[str, AlphaMarketValue]:
    now = datetime.now(UTC)
    values = _cached_alpha_values(now=now)
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
            symbol="USD/CNH",
            label="USD/CNH",
            fetch_factory=lambda client: lambda: client.exchange_rate(
                from_currency="USD",
                to_currency="CNH",
            ),
        ),
    ]


def _cached_alpha_values(*, now: datetime) -> dict[str, AlphaMarketValue]:
    max_age = timedelta(seconds=max(settings.alpha_vantage_cache_max_age_seconds, 0))
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
    _ALPHA_VALUE_CACHE[value.symbol] = _CachedAlphaValue(value=value, fetched_at=fetched_at)


def _fred_market_values() -> dict[str, AlphaMarketValue]:
    if not settings.fred_api_key.strip():
        return {}

    values: dict[str, AlphaMarketValue] = {}
    with httpx.Client(timeout=8.0) as client:
        for symbol, series_id in (("WTI", "DCOILWTICO"), ("US10Y", "DGS10")):
            try:
                value = _fred_latest_value(client=client, symbol=symbol, series_id=series_id)
            except Exception as exc:
                logger.warning("FRED %s fetch failed: %s", symbol, exc)
                continue
            if value is not None:
                values[symbol] = value
    return values


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
