"""TWSE after-close price connector for Taiwan ETF attribution.

This connector uses TWSE's public after-trading monthly stock endpoint for a
small, auditable workflow: calculate one stock's latest available daily return
on or before a requested date. It is not an intraday or redistributable market
data feed.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import httpx

from app.core.config import settings

_INDUSTRY_CACHE: dict[str, str] = {}
_INDUSTRY_CACHE_AT: datetime | None = None


@dataclass(frozen=True)
class TwseDailyReturn:
    symbol: str
    trade_date: str
    close: float
    previous_close: float
    return_pct: float
    source: str = "TWSE afterTrading STOCK_DAY"
    source_status: str = "eod"


@dataclass(frozen=True)
class TwseBenchmarkReturn:
    symbol: str
    name: str
    trade_date: str
    close: float
    previous_close: float
    return_pct: float
    source: str = "TWSE afterTrading MI_INDEX"
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

    def taiex_return(self, *, as_of: date) -> TwseBenchmarkReturn | None:
        response = self._client.get(
            settings.twse_mi_index_url,
            params={
                "response": "json",
                "date": as_of.strftime("%Y%m%d"),
                "type": "IND",
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            return None
        return twse_benchmark_return_from_payload(
            symbol="TAIEX",
            name="台灣加權指數",
            payload=payload,
            as_of=as_of,
        )

    def sector_returns(self, *, as_of: date) -> dict[str, float]:
        response = self._client.get(
            settings.twse_mi_index_url,
            params={
                "response": "json",
                "date": as_of.strftime("%Y%m%d"),
                "type": "IND",
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            return {}
        return twse_sector_returns_from_payload(payload)

    def close(self) -> None:
        self._client.close()


# TWSE 產業別 codes → names that line up (after canonical_sector) with the TWSE
# sector class indices (e.g. 24 → 半導體, matching 半導體類指數).
TWSE_INDUSTRY_CODES = {
    "01": "水泥",
    "02": "食品",
    "03": "塑膠",
    "04": "紡織纖維",
    "05": "電機機械",
    "06": "電器電纜",
    "08": "玻璃陶瓷",
    "09": "造紙",
    "10": "鋼鐵",
    "11": "橡膠",
    "12": "汽車",
    "14": "建材營造",
    "15": "航運",
    "16": "觀光餐旅",
    "17": "金融保險",
    "18": "貿易百貨",
    "19": "綜合",
    "20": "其他",
    "21": "化學",
    "22": "生技醫療",
    "23": "油電燃氣",
    "24": "半導體",
    "25": "電腦及週邊設備",
    "26": "光電",
    "27": "通信網路",
    "28": "電子零組件",
    "29": "電子通路",
    "30": "資訊服務",
    "31": "其他電子",
    "32": "文化創意",
    "33": "農業科技",
    "34": "電子商務",
    "35": "綠能環保",
    "36": "數位雲端",
    "37": "運動休閒",
    "38": "居家生活",
}


def _industry_name(value: str) -> str:
    cleaned = value.strip()
    if cleaned.isdigit():
        return TWSE_INDUSTRY_CODES.get(cleaned.zfill(2), cleaned)
    return cleaned


def parse_listed_industry(payload: object) -> dict[str, str]:
    """Build code → 產業別 name from the TWSE listed-company OpenAPI payload, mapping
    numeric industry codes to names so they match the TWSE sector indices."""
    if not isinstance(payload, list):
        return {}
    out: dict[str, str] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        code = str(item.get("公司代號") or item.get("Code") or "").strip()
        sector = str(item.get("產業別") or item.get("Industry") or "").strip()
        if code and sector:
            out[code] = _industry_name(sector)
    return out


def fetch_listed_industry_map() -> dict[str, str]:
    """Code → 產業別 for TWSE-listed companies (public OpenAPI), cached for a day.
    Best-effort: returns the last good map (or empty) on any failure."""
    global _INDUSTRY_CACHE, _INDUSTRY_CACHE_AT
    now = datetime.now(UTC)
    ttl = timedelta(seconds=max(settings.twse_industry_cache_ttl_seconds, 0))
    if _INDUSTRY_CACHE and _INDUSTRY_CACHE_AT and now - _INDUSTRY_CACHE_AT <= ttl:
        return _INDUSTRY_CACHE
    try:
        with httpx.Client(timeout=settings.twse_request_timeout_seconds) as client:
            response = client.get(settings.twse_industry_url)
            response.raise_for_status()
            parsed = parse_listed_industry(response.json())
    except Exception:  # noqa: BLE001 - classification is best-effort.
        return _INDUSTRY_CACHE
    if parsed:
        _INDUSTRY_CACHE = parsed
        _INDUSTRY_CACHE_AT = now
    return _INDUSTRY_CACHE


def twse_sector_returns_from_payload(payload: dict[str, object]) -> dict[str, float]:
    """Pull every TWSE sector class index (e.g. 半導體類指數, 金融保險類指數) and its
    daily % change from the same MI_INDEX after-close report used for the TAIEX."""
    out: dict[str, float] = {}
    tables = payload.get("tables")
    candidates = tables if isinstance(tables, list) else [payload]
    for table in candidates:
        if isinstance(table, dict):
            _collect_sector_returns(out, fields=table.get("fields"), rows=table.get("data"))
    return out


def _collect_sector_returns(
    out: dict[str, float], *, fields: object, rows: object
) -> None:
    if not isinstance(fields, list) or not isinstance(rows, list):
        return
    field_map = {_normalize_header(str(field)): index for index, field in enumerate(fields)}
    name_index = _first_index(field_map, ("指數", "index", "name", "指數名稱"))
    change_pct_index = _first_index(
        field_map,
        ("漲跌百分比", "漲跌幅", "change_percent", "change_pct"),
    )
    if name_index is None or change_pct_index is None:
        return
    for row in rows:
        if not isinstance(row, list) or max(name_index, change_pct_index) >= len(row):
            continue
        name = str(row[name_index]).strip()
        if not name.endswith("類指數"):
            continue
        pct = _parse_float(row[change_pct_index])
        if pct is not None:
            out[name] = round(pct, 4)


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


def twse_benchmark_return_from_payload(
    *,
    symbol: str,
    name: str,
    payload: dict[str, object],
    as_of: date,
) -> TwseBenchmarkReturn | None:
    tables = payload.get("tables")
    if isinstance(tables, list):
        for table in tables:
            if not isinstance(table, dict):
                continue
            result = _benchmark_return_from_table(
                symbol=symbol,
                name=name,
                fields=table.get("fields"),
                rows=table.get("data"),
                as_of=as_of,
            )
            if result is not None:
                return result

    return _benchmark_return_from_table(
        symbol=symbol,
        name=name,
        fields=payload.get("fields"),
        rows=payload.get("data"),
        as_of=as_of,
    )


def _benchmark_return_from_table(
    *,
    symbol: str,
    name: str,
    fields: object,
    rows: object,
    as_of: date,
) -> TwseBenchmarkReturn | None:
    if not isinstance(fields, list) or not isinstance(rows, list):
        return None

    field_map = {_normalize_header(str(field)): index for index, field in enumerate(fields)}
    name_index = _first_index(field_map, ("指數", "index", "name", "指數名稱"))
    close_index = _first_index(field_map, ("收盤指數", "收盤價", "close", "closing_index"))
    change_pct_index = _first_index(
        field_map,
        ("漲跌百分比", "漲跌幅", "change_percent", "change_pct"),
    )
    if name_index is None or close_index is None or change_pct_index is None:
        return None

    for row in rows:
        if not isinstance(row, list):
            continue
        if max(name_index, close_index, change_pct_index) >= len(row):
            continue
        row_name = str(row[name_index]).strip()
        if not _is_taiex_name(row_name):
            continue
        close = _parse_float(row[close_index])
        return_pct = _parse_float(row[change_pct_index])
        if close is None or return_pct is None:
            continue
        previous_close = close / (1 + return_pct / 100) if return_pct != -100 else close
        return TwseBenchmarkReturn(
            symbol=symbol,
            name=name,
            trade_date=as_of.isoformat(),
            close=round(close, 4),
            previous_close=round(previous_close, 4),
            return_pct=round(return_pct, 4),
        )
    return None


def _first_index(field_map: dict[str, int], candidates: tuple[str, ...]) -> int | None:
    for candidate in candidates:
        if candidate in field_map:
            return field_map[candidate]
    return None


def _normalize_header(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("(%)", "")


def _is_taiex_name(value: str) -> bool:
    normalized = value.replace(" ", "")
    return normalized in {"發行量加權股價指數", "臺灣加權指數", "台灣加權指數", "TAIEX"}


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
