"use client";

import { useCallback, useEffect, useState } from "react";
import {
  API_URL,
  type SectorAttributionPayload,
  type SectorAttributionRow,
  type SectorConfigPayload,
} from "@/lib/api";
import { parseMap, parseWeights } from "@/lib/sector-config";

const MAX_ABS_DIFF = 4.0; // a 4pp over/underweight fills half the track

// Shown on the backend-less public demo (NEXT_PUBLIC_DEMO_MODE=1).
const DEMO_SECTOR: SectorAttributionPayload = {
  as_of: "2026-06-28",
  fund_name: "示範 ETF（範例資料）",
  benchmark_name: "台灣加權指數",
  has_benchmark: true,
  rows: [
    { sector: "半導體", etf_weight_pct: 25.75, benchmark_weight_pct: 38.0, weight_diff_pct: -12.25, sector_return_pct: -3.43, etf_contribution_pct: -0.88, allocation_effect_pct: 0.42 },
    { sector: "金融保險", etf_weight_pct: 4.0, benchmark_weight_pct: 16.0, weight_diff_pct: -12.0, sector_return_pct: -4.93, etf_contribution_pct: -0.2, allocation_effect_pct: 0.59 },
    { sector: "電信", etf_weight_pct: 6.0, benchmark_weight_pct: 3.5, weight_diff_pct: 2.5, sector_return_pct: 0.82, etf_contribution_pct: 0.05, allocation_effect_pct: 0.02 },
  ],
  allocation_total_pct: 1.03,
  unmapped_weight_pct: 0,
  summary_zh_hant: "示範資料：基金相對加權指數明顯減碼半導體與金融，今日這兩大產業下跌，因此配置效果為正。",
  source_notes: ["示範資料，僅供展示介面。"],
  disclaimer: "本頁為教育性績效歸因，不構成投資建議。",
};

function pct(value: number | null, dash = "—") {
  return value === null ? dash : `${value.toFixed(2)}%`;
}

function signed(value: number | null, decimals = 1, dash = "—") {
  if (value === null) return dash;
  return `${value >= 0 ? "+" : ""}${value.toFixed(decimals)}`;
}

function tokenColor(value: number | null) {
  if (value === null || value === 0) return "var(--color-neutral-70)";
  return value > 0 ? "var(--color-up)" : "var(--color-down)";
}

