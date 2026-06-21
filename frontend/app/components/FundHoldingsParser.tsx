"use client";

import { useMemo, useState } from "react";
import {
  API_URL,
  type AttributionRow,
  type BenchmarkReturnPayload,
  type FundAttributionPayload,
  type HoldingReturnFillPayload,
  type HoldingsParsePayload,
} from "@/lib/api";

const SAMPLE = `股票代號,股票名稱,持股比重,漲跌幅
2330,台積電,20.5%,1.2%
2454,聯發科,5.25%,-0.4%
2882,國泰金,4.0%,-1.0%`;

const buttonMotion =
  "transition-[background-color,border-color,box-shadow,transform] hover:shadow-md active:translate-y-px disabled:translate-y-0 disabled:hover:shadow-none";

function fmt(value: number | null, suffix = "%", nullLabel = "缺資料") {
  if (value === null) return nullLabel;
  return `${value.toFixed(2)}${suffix}`;
}

function signed(value: number) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function arrayBufferToBase64(buffer: ArrayBuffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let index = 0; index < bytes.byteLength; index += 1) {
    binary += String.fromCharCode(bytes[index]);
  }
  return window.btoa(binary);
}

function rowTone(row: AttributionRow) {
  if (row.direction === "positive") return "text-up";
  if (row.direction === "negative") return "text-down";
  if (row.direction === "missing") return "text-flag";
  return "text-neutral-70";
}

