import csv
import io
import re
from datetime import date

from app.connectors.twse import TwseClient
from app.fund_attribution.schemas import (
    AttributionRow,
    AutomationPolicyItem,
    BenchmarkReturnOut,
    BenchmarkReturnRequest,
    FundAttributionOut,
    FundAttributionPlanOut,
    FundAttributionRequest,
    HoldingInput,
    HoldingReturnFillOut,
    HoldingReturnFillRequest,
    HoldingsParseOut,
    HoldingsParseRequest,
)

DISCLAIMER = "本頁提供績效歸因與教育資訊，不構成個人化投資建議或買賣建議。"

COLUMN_ALIASES = {
    "symbol": {
        "symbol",
        "ticker",
        "ticker_symbol",
        "stock_code",
        "code",
        "sedol",
        "isin",
        "ric",
        "代號",
        "股票代號",
        "證券代號",
        "標的代號",
    },
    "name": {
        "name",
        "security",
        "security_name",
        "holding",
        "holdings",
        "company",
        "issuer",
        "description",
        "名稱",
        "股票名稱",
        "證券名稱",
        "持股名稱",
        "基金資產股票",
    },
    "weight_pct": {
        "weight",
        "weight_pct",
        "weight_percent",
        "weighting",
        "percent",
        "pct",
        "of_nav",
        "nav_percent",
        "market_value_percent",
        "權重",
        "比重",
        "持股比重",
        "占比",
        "淨資產百分比",
    },
    "return_pct": {
        "return",
        "return_pct",
        "return_percent",
        "daily_return",
        "daily_return_pct",
        "漲跌幅",
        "報酬率",
        "日報酬",
        "當日報酬",
    },
}


def automation_policy() -> list[AutomationPolicyItem]:
    return [
        AutomationPolicyItem(
            label="JPM ETF holdings file",
            status="manual_first",
            note=(
                "先支援使用者上傳官網下載的持股檔；自動下載前需確認 JPM 頁面條款與機器存取方式。"
            ),
        ),
        AutomationPolicyItem(
            label="TWSE after-close prices",
            status="allowed",
            note="台股每日收盤後可用官方公開資料抓取個股收盤價；需保留來源、時間與快取紀錄。",
        ),
        AutomationPolicyItem(
            label="TAIEX benchmark close",
            status="needs_review",
            note="可用官方或授權來源做每日比較；公開產品前需確認指數顯示/再發布條款。",
        ),
        AutomationPolicyItem(
            label="Intraday attribution",
            status="blocked",
            note="盤中即時歸因通常需要正式行情授權；第一版只做每日收盤後分析。",
        ),
    ]


def attribution_plan() -> FundAttributionPlanOut:
    return FundAttributionPlanOut(
        title="ETF / Fund vs Benchmark Attribution",
        target_use_case="每天收盤後回答：基金和大盤表現差在哪裡，哪些持股造成差異。",
        first_region="Taiwan",
        daily_trigger="台股收盤後，等 TWSE/JPM 資料更新再跑。",
        required_inputs=[
            "ETF 持股、權重與持股日期",
            "ETF 當日報酬率或淨值/收盤價",
            "台灣加權指數當日報酬率",
            "每個持股的當日報酬率",
        ],
        first_supported_workflow=[
            "先讓使用者上傳 JPM 官網下載的持股檔",
            "系統抓 TWSE 收盤價並計算每檔持股報酬",
            "用權重 x 報酬計算貢獻",
            "輸出贏/輸大盤原因、最大貢獻、最大拖累、無法解釋殘差",
        ],
        automation_policy=automation_policy(),
        disclaimer=DISCLAIMER,
    )


def parse_holdings_text(request: HoldingsParseRequest) -> HoldingsParseOut:
    rows, detected_columns = _read_tabular_text(request.text)
    warnings: list[str] = []
    skipped = 0
    holdings: list[HoldingInput] = []

    if not rows:
        return HoldingsParseOut(
            source_name=request.source_name,
            parsed_count=0,
            skipped_rows=0,
            detected_columns=detected_columns,
            holdings=[],
            warnings=["找不到可解析的持股表格。請貼上 CSV/TSV 或從試算表複製完整表格。"],
            source_notes=[f"source: {request.source_name}", "manual holdings parse"],
        )

    for index, row in enumerate(rows, start=1):
        symbol = _clean_text(row.get("symbol"))
        name = _clean_text(row.get("name"))
        weight = _parse_percent(row.get("weight_pct"))
        return_pct = _parse_percent(row.get("return_pct"))

        if not symbol and name:
            symbol = _infer_symbol(name)
        if not name and symbol:
            name = symbol
        if not name or weight is None:
            skipped += 1
            continue

        holdings.append(
            HoldingInput(
                symbol=symbol or f"ROW-{index}",
                name=name,
                weight_pct=weight,
                return_pct=return_pct,
            )
        )

    if not holdings:
        warnings.append("沒有成功解析任何持股；請確認欄位包含名稱與權重。")
    if skipped:
        warnings.append(f"已略過 {skipped} 列缺少名稱或權重的資料。")

    return HoldingsParseOut(
        source_name=request.source_name,
        parsed_count=len(holdings),
        skipped_rows=skipped,
        detected_columns=detected_columns,
        holdings=holdings,
        warnings=warnings,
        source_notes=[f"source: {request.source_name}", "manual holdings parse"],
    )


