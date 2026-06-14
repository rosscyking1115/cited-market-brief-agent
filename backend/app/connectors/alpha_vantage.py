"""Alpha Vantage connector for the Taiwan morning market radar pilot.

The connector intentionally covers a small, auditable slice first: FX pairs,
WTI crude, and the US 10-year Treasury yield. Index/futures display rights are
left to a later licensed provider decision.
"""

from dataclasses import dataclass
from typing import Literal

import httpx

from app.core.config import settings

AlphaSourceStatus = Literal["delayed", "eod"]


@dataclass(frozen=True)
class AlphaMarketValue:
    symbol: str
    value: float
    previous_value: float | None
    updated_at: str | None
    source_status: AlphaSourceStatus

    @property
    def change(self) -> float | None:
        if self.previous_value is None:
            return None
        return self.value - self.previous_value

    @property
    def change_pct(self) -> float | None:
        if self.previous_value in (None, 0):
            return None
        return (self.value - self.previous_value) / self.previous_value * 100


class AlphaVantageClient:
    def __init__(self) -> None:
        self._client = httpx.Client(timeout=settings.alpha_vantage_request_timeout_seconds)

    def exchange_rate(self, *, from_currency: str, to_currency: str) -> AlphaMarketValue | None:
        payload = self._get(
            function="CURRENCY_EXCHANGE_RATE",
            from_currency=from_currency,
            to_currency=to_currency,
        )
        block = payload.get("Realtime Currency Exchange Rate")
        if not isinstance(block, dict):
            return None

        value = _parse_float(block.get("5. Exchange Rate"))
        if value is None:
            return None

        return AlphaMarketValue(
            symbol=f"{from_currency}/{to_currency}",
            value=value,
            previous_value=None,
            updated_at=str(block.get("6. Last Refreshed") or "").strip() or None,
            source_status="delayed",
        )

    def wti(self) -> AlphaMarketValue | None:
        return self._series_latest(symbol="WTI", function="WTI", source_status="eod")

    def treasury_yield_10y(self) -> AlphaMarketValue | None:
        return self._series_latest(
            symbol="US10Y",
            function="TREASURY_YIELD",
            source_status="eod",
            maturity="10year",
        )

    def close(self) -> None:
        self._client.close()

    def _get(self, **params: str) -> dict[str, object]:
        resp = self._client.get(
            settings.alpha_vantage_base_url,
            params={**params, "apikey": settings.alpha_vantage_api_key},
        )
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, dict):
            return {}
        return payload

    def _series_latest(
        self,
        *,
        symbol: str,
        function: str,
        source_status: AlphaSourceStatus,
        **params: str,
    ) -> AlphaMarketValue | None:
        payload = self._get(function=function, interval="daily", **params)
        return alpha_series_latest(
            symbol=symbol,
            payload=payload,
            source_status=source_status,
        )


def alpha_series_latest(
    *,
    symbol: str,
    payload: dict[str, object],
    source_status: AlphaSourceStatus,
) -> AlphaMarketValue | None:
    rows = payload.get("data")
    if not isinstance(rows, list):
        return None

    values: list[tuple[str | None, float]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        value = _parse_float(raw.get("value"))
        if value is None:
            continue
        date_value = str(raw.get("date") or "").strip() or None
        values.append((date_value, value))
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
        source_status=source_status,
    )


def _parse_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None
