"""Morning market radar endpoints."""

import logging
from collections.abc import Callable

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
        snapshots = build_snapshots(alpha_values)
        overnight_risk = build_overnight_risk(alpha_values)

    return build_morning_radar(
        popular_news=normalize_popular_news_ranks(popular_news) if popular_news else None,
        snapshots=snapshots,
        overnight_risk=overnight_risk,
    )


def _alpha_vantage_values() -> dict[str, AlphaMarketValue]:
    client = AlphaVantageClient()
    values: dict[str, AlphaMarketValue] = {}
    try:
        for from_currency, to_currency in (("USD", "TWD"), ("USD", "JPY"), ("USD", "CNH")):
            _collect_alpha_value(
                values,
                label=f"{from_currency}/{to_currency}",
                fetch=lambda from_currency=from_currency, to_currency=to_currency: (
                    client.exchange_rate(
                        from_currency=from_currency,
                        to_currency=to_currency,
                    )
                ),
            )

        _collect_alpha_value(values, label="WTI", fetch=client.wti)
        _collect_alpha_value(values, label="US10Y", fetch=client.treasury_yield_10y)
    finally:
        client.close()
    return values


def _collect_alpha_value(
    values: dict[str, AlphaMarketValue],
    *,
    label: str,
    fetch: Callable[[], AlphaMarketValue | None],
) -> None:
    try:
        value = fetch()
    except Exception as exc:
        logger.info("Alpha Vantage %s fetch failed: %s", label, exc)
        return
    if value is None:
        logger.info("Alpha Vantage %s returned no usable value", label)
        return
    values[value.symbol] = value