def fill_holding_returns_from_twse(request: HoldingReturnFillRequest) -> HoldingReturnFillOut:
    as_of = _parse_iso_date(request.as_of)
    if as_of is None:
        return HoldingReturnFillOut(
            as_of=request.as_of,
            filled_count=0,
            missing_symbols=[holding.symbol for holding in request.holdings],
            holdings=request.holdings,
            warnings=["日期格式需要是 YYYY-MM-DD。"],
            source_notes=["TWSE after-close return fill skipped"],
        )

    client = TwseClient()
    holdings: list[HoldingInput] = []
    missing: list[str] = []
    warnings: list[str] = []
    filled = 0
    try:
        for holding in request.holdings:
            symbol = _normalize_twse_symbol(holding.symbol)
            if not symbol:
                holdings.append(holding)
                missing.append(holding.symbol)
                continue
            try:
                daily_return = client.stock_daily_return(symbol=symbol, as_of=as_of)
            except Exception as exc:  # noqa: BLE001 - source failures should not break manual flow.
                warnings.append(f"{symbol} TWSE 取價失敗：{exc}")
                holdings.append(holding)
                missing.append(holding.symbol)
                continue
            if daily_return is None:
                holdings.append(holding)
                missing.append(holding.symbol)
                continue
            holdings.append(holding.model_copy(update={"return_pct": daily_return.return_pct}))
            filled += 1
    finally:
        client.close()

    if missing:
        warnings.append(f"有 {len(missing)} 檔沒有補到 TWSE 漲跌幅，仍可手動填入。")

    return HoldingReturnFillOut(
        as_of=as_of.isoformat(),
        filled_count=filled,
        missing_symbols=missing,
        holdings=holdings,
        warnings=warnings,
        source_notes=[
            "source: TWSE afterTrading STOCK_DAY",
            "returns calculated from latest available close and previous close",
        ],
    )


def benchmark_return_from_twse(request: BenchmarkReturnRequest) -> BenchmarkReturnOut:
    as_of = _parse_iso_date(request.as_of)
    if as_of is None:
        return BenchmarkReturnOut(
            as_of=request.as_of,
            benchmark=request.benchmark,
            name="台灣加權指數",
            return_pct=None,
            close=None,
            previous_close=None,
            warnings=["日期格式需要是 YYYY-MM-DD。"],
            source_notes=["TWSE benchmark return skipped"],
        )

    client = TwseClient()
    warnings: list[str] = []
    try:
        try:
            value = client.taiex_return(as_of=as_of)
        except Exception as exc:  # noqa: BLE001 - keep manual benchmark fallback available.
            value = None
            warnings.append(f"TAIEX TWSE 取價失敗：{exc}")
    finally:
        client.close()

    if value is None:
        warnings.append("沒有補到台灣加權指數漲跌幅，仍可手動填入。")
        return BenchmarkReturnOut(
            as_of=as_of.isoformat(),
            benchmark=request.benchmark,
            name="台灣加權指數",
            return_pct=None,
            close=None,
            previous_close=None,
            warnings=warnings,
            source_notes=["source: TWSE afterTrading MI_INDEX"],
        )

    return BenchmarkReturnOut(
        as_of=value.trade_date,
        benchmark=value.symbol,
        name=value.name,
        return_pct=value.return_pct,
        close=value.close,
        previous_close=value.previous_close,
        warnings=warnings,
        source_notes=[
            "source: TWSE afterTrading MI_INDEX",
            "benchmark return from TWSE reported index percentage change",
        ],
    )


def analyze_fund_attribution(request: FundAttributionRequest) -> FundAttributionOut:
    rows = [_row_from_holding(holding) for holding in request.holdings]
    explained_return = sum(row.contribution_pct or 0 for row in rows)
    active_return = request.fund_return_pct - request.benchmark_return_pct
    residual = request.fund_return_pct - explained_return

    contributors = sorted(
        [row for row in rows if (row.contribution_pct or 0) > 0],
        key=lambda row: row.contribution_pct or 0,
        reverse=True,
    )[:5]
    drags = sorted(
        [row for row in rows if (row.contribution_pct or 0) < 0],
        key=lambda row: row.contribution_pct or 0,
    )[:5]
    missing = [row for row in rows if row.direction == "missing"]

    return FundAttributionOut(
        fund_name=request.fund_name,
        benchmark_name=request.benchmark_name,
        as_of=request.as_of,
        fund_return_pct=round(request.fund_return_pct, 4),
        benchmark_return_pct=round(request.benchmark_return_pct, 4),
        active_return_pct=round(active_return, 4),
        explained_return_pct=round(explained_return, 4),
        residual_pct=round(residual, 4),
        holdings_count=len(request.holdings),
        contributors=contributors,
        drags=drags,
        missing_returns=missing,
        source_notes=request.source_notes,
        automation_policy=automation_policy(),
        summary_zh_hant=_summary_zh(
            fund_name=request.fund_name,
            benchmark_name=request.benchmark_name,
            fund_return=request.fund_return_pct,
            benchmark_return=request.benchmark_return_pct,
            active_return=active_return,
            contributors=contributors,
            drags=drags,
        ),
        disclaimer=DISCLAIMER,
    )


