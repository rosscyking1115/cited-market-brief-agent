import re
from datetime import datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from app.connectors.alpha_vantage import AlphaMarketValue
from app.connectors.bbc import BbcArticle
from app.connectors.gdelt import GdeltArticle
from app.market_radar.schemas import (
    GlossaryItem,
    MarketClockItem,
    MarketSnapshotItem,
    MarketStatus,
    MarketStoryItem,
    MorningRadarOut,
    OvernightRiskItem,
    PopularNewsItem,
    SnapshotTone,
)
from app.sources.policy import source_policy

TAIPEI_TZ = ZoneInfo("Asia/Taipei")
type RiskGroup = Literal["futures", "volatility", "fx", "commodities", "rates"]

BUSINESS_CATEGORIES = {"business", "economy", "money"}
MARKET_TOKENS = {
    "ai",
    "bank",
    "banks",
    "brent",
    "chip",
    "chips",
    "copper",
    "crude",
    "currency",
    "dollar",
    "earnings",
    "economy",
    "equities",
    "fed",
    "gold",
    "inflation",
    "market",
    "markets",
    "nvidia",
    "oil",
    "profit",
    "profits",
    "rate",
    "rates",
    "revenue",
    "semiconductor",
    "semiconductors",
    "stocks",
    "tariff",
    "tariffs",
    "trade",
    "tsmc",
    "wti",
    "yen",
    "yield",
    "yields",
}
MARKET_PHRASES = {
    "central bank",
    "federal reserve",
    "interest rate",
    "strait of hormuz",
    "wall street",
}


def _status_for(
    minutes: int, windows: list[tuple[int, int]], *, weekend: bool
) -> MarketStatus:
    if weekend:
        return "weekend"
    if any(start <= minutes < end for start, end in windows):
        return "open"
    if len(windows) == 2 and windows[0][1] <= minutes < windows[1][0]:
        return "lunch"
    if minutes < windows[0][0]:
        return "not_open"
    return "closed"


def _status_text(status: MarketStatus) -> str:
    return {
        "open": "盤中",
        "lunch": "午休",
        "closed": "已收盤",
        "weekend": "週末",
        "not_open": "未開盤",
    }[status]


def _market_clock(now: datetime) -> list[MarketClockItem]:
    local = now.astimezone(TAIPEI_TZ)
    minutes = local.hour * 60 + local.minute
    weekend = local.weekday() >= 5
    return [
        MarketClockItem(
            market="日本",
            label="日經225 / TOPIX",
            window="08:00-10:30, 11:30-14:30",
            status=_status_for(
                minutes,
                [(8 * 60, 10 * 60 + 30), (11 * 60 + 30, 14 * 60 + 30)],
                weekend=weekend,
            ),
            note="亞洲第一棒，先看科技與匯率。",
        ),
        MarketClockItem(
            market="韓國",
            label="KOSPI / KOSDAQ",
            window="08:00-14:30",
            status=_status_for(minutes, [(8 * 60, 14 * 60 + 30)], weekend=weekend),
            note="記憶體、電池、出口股參考。",
        ),
        MarketClockItem(
            market="台灣",
            label="加權指數 / 台指期",
            window="09:00-13:30",
            status=_status_for(minutes, [(9 * 60, 13 * 60 + 30)], weekend=weekend),
            note="開盤前先看台幣、台指期與半導體。",
        ),
        MarketClockItem(
            market="香港 / A股",
            label="恆生 / 上證 / 滬深300",
            window="09:30-12:00, 13:00-16:00",
            status=_status_for(
                minutes,
                [(9 * 60 + 30, 12 * 60), (13 * 60, 16 * 60)],
                weekend=weekend,
            ),
            note="中國需求、政策與港股科技股。",
        ),
        MarketClockItem(
            market="歐洲",
            label="Stoxx 600 / DAX / FTSE 100",
            window="夏令約 15:00 後",
            status=_status_for(minutes, [(15 * 60, 23 * 60 + 30)], weekend=weekend),
            note="下午接力觀察歐股與歐元。",
        ),
        MarketClockItem(
            market="美國",
            label="道瓊 / 標普500 / 那斯達克",
            window="夏令 21:30-04:00",
            status=(
                "weekend"
                if weekend
                else "open"
                if minutes < 4 * 60 or minutes >= 21 * 60 + 30
                else "closed"
            ),
            note="台灣早上主要看昨晚收盤與期貨。",
        ),
    ]