function Arrow({ up }: { up: boolean }) {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" className="inline align-[-1px]" aria-hidden>
      <path
        d={up ? "M12 19V5M12 5l-5 5M12 5l5 5" : "M12 5v14M12 19l-5-5M12 19l5-5"}
        stroke="currentColor"
        strokeWidth={2.6}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function DivergingRow({ row }: { row: SectorAttributionRow }) {
  const diff = row.weight_diff_pct;
  const day = row.sector_return_pct;
  if (diff === null) return null;
  const over = diff >= 0;
  const width = Math.min(Math.abs(diff) / MAX_ABS_DIFF, 1) * 50;
  const barColor = tokenColor(day ?? 0);
  return (
    <div className="flex items-center gap-3">
      <div className="w-[68px] shrink-0 text-right text-[13px] font-medium text-neutral-50 sm:w-[84px]">
        {row.sector}
      </div>
      <div
        className="relative h-7 flex-1 rounded-(--radius-ctl)"
        style={{ background: "color-mix(in srgb, var(--color-neutral-90) 14%, transparent)" }}
      >
        <div className="absolute inset-y-0 left-1/2 w-px" style={{ background: "var(--color-neutral-90)", opacity: 0.5 }} />
        <div
          className="absolute inset-y-1 rounded-[3px] transition-[width] duration-500"
          style={over ? { left: "50%", width: `${width}%`, background: barColor } : { right: "50%", width: `${width}%`, background: barColor }}
        />
        <span
          className="absolute top-1/2 -translate-y-1/2 font-mono text-[11.5px] font-semibold"
          style={{ ...(over ? { left: `calc(50% + ${width}% + 6px)` } : { right: `calc(50% + ${width}% + 6px)` }), color: barColor }}
        >
          {signed(diff)}
        </span>
      </div>
      <div className="w-[78px] shrink-0 text-right">
        {day !== null && (
          <span className="font-mono text-[12px]" style={{ color: barColor }}>
            <Arrow up={day >= 0} /> {signed(day, 2)}%
          </span>
        )}
      </div>
      <div className="hidden w-[72px] shrink-0 text-right md:block">
        {row.allocation_effect_pct !== null && (
          <span className="font-mono text-[13px] font-semibold" style={{ color: tokenColor(row.allocation_effect_pct) }}>
            {signed(row.allocation_effect_pct, 2)}
            <span className="text-[10px] opacity-70"> pp</span>
          </span>
        )}
      </div>
    </div>
  );
}

export default function SectorAttributionPanel() {
  const [data, setData] = useState<SectorAttributionPayload | null>(null);
  const [busy, setBusy] = useState<"load" | "save" | null>("load");
  const [error, setError] = useState<string | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const [taiexText, setTaiexText] = useState("");
  const [mapText, setMapText] = useState("");
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBusy("load");
    setError(null);
    if (process.env.NEXT_PUBLIC_DEMO_MODE === "1") {
      setData(DEMO_SECTOR);
      setBusy(null);
      return;
    }
    try {
      const [attribution, config] = await Promise.all([
        // Same-origin /api proxy: this runs in the browser, so it must not use the
        // server-only API origin (which points at localhost from the viewer's machine).
        fetch(`${API_URL}/fund-attribution/sector-attribution`, { cache: "no-store" })
          .then((r) => (r.ok ? (r.json() as Promise<SectorAttributionPayload>) : null))
          .catch(() => null),
        fetch(`${API_URL}/fund-attribution/sector-config`, { cache: "no-store" })
          .then((r) => (r.ok ? (r.json() as Promise<SectorConfigPayload>) : null))
          .catch(() => null),
      ]);
      setData(attribution);
      if (config) {
        if (config.taiex_weights.length && !taiexText) {
          setTaiexText(config.taiex_weights.map((w) => `${w.sector},${w.weight_pct}`).join("\n"));
        }
        const mapEntries = Object.entries(config.sector_map);
        if (mapEntries.length && !mapText) {
          setMapText(mapEntries.map(([code, sector]) => `${code},${sector}`).join("\n"));
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load sector attribution");
    } finally {
      setBusy(null);
    }
  }, [taiexText, mapText]);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function save() {
    setBusy("save");
    setError(null);
    setSavedMsg(null);
    try {
      const response = await fetch(`${API_URL}/fund-attribution/sector-config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ taiex_weights: parseWeights(taiexText), sector_map: parseMap(mapText) }),
      });
      if (!response.ok) throw new Error(`Save failed (${response.status})`);
      await load();
      setSavedMsg("已儲存產業設定，之後每天自動套用。");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save sector config");
    } finally {
      setBusy(null);
    }
  }

  const rows = data?.rows ?? [];
  const hasBenchmark = data?.has_benchmark ?? false;
  const divergingRows = rows.filter((r) => r.weight_diff_pct !== null);

  return (
    <section className="mt-10">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-serif text-[20px] font-semibold text-neutral-30">產業配置比較</h2>
          <p className="reader-meta mt-0.5 text-neutral-70">基金相對加權指數的產業加減碼 · 色彩依今日產業漲跌</p>
        </div>
        <button
          type="button"
          onClick={() => setShowEditor((v) => !v)}
          className="inline-flex cursor-pointer items-center gap-1.5 text-[13px] font-medium text-action"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
            <path d="M4 7h16M4 12h16M4 17h10" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" />
          </svg>
          編輯指數權重
        </button>
      </div>

      {data?.summary_zh_hant && <p className="reader-body mt-3 text-neutral-50">{data.summary_zh_hant}</p>}

      {hasBenchmark && data?.allocation_total_pct !== null && data?.allocation_total_pct !== undefined && (
        <p className="mt-2 font-mono text-[15px] font-semibold">
          <span className="th-label mr-2 align-middle">產業配置效果合計</span>
          <span className="align-middle" style={{ color: tokenColor(data.allocation_total_pct) }}>
            {signed(data.allocation_total_pct, 2)} pp
          </span>
        </p>
      )}

      {data && data.unmapped_weight_pct > 0.01 && (
        <p className="reader-meta mt-2 text-flag">
          有 {pct(data.unmapped_weight_pct)} 持股尚未對應到產業（多為現金或上櫃股）。可於下方「股票對照產業」補上。
        </p>
      )}

      {error && <p className="reader-body mt-3 text-down">{error}</p>}

      {/* Diverging-bar viz (primary) */}
      {hasBenchmark && divergingRows.length > 0 && (
        <div className="mt-3 rounded-(--radius-card) border border-hairline bg-card p-4 shadow-[var(--shadow-soft)] sm:p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4 text-[12px] text-neutral-70">
              <span className="inline-flex items-center gap-1.5">
                <span className="inline-block h-2.5 w-2.5 rounded-[2px]" style={{ background: "var(--color-up)" }} />產業今日上漲
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="inline-block h-2.5 w-2.5 rounded-[2px]" style={{ background: "var(--color-down)" }} />產業今日下跌
              </span>
            </div>
            <div className="hidden w-[200px] items-center justify-between text-[11px] font-medium text-neutral-90 sm:flex">
              <span>← 減碼</span>
              <span>加碼 →</span>
            </div>
          </div>
          <div className="mt-4 space-y-2.5">
            {divergingRows.map((row) => (
              <DivergingRow key={row.sector} row={row} />
            ))}
          </div>
        </div>
      )}

      {/* Detail table (secondary) */}
      {rows.length > 0 && (
        <div className="mt-3 overflow-hidden rounded-(--radius-card) border border-hairline bg-card shadow-[var(--shadow-soft)]">
          <table className="hidden w-full sm:table">
            <thead>
              <tr className="border-b border-hairline">
                <th className="th-label px-4 py-2.5 text-left font-normal">產業</th>
                <th className="th-label px-4 py-2.5 text-right font-normal">基金</th>
                <th className="th-label px-4 py-2.5 text-right font-normal">指數</th>
                <th className="th-label px-4 py-2.5 text-right font-normal">差異</th>
                <th className="th-label px-4 py-2.5 text-right font-normal">當日</th>
                <th className="th-label px-4 py-2.5 text-right font-normal">配置效果</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {rows.map((row) => (
                <tr key={row.sector} className="transition-colors hover:bg-action/[0.05]">
                  <td className="px-4 py-3 text-[14px] font-medium text-neutral-30">{row.sector}</td>
                  <td className="px-4 py-3 text-right font-mono text-[13.5px] text-neutral-50">{pct(row.etf_weight_pct)}</td>
                  <td className="px-4 py-3 text-right font-mono text-[13.5px] text-neutral-70">{pct(row.benchmark_weight_pct)}</td>
                  <td className="px-4 py-3 text-right font-mono text-[13.5px] font-semibold" style={{ color: tokenColor(row.weight_diff_pct) }}>
                    {signed(row.weight_diff_pct)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-[13.5px]" style={{ color: tokenColor(row.sector_return_pct) }}>
                    {row.sector_return_pct === null ? "—" : (<><Arrow up={row.sector_return_pct >= 0} /> {signed(row.sector_return_pct, 2)}%</>)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-[14px] font-semibold" style={{ color: tokenColor(row.allocation_effect_pct) }}>
                    {row.allocation_effect_pct === null ? "—" : (<>{signed(row.allocation_effect_pct, 2)}<span className="text-[10px] opacity-70">pp</span></>)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Mobile stacked cards */}
          <div className="divide-y divide-hairline sm:hidden">
            {rows.map((row) => (
              <div key={row.sector} className="p-4">
                <div className="flex items-center justify-between">
                  <span className="text-[15px] font-semibold text-neutral-30">{row.sector}</span>
                  <span className="font-mono text-[15px] font-semibold" style={{ color: tokenColor(row.allocation_effect_pct) }}>
                    配置效果 {row.allocation_effect_pct === null ? "—" : (<>{signed(row.allocation_effect_pct, 2)}<span className="text-[10px] opacity-70">pp</span></>)}
                  </span>
                </div>
                <div className="reader-meta mt-2 flex items-center justify-between text-neutral-70">
                  <span>
                    基金 <span className="font-mono text-neutral-50">{pct(row.etf_weight_pct)}</span> · 指數 <span className="font-mono">{pct(row.benchmark_weight_pct)}</span>
                  </span>
                  <span className="font-mono" style={{ color: tokenColor(row.weight_diff_pct) }}>差異 {signed(row.weight_diff_pct)}</span>
                </div>
                <div className="reader-meta mt-1 text-neutral-70">
                  當日 <span className="font-mono" style={{ color: tokenColor(row.sector_return_pct) }}>
                    {row.sector_return_pct === null ? "—" : (<><Arrow up={row.sector_return_pct >= 0} /> {signed(row.sector_return_pct, 2)}%</>)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="reader-meta mt-2 text-neutral-90">
        「配置效果」= (基金權重 − 指數權重) × 該產業當日漲跌。正值代表配置相對指數有利（少配跌的、多配漲的）。
        產業漲跌來自 TWSE 類股指數。指數產業權重目前為概略預設值，可在右上「編輯指數權重」依 TAIFEX 校準。
        本頁為教育性績效歸因，不構成投資建議。
      </p>

      {!hasBenchmark && rows.length > 0 && (
        <p className="reader-meta mt-2 text-action">設定加權指數產業權重後，即可看到「指數」「差異」與配置效果。按右上角「編輯指數權重」。</p>
      )}

      {/* Set-once weights editor (tucked away) */}
      {showEditor && (
        <div className="mt-3 rounded-(--radius-card) border border-hairline bg-card p-4 shadow-[var(--shadow-soft)] sm:p-5">
          <h3 className="text-[14px] font-semibold text-neutral-30">加權指數產業權重（設定一次）</h3>
          <p className="reader-meta mt-1 text-neutral-70">從 TAIFEX/TWSE 公布的產業分布填入，約每月更新一次；設定後自動沿用。</p>
          <div className="mt-3 grid gap-3 lg:grid-cols-2">
            <label className="block">
              <span className="th-label">加權指數產業權重（每行：產業,權重）</span>
              <textarea
                value={taiexText}
                onChange={(e) => setTaiexText(e.target.value)}
                rows={8}
                placeholder={"半導體,38.5\n金融保險,16.8\n電子零組件,8.1"}
                className="mt-1 w-full resize-y rounded-(--radius-ctl) border border-elevated bg-page px-3 py-2 font-mono text-[12px] leading-relaxed text-neutral-40 outline-none focus:border-action"
              />
            </label>
            <label className="block">
              <span className="th-label">股票對照產業（選填，每行：代號,產業）</span>
              <textarea
                value={mapText}
                onChange={(e) => setMapText(e.target.value)}
                rows={8}
                placeholder={"2330,半導體\n2882,金融保險"}
                className="mt-1 w-full resize-y rounded-(--radius-ctl) border border-elevated bg-page px-3 py-2 font-mono text-[12px] leading-relaxed text-neutral-40 outline-none focus:border-action"
              />
            </label>
          </div>
          <div className="mt-3">
            <button
              type="button"
              onClick={save}
              disabled={busy !== null}
              className="min-h-9 cursor-pointer rounded-(--radius-ctl) bg-action px-4 py-1.5 text-[13px] font-semibold text-white transition-[transform,box-shadow] hover:shadow-[var(--shadow-lift)] active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50"
            >
              {busy === "save" ? "儲存中…" : "儲存並重新計算"}
            </button>
            {savedMsg && <span className="reader-meta ml-3 text-up">{savedMsg}</span>}
          </div>
        </div>
      )}
    </section>
  );
}