def _read_tabular_text(text: str) -> tuple[list[dict[str, str]], list[str]]:
    lines = [line for line in text.replace("\ufeff", "").splitlines() if line.strip()]
    if not lines:
        return [], []

    delimiter = _guess_delimiter(lines)
    reader = csv.reader(io.StringIO("\n".join(lines)), delimiter=delimiter)
    raw_rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not raw_rows:
        return [], []

    header_index, field_map = _find_header(raw_rows)
    if header_index is None:
        return [], []

    headers = [cell.strip() for cell in raw_rows[header_index]]
    parsed_rows: list[dict[str, str]] = []
    for raw in raw_rows[header_index + 1 :]:
        normalized: dict[str, str] = {}
        for source_idx, target in field_map.items():
            if source_idx < len(raw):
                normalized[target] = raw[source_idx].strip()
        if normalized:
            parsed_rows.append(normalized)
    return parsed_rows, headers


def _guess_delimiter(lines: list[str]) -> str:
    candidates = [",", "\t", ";", "|"]
    sample = "\n".join(lines[:8])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="".join(candidates))
        return dialect.delimiter
    except csv.Error:
        return max(
            candidates,
            key=lambda delimiter: sum(line.count(delimiter) for line in lines[:8]),
        )


def _find_header(rows: list[list[str]]) -> tuple[int | None, dict[int, str]]:
    best_index: int | None = None
    best_map: dict[int, str] = {}
    best_score = 0
    for index, row in enumerate(rows[:20]):
        field_map: dict[int, str] = {}
        for cell_index, cell in enumerate(row):
            target = _field_for_header(cell)
            if target:
                field_map[cell_index] = target
        score = len(set(field_map.values()))
        if score > best_score and {"name", "weight_pct"}.issubset(set(field_map.values())):
            best_index = index
            best_map = field_map
            best_score = score
    return best_index, best_map


def _field_for_header(value: str) -> str | None:
    normalized = _normalize_header(value)
    for target, aliases in COLUMN_ALIASES.items():
        if normalized in aliases:
            return target
    return None


def _normalize_header(value: str) -> str:
    cleaned = value.strip().lower()
    cleaned = cleaned.replace("%", " percent ")
    cleaned = re.sub(r"[\s/().\-]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned


def _clean_text(value: str | None) -> str:
    return (value or "").strip().strip('"').strip()


def _parse_percent(value: str | None) -> float | None:
    cleaned = _clean_text(value)
    if not cleaned or cleaned in {"-", "--", "N/A", "n/a"}:
        return None
    cleaned = cleaned.replace("%", "").replace(",", "").replace("％", "").strip()
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = f"-{cleaned[1:-1]}"
    try:
        return round(float(cleaned), 6)
    except ValueError:
        return None


def _parse_iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _normalize_twse_symbol(value: str) -> str:
    match = re.search(r"\b[0-9]{4,6}\b", value)
    return match.group(0) if match else ""


def _infer_symbol(name: str) -> str:
    match = re.search(r"\b[0-9]{4,6}\b", name)
    if match:
        return match.group(0)
    return ""


def _row_from_holding(holding: HoldingInput) -> AttributionRow:
    if holding.return_pct is None:
        return AttributionRow(
            symbol=holding.symbol,
            name=holding.name,
            weight_pct=round(holding.weight_pct, 4),
            return_pct=None,
            contribution_pct=None,
            direction="missing",
        )

    contribution = holding.weight_pct * holding.return_pct / 100
    if contribution > 0:
        direction = "positive"
    elif contribution < 0:
        direction = "negative"
    else:
        direction = "flat"
    return AttributionRow(
        symbol=holding.symbol,
        name=holding.name,
        weight_pct=round(holding.weight_pct, 4),
        return_pct=round(holding.return_pct, 4),
        contribution_pct=round(contribution, 4),
        direction=direction,
    )


def _summary_zh(
    *,
    fund_name: str,
    benchmark_name: str,
    fund_return: float,
    benchmark_return: float,
    active_return: float,
    contributors: list[AttributionRow],
    drags: list[AttributionRow],
) -> str:
    relation = "贏過" if active_return >= 0 else "落後"
    leader = contributors[0].name if contributors else "主要持股"
    laggard = drags[0].name if drags else "部分持股或現金部位"
    return (
        f"{fund_name} 當日報酬 {fund_return:+.2f}%，{benchmark_name} {benchmark_return:+.2f}%，"
        f"相對表現 {active_return:+.2f} 個百分點，今天{relation}基準。"
        f"主要正貢獻來自 {leader}；主要拖累來自 {laggard}。"
    )