def _snapshots() -> list[MarketSnapshotItem]:
    return [
        MarketSnapshotItem(
            label="Oil / Gold",
            local_name="油價 / 黃金",
            value="待資料",
            change="有 FRED/授權商品資料時顯示",
            tone="pending",
            source="FRED / licensed metals feed required",
        ),
        MarketSnapshotItem(
            label="USD/TWD",
            local_name="美元 / 台幣",
            value="待資料",
            change="有延遲匯率資料時顯示",
            tone="pending",
            source="FX feed required",
        ),
        MarketSnapshotItem(
            label="US10Y",
            local_name="美國 10 年債",
            value="待資料",
            change="有 FRED 資料時顯示",
            tone="pending",
            source="FRED",
        ),
    ]


def hydrate_snapshots_with_alpha(
    rows: list[MarketSnapshotItem],
    values: dict[str, AlphaMarketValue],
) -> list[MarketSnapshotItem]:
    hydrated: list[MarketSnapshotItem] = []
    for row in rows:
        value = _alpha_value_for_snapshot(row.label, values)
        if value is None:
            hydrated.append(row)
            continue

        updated = {
            "value": _format_market_value(value.symbol, value.value),
            "change": _format_market_change(value),
            "tone": _tone_for_change(value.change),
            "source": value.source,
            "source_status": value.source_status,
        }
        if row.label == "Oil / Gold":
            updated["local_name"] = "WTI 原油 / 黃金"
            updated["change"] = _snapshot_pair_change(
                primary_label="WTI",
                primary=value,
                secondary_label="黃金",
                secondary=values.get("XAU"),
            )
        hydrated.append(row.model_copy(update=updated))
    return hydrated


def build_snapshots(
    alpha_values: dict[str, AlphaMarketValue] | None = None,
    *,
    include_planned: bool = False,
) -> list[MarketSnapshotItem]:
    rows = _snapshots()
    if not alpha_values:
        return rows if include_planned else []
    hydrated = hydrate_snapshots_with_alpha(rows, alpha_values)
    if include_planned:
        return hydrated
    return [row for row in hydrated if row.source_status != "planned"]


def _alpha_value_for_snapshot(
    label: str,
    values: dict[str, AlphaMarketValue],
) -> AlphaMarketValue | None:
    return {
        "Oil / Gold": values.get("WTI"),
        "USD/TWD": values.get("USD/TWD"),
        "US10Y": values.get("US10Y"),
    }.get(label)


def _snapshot_pair_change(
    *,
    primary_label: str,
    primary: AlphaMarketValue,
    secondary_label: str,
    secondary: AlphaMarketValue | None,
) -> str:
    if secondary:
        secondary_text = f"{secondary_label} {_format_market_change(secondary)}"
    else:
        secondary_text = f"{secondary_label} 待接入"
    return f"{primary_label} {_format_market_change(primary)}；{secondary_text}"


def _stories() -> list[MarketStoryItem]:
    return [
        MarketStoryItem(
            title="先看隔夜美股、歐股，再看亞洲開盤順序。",
            why="早上需要的是全球市場脈絡，不是只看單一公司或單一產業。",
            tag="新版主軸",
        ),
        MarketStoryItem(
            title="油金、美元、利率放在同一排看。",
            why="商品、匯率與利率常一起影響風險情緒，但不直接代表可以買賣。",
            tag="市場背景",
        ),
        MarketStoryItem(
            title="公司新聞要分成美股、歐股、亞洲與台灣供應鏈。",
            why="避免只看美國半導體，改成全球市場與產業鏈一起讀。",
            tag="內容擴充",
        ),
    ]


