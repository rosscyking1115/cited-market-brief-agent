"use client";

import { useMemo, useState } from "react";
import { API_URL, type HoldingsParsePayload } from "@/lib/api";

const SAMPLE = `股票代號,股票名稱,持股比重,漲跌幅
2330,台積電,20.5%,1.2%
2454,聯發科,5.25%,-0.4%
2882,國泰金,4.0%,-1.0%`;

function fmt(value: number | null, suffix = "%") {
  if (value === null) return "待資料";
  return `${value.toFixed(2)}${suffix}`;
}

export default function FundHoldingsParser() {
  const [text, setText] = useState(SAMPLE);
  const [sourceName, setSourceName] = useState("JPM holdings paste");
  const [result, setResult] = useState<HoldingsParsePayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const totalWeight = useMemo(
    () => result?.holdings.reduce((sum, row) => sum + row.weight_pct, 0) ?? 0,
    [result],
  );

  async function parse() {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/fund-attribution/parse-holdings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_name: sourceName, text }),
      });
      if (!response.ok) throw new Error(`Parse failed (${response.status})`);
      setResult((await response.json()) as HoldingsParsePayload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not parse holdings");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="border-t border-hairline px-4 py-4 sm:px-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="th-label">持股表格解析</p>
          <h3 className="reader-heading mt-1 font-semibold text-neutral-30">
            先貼上 JPM 下載檔中的持股表，確認系統讀得懂
          </h3>
        </div>
        <button
          type="button"
          onClick={parse}
          disabled={busy || !text.trim()}
          className="min-h-9 rounded-(--radius-ctl) border border-action bg-action px-3 py-1.5 text-[13px] font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? "解析中..." : "解析持股"}
        </button>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(300px,0.8fr)]">
        <div>
          <label className="th-label" htmlFor="fund-source-name">
            來源名稱
          </label>
          <input
            id="fund-source-name"
            value={sourceName}
            onChange={(event) => setSourceName(event.target.value)}
            className="mt-1 w-full rounded-(--radius-ctl) border border-elevated bg-page px-3 py-2 text-[13px] text-neutral-40 outline-none focus:border-action"
          />
          <label className="th-label mt-3 block" htmlFor="fund-holdings-text">
            CSV / TSV 內容
          </label>
          <textarea
            id="fund-holdings-text"
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={7}
            className="mt-1 w-full resize-y rounded-(--radius-ctl) border border-elevated bg-page px-3 py-2 font-mono text-[12px] leading-relaxed text-neutral-40 outline-none focus:border-action"
          />
          <p className="reader-meta mt-2 text-neutral-90">
            支援常見欄位：股票代號、股票名稱、持股比重、漲跌幅，或 Ticker、Security Name、Weight (%)。
          </p>
        </div>

        <div className="rounded-(--radius-ctl) border border-hairline bg-page/50">
          <div className="border-b border-hairline px-3 py-2">
            <p className="th-label">解析結果</p>
            {result ? (
              <p className="reader-meta mt-1 text-neutral-90">
                {result.parsed_count} 檔 · 權重合計 {fmt(totalWeight)} · 略過 {result.skipped_rows} 列
              </p>
            ) : (
              <p className="reader-meta mt-1 text-neutral-90">尚未解析。</p>
            )}
          </div>

          {error && <p className="reader-body px-3 py-3 text-down">{error}</p>}

          {result?.warnings.length ? (
            <div className="border-b border-hairline px-3 py-2">
              {result.warnings.map((warning) => (
                <p key={warning} className="reader-meta text-flag">
                  {warning}
                </p>
              ))}
            </div>
          ) : null}

          <div className="max-h-72 overflow-auto">
            {result?.holdings.slice(0, 12).map((holding) => (
              <div
                key={`${holding.symbol}-${holding.name}`}
                className="grid grid-cols-[64px_1fr_auto] gap-2 border-b border-hairline px-3 py-2 last:border-b-0"
              >
                <span className="font-mono text-[12px] text-neutral-90">{holding.symbol}</span>
                <span className="reader-body truncate text-neutral-40">{holding.name}</span>
                <span className="font-mono text-[12px] text-neutral-70">
                  {fmt(holding.weight_pct)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
