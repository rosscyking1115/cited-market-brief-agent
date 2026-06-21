"""TWSE after-close price connector for Taiwan ETF attribution.

This connector uses TWSE's public after-trading monthly stock endpoint for a
small, auditable workflow: calculate one stock's latest available daily return
on or before a requested date. It is not an intraday or redistributable market
data feed.
"""

from dataclasses import dataclass
from datetime import date

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class TwseDailyReturn:
    symbol: str
    trade_date: str
    close: float
    previous_close: float
    return_pct: float
    source: str = "TWSE afterTrading STOCK_DAY"
    source_status: str = "eod"


class TwseClient:
    def __init__(self) -> None:
        self._client = httpx.Client(timeout=settings.twse_request_timeout_seconds)

    def stock_daily_return(self, *, symbol: str, as_of: date) -> TwseDailyReturn | None:
        response = self._client.get(
            settings.twse_stock_day_url,
            params={
                "response": "json",
                "date": as_of.strftime("%Y%m%d"),
                "stockNo": symbol,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            return None
        return twse_daily_return_from_payload(symbol=symbol, payload=payload, as_of=as_of)

    def close(self) -> None:
        self._client.close()


def twse_daily_return_from_payload(
    *,
    symbol: str,
    payload: dict[str, object],
    as_of: date,
) -> TwseDailyReturn | None:
    fields = payload.get("fields")
    rows = payload.get("data")
    if not isinstance(fields, list) or not isinstance(rows, list):
        return None

    field_map = {_normalize_header(str(field)): index for index, field in enumerate(fields)}
    date_index = _first_index(field_map, ("date", "日期"))
    close_index = _first_index(field_map, ("close", "收盤價"))
    if date_index is None or close_index is None:
        return None

    parsed: list[tuple[date, float]] = []
    for row in rows:
        if not isinstance(row, list):
            continue
        if date_index >= len(row) or close_index >= len(row):
            continue
        trade_date = _parse_twse_date(str(row[date_index]))
        close = _parse_float(row[close_index])
        if trade_date is None or close is None or trade_date > as_of:
            continue
        parsed.append((trade_date, close))

    parsed.sort(key=lambda item: item[0])
    if len(parsed) < 2:
        return None

    latest_date, latest_close = parsed[-1]
    previous_close = parsed[-2][1]
    if previous_close == 0:
        return None

    return TwseDailyReturn(
        symbol=symbol,
        trade_date=latest_date.isoformat(),
        close=round(latest_close, 4),
        previous_close=round(previous_close, 4),
        return_pct=round((latest_close - previous_close) / previous_close * 100, 4),
    )


def _first_index(field_map: dict[str, int], candidates: tuple[str, ...]) -> int | None:
    for candidate in candidates:
        if candidate in field_map:
            return field_map[candidate]
    return None


def _normalize_header(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _parse_twse_date(value: str) -> date | None:
    parts = value.strip().split("/")
    if len(parts) != 3:
        return None
    try:
        year = int(parts[0])
        if year < 1911:
            year += 1911
        return date(year, int(parts[1]), int(parts[2]))
    except ValueError:
        return None


def _parse_float(value: object) -> float | None:
    try:
        return float(str(value).replace(",", "").replace("--", "").strip())
    except ValueError:
        return None