def _placeholder_popular_news() -> list[PopularNewsItem]:
    bbc_policy = source_policy("bbc_rss")
    gdelt_policy = source_policy("gdelt_doc")
    return [
        PopularNewsItem(
            rank=1,
            title="BBC latest headlines connector pending",
            title_zh_hant="BBC 最新新聞接入待確認",
            source=bbc_policy.display_name,
            window="1h",
            rank_kind="latest",
            source_status=bbc_policy.source_status,
            category="全球",
            why=(
                "BBC 公開 RSS 可作為最新新聞來源候選，但不能標示為閱讀最多，"
                "除非取得官方人氣資料或授權。"
            ),
            rights_note=bbc_policy.rights_note,
        ),
        PopularNewsItem(
            rank=2,
            title="GDELT trending cluster connector pending",
            title_zh_hant="GDELT 熱門/最多報導新聞群組待接入",
            source=gdelt_policy.display_name,
            window="1h",
            rank_kind="trending",
            source_status=gdelt_policy.source_status,
            category="市場",
            why="可用來源數、來源多樣性與首頁位置推估熱門程度，但這不是實際閱讀量。",
            rights_note=gdelt_policy.rights_note,
        ),
        PopularNewsItem(
            rank=1,
            title="Most covered global market stories connector pending",
            title_zh_hant="24 小時全球市場最多報導新聞待接入",
            source=gdelt_policy.display_name,
            window="24h",
            rank_kind="most_covered",
            source_status=gdelt_policy.source_status,
            category="全球市場",
            why="24 小時窗口適合整理跨媒體重複出現的重大新聞。",
            rights_note="Most covered is not most read; label must stay precise.",
        ),
        PopularNewsItem(
            rank=2,
            title="NYT Most Popular can provide source-specific 24h popularity",
            title_zh_hant="NYT 可作為單一來源 24 小時熱門新聞候選",
            source="New York Times",
            window="24h",
            rank_kind="most_viewed",
            source_status="official_api",
            category="國際",
            why="NYT Most Popular 是乾淨的官方人氣 API 範例，但只代表 NYT，不代表全網。",
            rights_note="Requires NYT API key and compliance with NYT developer terms.",
        ),
    ]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _has_phrase(text: str, phrases: set[str]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def _market_category(title: str) -> str:
    tokens = _tokens(title)
    if tokens & {"oil", "gold", "brent", "wti", "copper", "crude"} or _has_phrase(
        title, {"strait of hormuz"}
    ):
        return "商品"
    if tokens & {"ai", "semiconductor", "semiconductors", "chip", "chips", "nvidia", "tsmc"}:
        return "半導體"
    if tokens & {
        "inflation",
        "fed",
        "rate",
        "rates",
        "yield",
        "yields",
        "tariff",
        "tariffs",
        "trade",
        "dollar",
        "yen",
        "currency",
    } or _has_phrase(title, {"central bank", "federal reserve", "interest rate"}):
        return "宏觀"
    if tokens & {"earnings", "revenue", "profit", "profits"}:
        return "公司"
    return "市場"


def _is_market_relevant_bbc(article: BbcArticle) -> bool:
    category = (article.category or "").strip().lower()
    if category in BUSINESS_CATEGORIES:
        return True
    tokens = _tokens(article.title)
    return bool(tokens & MARKET_TOKENS) or _has_phrase(article.title, MARKET_PHRASES)


def _gdelt_news_rows(
    *,
    articles: list[GdeltArticle],
    window: Literal["1h", "24h"],
    rank_kind: Literal["most_covered", "trending"],
    limit: int,
) -> list[PopularNewsItem]:
    rows: list[PopularNewsItem] = []
    policy = source_policy("gdelt_doc")
    for rank, article in enumerate(articles[:limit], start=1):
        rows.append(
            PopularNewsItem(
                rank=rank,
                title=article.title,
                title_zh_hant=article.title,
                source=article.domain,
                url=article.url,
                published_at=article.seendate,
                window=window,
                rank_kind=rank_kind,
                source_status=policy.source_status,
                category=_market_category(article.title),
                why="GDELT 在此時間窗找到的市場相關新聞；這是趨勢/覆蓋度訊號，不是閱讀量。",
                rights_note=policy.rights_note,
            )
        )
    return rows


def _bbc_latest_rows(
    *,
    articles: list[BbcArticle],
    now: datetime,
    window: Literal["1h", "24h"],
    limit: int,
) -> list[PopularNewsItem]:
    policy = source_policy("bbc_rss")
    window_delta = timedelta(hours=1) if window == "1h" else timedelta(hours=24)
    cutoff = now.astimezone(TAIPEI_TZ) - window_delta
    rows: list[PopularNewsItem] = []
    for article in articles:
        if article.published_at is None:
            continue
        if not _is_market_relevant_bbc(article):
            continue
        published = article.published_at.astimezone(TAIPEI_TZ)
        if published < cutoff:
            continue
        rows.append(
            PopularNewsItem(
                rank=len(rows) + 1,
                title=article.title,
                title_zh_hant=article.title,
                source=policy.display_name,
                url=article.url,
                published_at=published.isoformat(),
                window=window,
                rank_kind="latest",
                source_status=policy.source_status,
                category=_market_category(article.title),
                why="BBC RSS 在此時間窗內發布的最新新聞；這不是閱讀量排名。",
                rights_note=policy.rights_note,
            )
        )
        if len(rows) >= limit:
            break
    return rows


def popular_news_from_bbc(
    *,
    articles: list[BbcArticle],
    now: datetime | None = None,
) -> list[PopularNewsItem]:
    local_now = now or datetime.now(TAIPEI_TZ)
    one_hour = _bbc_latest_rows(articles=articles, now=local_now, window="1h", limit=6)
    day = _bbc_latest_rows(articles=articles, now=local_now, window="24h", limit=8)
    return [*one_hour, *day]


def normalize_popular_news_ranks(items: list[PopularNewsItem]) -> list[PopularNewsItem]:
    counters = {"1h": 0, "24h": 0}
    normalized: list[PopularNewsItem] = []
    for item in items:
        counters[item.window] += 1
        normalized.append(item.model_copy(update={"rank": counters[item.window]}))
    return normalized


def popular_news_from_gdelt(
    *,
    last_hour: list[GdeltArticle],
    last_day: list[GdeltArticle],
) -> list[PopularNewsItem]:
    rows = [
        *_gdelt_news_rows(
            articles=last_hour,
            window="1h",
            rank_kind="trending",
            limit=12,
        ),
        *_gdelt_news_rows(
            articles=last_day,
            window="24h",
            rank_kind="most_covered",
            limit=24,
        ),
    ]
    return rows or _placeholder_popular_news()


def _overnight_risk() -> list[OvernightRiskItem]:
    rows: list[tuple[str, str, str, RiskGroup, str]] = [
        (
            "VIX",
            "CBOE Volatility Index",
            "VIX 波動率指數",
            "volatility",
            "避險與市場波動壓力參考。",
        ),
        (
            "USD/TWD",
            "US dollar / Taiwan dollar",
            "美元兌台幣",
            "fx",
            "影響台股電子與出口股情緒。",
        ),
        (
            "USD/JPY",
            "US dollar / Japanese yen",
            "美元兌日圓",
            "fx",
            "日本股市、出口股與亞洲匯率參考。",
        ),
        (
            "USD/CNY",
            "US dollar / Chinese yuan",
            "美元兌人民幣（CNY）",
            "fx",
            "中國與香港市場風險情緒參考；FRED 提供 CNY，不是離岸 CNH。",
        ),
        (
            "USD-BROAD",
            "Nominal Broad U.S. Dollar Index",
            "廣義美元指數",
            "fx",
            "美元強弱會影響商品、亞洲匯率與資金流；這是 FRED 廣義美元指數，不是 ICE DXY。",
        ),
        (
            "WTI",
            "WTI crude oil",
            "WTI 原油",
            "commodities",
            "油價影響通膨、能源股與市場風險情緒。",
        ),
        (
            "XAU",
            "Gold spot",
            "黃金",
            "commodities",
            "避險與實質利率情緒參考。",
        ),
        (
            "US10Y",
            "US 10-year Treasury yield",
            "美國 10 年債殖利率",
            "rates",
            "利率變化會影響科技股估值與美元。",
        ),
    ]
    return [
        OvernightRiskItem(
            rank=rank,
            symbol=symbol,
            name=name,
            local_name=local_name,
            group=group,
            value="待資料",
            change="公開或延遲資料更新後顯示",
            tone="pending",
            source="public/delayed source pending",
            why=why,
            rights_note="Show only when a usable public, delayed, or licensed source is available.",
        )
        for rank, (symbol, name, local_name, group, why) in enumerate(rows, start=1)
    ]


def hydrate_overnight_risk_with_alpha(
    rows: list[OvernightRiskItem],
    values: dict[str, AlphaMarketValue],
) -> list[OvernightRiskItem]:
    hydrated: list[OvernightRiskItem] = []
    for row in rows:
        value = values.get(row.symbol)
        if value is None:
            hydrated.append(row)
            continue
        hydrated.append(
            row.model_copy(
                update={
                    "value": _format_market_value(row.symbol, value.value),
                    "change": _format_market_change(value),
                    "tone": _tone_for_change(value.change),
                    "source": value.source,
                    "source_status": value.source_status,
                    "rights_note": (
                        f"{value.source} pilot feed; review plan/terms before public display."
                    ),
                }
            )
        )
    return hydrated


def build_overnight_risk(
    alpha_values: dict[str, AlphaMarketValue] | None = None,
    *,
    include_planned: bool = False,
) -> list[OvernightRiskItem]:
    rows = _overnight_risk()
    if not alpha_values:
        return rows if include_planned else []
    hydrated = hydrate_overnight_risk_with_alpha(rows, alpha_values)
    if include_planned:
        return hydrated
    return [row for row in hydrated if row.source_status != "planned"]


def _format_market_value(symbol: str, value: float) -> str:
    if symbol in {"US10Y"}:
        return f"{value:.2f}%"
    if symbol in {"WTI", "XAU"}:
        return f"{value:.2f}"
    if symbol in {"USD/JPY", "USD/TWD", "USD/CNY"}:
        return f"{value:.4f}"
    return f"{value:.2f}"


def _format_market_change(value: AlphaMarketValue) -> str:
    if value.change is None:
        suffix = f" · {value.updated_at}" if value.updated_at else ""
        return f"latest{suffix}"

    pct = f", {value.change_pct:+.2f}%" if value.change_pct is not None else ""
    suffix = f" · {value.updated_at}" if value.updated_at else ""
    return f"{value.change:+.2f}{pct}{suffix}"


def _tone_for_change(change: float | None) -> SnapshotTone:
    if change is None:
        return "flat"
    if change > 0:
        return "up"
    if change < 0:
        return "down"
    return "flat"


def _glossary() -> list[GlossaryItem]:
    return [
        GlossaryItem(
            term="費半",
            english="PHLX Semiconductor Index",
            meaning="美國主要半導體股票指數，常被用來觀察 AI 與晶片族群氣氛。",
        ),
        GlossaryItem(
            term="VIX",
            english="Volatility Index",
            meaning="市場恐慌與避險情緒指標，數字升高通常代表波動變大。",
        ),
        GlossaryItem(
            term="殖利率",
            english="Treasury yield",
            meaning="債券市場利率。美債殖利率上升時，成長股與科技股常會承壓。",
        ),
        GlossaryItem(
            term="期貨",
            english="Futures",
            meaning="現貨市場開盤前的參考價格，不等於正式開盤結果。",
        ),
        GlossaryItem(
            term="ADR",
            english="American Depositary Receipt",
            meaning="海外公司在美國交易的存託憑證，可作為台積電等公司隔夜參考。",
        ),
    ]


def build_morning_radar(
    now: datetime | None = None,
    popular_news: list[PopularNewsItem] | None = None,
    snapshots: list[MarketSnapshotItem] | None = None,
    overnight_risk: list[OvernightRiskItem] | None = None,
) -> MorningRadarOut:
    generated_at = now or datetime.now(TAIPEI_TZ)
    market_clock = _market_clock(generated_at)
    current = (
        next((item for item in market_clock if item.status == "open"), None)
        or next((item for item in market_clock if item.status == "not_open"), None)
        or market_clock[0]
    )
    return MorningRadarOut(
        generated_at=generated_at.astimezone(TAIPEI_TZ).isoformat(),
        headline="今天先看全球市場，再看台股開盤",
        summary_points=[
            "美股與歐股收盤先決定隔夜基調。",
            "08:00 先看日本、韓國；09:00 接台股。",
            "油金、美元、利率用來判斷風險情緒，不作買賣建議。",
        ],
        current_focus=f"{current.market} · {_status_text(current.status)}",
        market_clock=market_clock,
        snapshots=snapshots or build_snapshots(),
        popular_news=popular_news or _placeholder_popular_news(),
        overnight_risk=overnight_risk or build_overnight_risk(),
        stories=_stories(),
        glossary=_glossary(),
        disclaimer="本頁提供市場資訊與教育內容，不構成個人化投資建議或買賣建議。",
    )