function ResultRows({ title, rows }: { title: string; rows: AttributionRow[] }) {
  return (
    <div className="rounded-(--radius-ctl) border border-hairline bg-page/50">
      <div className="border-b border-hairline px-3 py-2">
        <p className="th-label">{title}</p>
      </div>
      {rows.length ? (
        <div className="divide-y divide-hairline">
          {rows.map((row) => (
            <div key={`${title}-${row.symbol}-${row.name}`} className="grid grid-cols-[58px_1fr_auto] gap-2 px-3 py-2">
              <span className="font-mono text-[12px] text-neutral-90">{row.symbol}</span>
              <div className="min-w-0">
                <p className="reader-body truncate text-neutral-40">{row.name}</p>
                <p className="reader-meta text-neutral-90">
                  權重 {fmt(row.weight_pct)} · 漲跌 {fmt(row.return_pct, "%", "缺漲跌幅")}
                </p>
              </div>
              <span className={`font-mono text-[12px] font-semibold ${rowTone(row)}`}>
                {row.contribution_pct === null ? "缺漲跌幅" : signed(row.contribution_pct)}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="reader-meta px-3 py-3 text-neutral-90">沒有資料。</p>
      )}
    </div>
  );
}

export default function FundHoldingsParser() {
  const [text, setText] = useState(SAMPLE);
  const [sourceName, setSourceName] = useState("JPM holdings paste");
  const [fundName, setFundName] = useState("主動摩根台灣鑫收益ETF");
  const [benchmarkName, setBenchmarkName] = useState("台灣加權指數");
  const [asOf, setAsOf] = useState(new Date().toISOString().slice(0, 10));
  const [fundReturn, setFundReturn] = useState("0.42");
  const [benchmarkReturn, setBenchmarkReturn] = useState("0.18");
  const [parseResult, setParseResult] = useState<HoldingsParsePayload | null>(null);
  const [analysis, setAnalysis] = useState<FundAttributionPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"parse" | "upload" | "fill" | "benchmark" | "analyze" | null>(null);

  const totalWeight = useMemo(
    () => parseResult?.holdings.reduce((sum, row) => sum + row.weight_pct, 0) ?? 0,
    [parseResult],
  );

  async function parse() {
    setBusy("parse");
    setError(null);
    setAnalysis(null);
    try {
      const response = await fetch(`${API_URL}/fund-attribution/parse-holdings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_name: sourceName, text }),
      });
      if (!response.ok) throw new Error(`Parse failed (${response.status})`);
      applyParseResult((await response.json()) as HoldingsParsePayload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not parse holdings");
    } finally {
      setBusy(null);
    }
  }

  async function parseWorkbook(file: File) {
    setBusy("upload");
    setError(null);
    setAnalysis(null);
    try {
      const contentBase64 = arrayBufferToBase64(await file.arrayBuffer());
      const response = await fetch(`${API_URL}/fund-attribution/parse-holdings-file`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: file.name,
          source_name: file.name,
          content_base64: contentBase64,
        }),
      });
      if (!response.ok) throw new Error(`File parse failed (${response.status})`);
      setSourceName(file.name);
      applyParseResult((await response.json()) as HoldingsParsePayload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not parse uploaded workbook");
    } finally {
      setBusy(null);
    }
  }

  function applyParseResult(payload: HoldingsParsePayload) {
    setParseResult(payload);
    if (payload.as_of) setAsOf(payload.as_of);
    if (payload.fund_name) setFundName(payload.fund_name);
  }

  async function analyze() {
    if (!parseResult?.holdings.length) return;
    const fundReturnPct = Number(fundReturn);
    const benchmarkReturnPct = Number(benchmarkReturn);
    if (!Number.isFinite(fundReturnPct) || !Number.isFinite(benchmarkReturnPct)) {
      setError("請輸入基金與台灣加權指數的漲跌幅數字。");
      return;
    }

    setBusy("analyze");
    setError(null);
    try {
      const response = await fetch(`${API_URL}/fund-attribution/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fund_name: fundName,
          benchmark_name: benchmarkName,
          as_of: asOf,
          fund_return_pct: fundReturnPct,
          benchmark_return_pct: benchmarkReturnPct,
          holdings: parseResult.holdings,
          source_notes: parseResult.source_notes,
        }),
      });
      if (!response.ok) throw new Error(`Analyze failed (${response.status})`);
      setAnalysis((await response.json()) as FundAttributionPayload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not analyze attribution");
    } finally {
      setBusy(null);
    }
  }

  async function fillReturnsFromTwse() {
    if (!parseResult?.holdings.length) return;
    setBusy("fill");
    setError(null);
    setAnalysis(null);
    try {
      const response = await fetch(`${API_URL}/fund-attribution/fill-returns/twse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ as_of: asOf, holdings: parseResult.holdings }),
      });
      if (!response.ok) throw new Error(`TWSE fill failed (${response.status})`);
      const payload = (await response.json()) as HoldingReturnFillPayload;
      setParseResult({
        ...parseResult,
        holdings: payload.holdings,
        warnings: [...parseResult.warnings, ...payload.warnings],
        source_notes: [...parseResult.source_notes, ...payload.source_notes],
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not fill returns from TWSE");
    } finally {
      setBusy(null);
    }
  }

  async function fillBenchmarkFromTwse() {
    setBusy("benchmark");
    setError(null);
    setAnalysis(null);
    try {
      const response = await fetch(`${API_URL}/fund-attribution/benchmark-return/twse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ as_of: asOf, benchmark: "TAIEX" }),
      });
      if (!response.ok) throw new Error(`TWSE benchmark failed (${response.status})`);
      const payload = (await response.json()) as BenchmarkReturnPayload;
      if (payload.return_pct === null) {
        setError(payload.warnings[0] ?? "沒有補到台灣加權指數漲跌幅。");
        return;
      }
      setBenchmarkName(payload.name);
      setBenchmarkReturn(String(payload.return_pct));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not fill benchmark from TWSE");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="border-t border-hairline px-4 py-4 sm:px-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="th-label">持股歸因試算</p>
          <h3 className="reader-heading mt-1 font-semibold text-neutral-30">
            貼上持股後，直接看基金和台灣加權指數差在哪裡
          </h3>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={parse}
            disabled={busy !== null || !text.trim()}
            className={`min-h-9 rounded-(--radius-ctl) border border-action bg-action px-3 py-1.5 text-[13px] font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50 ${buttonMotion}`}
          >
            {busy === "parse" ? "解析中..." : "解析持股"}
          </button>
          <button
            type="button"
            onClick={fillReturnsFromTwse}
            disabled={busy !== null || !parseResult?.holdings.length}
            className={`min-h-9 rounded-(--radius-ctl) border border-elevated bg-page px-3 py-1.5 text-[13px] font-semibold text-neutral-40 disabled:cursor-not-allowed disabled:opacity-50 ${buttonMotion}`}
          >
            {busy === "fill" ? "補資料中..." : "用 TWSE 補漲跌幅"}
          </button>
          <button
            type="button"
            onClick={analyze}
            disabled={busy !== null || !parseResult?.holdings.length}
            className={`min-h-9 rounded-(--radius-ctl) border border-up bg-up px-3 py-1.5 text-[13px] font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50 ${buttonMotion}`}
          >
            {busy === "analyze" ? "分析中..." : "分析差異"}
          </button>
        </div>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.8fr)]">
        <div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="th-label">基金名稱</span>
              <input
                value={fundName}
                onChange={(event) => setFundName(event.target.value)}
                className="mt-1 w-full rounded-(--radius-ctl) border border-elevated bg-page px-3 py-2 text-[13px] text-neutral-40 outline-none focus:border-action"
              />
            </label>
            <label className="block">
              <span className="th-label">比較基準</span>
              <input
                value={benchmarkName}
                onChange={(event) => setBenchmarkName(event.target.value)}
                className="mt-1 w-full rounded-(--radius-ctl) border border-elevated bg-page px-3 py-2 text-[13px] text-neutral-40 outline-none focus:border-action"
              />
            </label>
            <label className="block">
              <span className="th-label">日期</span>
              <input
                type="date"
                value={asOf}
                onChange={(event) => setAsOf(event.target.value)}
                className="mt-1 w-full rounded-(--radius-ctl) border border-elevated bg-page px-3 py-2 text-[13px] text-neutral-40 outline-none focus:border-action"
              />
            </label>
            <label className="block">
              <span className="th-label">來源名稱</span>
              <input
                value={sourceName}
                onChange={(event) => setSourceName(event.target.value)}
                className="mt-1 w-full rounded-(--radius-ctl) border border-elevated bg-page px-3 py-2 text-[13px] text-neutral-40 outline-none focus:border-action"
              />
            </label>
            <label className="block">
              <span className="th-label">基金當日漲跌幅 %</span>
              <input
                inputMode="decimal"
                value={fundReturn}
                onChange={(event) => setFundReturn(event.target.value)}
                className="mt-1 w-full rounded-(--radius-ctl) border border-elevated bg-page px-3 py-2 font-mono text-[13px] text-neutral-40 outline-none focus:border-action"
              />
            </label>
            <label className="block">
              <span className="th-label">台灣加權指數漲跌幅 %</span>
              <div className="mt-1 grid grid-cols-[minmax(0,1fr)_auto] gap-2">
                <input
                  inputMode="decimal"
                  value={benchmarkReturn}
                  onChange={(event) => setBenchmarkReturn(event.target.value)}
                  className="w-full rounded-(--radius-ctl) border border-elevated bg-page px-3 py-2 font-mono text-[13px] text-neutral-40 outline-none focus:border-action"
                />
                <button
                  type="button"
                  onClick={fillBenchmarkFromTwse}
                  disabled={busy !== null}
                  className={`rounded-(--radius-ctl) border border-elevated bg-page px-2 py-1.5 text-[12px] font-semibold text-neutral-40 disabled:cursor-not-allowed disabled:opacity-50 ${buttonMotion}`}
                >
                  {busy === "benchmark" ? "補中" : "TWSE"}
                </button>
              </div>
            </label>
          </div>

          <label className="th-label mt-3 block">上傳 JPM Excel 檔（.xlsx / .xls）</label>
          <div className="mt-1 rounded-(--radius-ctl) border border-dashed border-elevated bg-page px-3 py-3">
            <input
              type="file"
              accept=".xlsx,.xls"
              disabled={busy !== null}
              onChange={(event) => {
                const file = event.currentTarget.files?.[0];
                event.currentTarget.value = "";
                if (file) void parseWorkbook(file);
              }}
              className="w-full text-[13px] text-neutral-70 file:mr-3 file:rounded-(--radius-ctl) file:border file:border-elevated file:bg-surface file:px-3 file:py-1.5 file:text-[13px] file:font-semibold file:text-neutral-40 file:transition-shadow file:hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
            />
            <p className="reader-meta mt-2 text-neutral-90">
              支援 JPMAM 下載的投資組合 Excel；會讀取「基金資產 - 股票」中的股票代碼、股票名稱與權重。
            </p>
            {busy === "upload" && <p className="reader-meta mt-1 text-action">Excel 解析中...</p>}
          </div>

          <label className="th-label mt-3 block" htmlFor="fund-holdings-text">
            或手動貼上 CSV / TSV 內容
          </label>
          <textarea
            id="fund-holdings-text"
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={8}
            className="mt-1 w-full resize-y rounded-(--radius-ctl) border border-elevated bg-page px-3 py-2 font-mono text-[12px] leading-relaxed text-neutral-40 outline-none focus:border-action"
          />
          <p className="reader-meta mt-2 text-neutral-90">
            支援常見欄位：股票代號、股票名稱、持股比重、漲跌幅，或 Ticker、Security Name、Weight (%)。
          </p>
        </div>

        <div className="rounded-(--radius-ctl) border border-hairline bg-page/50">
          <div className="border-b border-hairline px-3 py-2">
            <p className="th-label">解析結果</p>
            {parseResult ? (
              <div className="mt-1 space-y-1">
                <p className="reader-meta text-neutral-90">
                  {parseResult.parsed_count} 檔 · 權重合計 {fmt(totalWeight)} · 略過 {parseResult.skipped_rows} 列
                </p>
                <p className="reader-meta text-neutral-90">
                  「缺漲跌幅」代表已讀到持股與權重，但還沒有該股票當日漲跌幅；按 TWSE 補資料後才可計算貢獻。
                </p>
              </div>
            ) : (
              <p className="reader-meta mt-1 text-neutral-90">尚未解析。</p>
            )}
          </div>

          {error && <p className="reader-body px-3 py-3 text-down">{error}</p>}

          {parseResult?.warnings.length ? (
            <div className="border-b border-hairline px-3 py-2">
              {parseResult.warnings.map((warning) => (
                <p key={warning} className="reader-meta text-flag">
                  {warning}
                </p>
              ))}
            </div>
          ) : null}

          <div className="max-h-72 overflow-auto">
            {parseResult?.holdings.slice(0, 12).map((holding) => (
              <div
                key={`${holding.symbol}-${holding.name}`}
                className="grid grid-cols-[64px_1fr_auto] gap-2 border-b border-hairline px-3 py-2 last:border-b-0"
              >
                <span className="font-mono text-[12px] text-neutral-90">{holding.symbol}</span>
                <span className="reader-body truncate text-neutral-40">{holding.name}</span>
                <span className="text-right font-mono text-[12px] text-neutral-70">
                  {fmt(holding.weight_pct)}
                  <br />
                  <span className={holding.return_pct === null ? "text-flag" : "text-neutral-90"}>
                    {fmt(holding.return_pct, "%", "缺漲跌幅")}
                  </span>
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {analysis && (
        <section className="mt-4 border-t border-hairline pt-4">
          <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_360px]">
            <div className="rounded-(--radius-ctl) border border-hairline bg-page/50 px-4 py-4">
              <p className="th-label">分析結論</p>
              <p className="reader-heading mt-2 font-semibold text-neutral-30">{analysis.summary_zh_hant}</p>
              <div className="mt-3 grid gap-2 sm:grid-cols-3">
                <div>
                  <p className="th-label">相對表現</p>
                  <p className={`mt-1 font-mono text-[18px] font-semibold ${analysis.active_return_pct >= 0 ? "text-up" : "text-down"}`}>
                    {signed(analysis.active_return_pct)}
                  </p>
                </div>
                <div>
                  <p className="th-label">持股解釋</p>
                  <p className="mt-1 font-mono text-[18px] font-semibold text-neutral-40">
                    {signed(analysis.explained_return_pct)}
                  </p>
                </div>
                <div>
                  <p className="th-label">無法解釋殘差</p>
                  <p className="mt-1 font-mono text-[18px] font-semibold text-flag">
                    {signed(analysis.residual_pct)}
                  </p>
                </div>
              </div>
              <p className="reader-meta mt-3 text-neutral-90">{analysis.disclaimer}</p>
            </div>

            <div className="rounded-(--radius-ctl) border border-hairline bg-page/50 px-4 py-4">
              <p className="th-label">讀法</p>
              <p className="reader-body mt-2 text-neutral-70">
                正貢獻代表該持股推升基金表現；負貢獻代表拖累。殘差通常來自現金、未填報酬率、費用、權重日期和價格日期不同。
              </p>
            </div>
          </div>

          <div className="mt-3 grid gap-3 lg:grid-cols-3">
            <ResultRows title="最大正貢獻" rows={analysis.contributors} />
            <ResultRows title="最大拖累" rows={analysis.drags} />
            <ResultRows title="缺少漲跌幅" rows={analysis.missing_returns.slice(0, 5)} />
          </div>
        </section>
      )}
    </div>
  );
}
