"use client";

import { useCallback, useEffect, useState } from "react";
import {
  API_URL,
  getSectorAttribution,
  type SectorAttributionPayload,
  type SectorConfigPayload,
} from "@/lib/api";

const buttonMotion =
  "transition-[background-color,border-color,box-shadow,transform] hover:shadow-md active:translate-y-px disabled:translate-y-0";

function pct(value: number | null, suffix = "%", dash = "—") {
  return value === null ? dash : `${value.toFixed(2)}${suffix}`;
}

function signed(value: number | null, dash = "—") {
  if (value === null) return dash;
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function tone(value: number | null) {
  if (value === null || value === 0) return "text-neutral-70";
  return value > 0 ? "text-up" : "text-down";
}

// "半導體,55" / "半導體 55" / "半導體\t55" -> {sector, weight_pct}
function parseWeights(text: string) {
  const rows: { sector: string; weight_pct: number }[] = [];
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const parts = trimmed.split(/[,\t]|\s{2,}|\s(?=[\d.]+%?$)/).map((p) => p.trim()).filter(Boolean);
    if (parts.length < 2) continue;
    const weight = Number(parts[parts.length - 1].replace("%", ""));
    const sector = parts.slice(0, -1).join(" ").trim();
    if (sector && Number.isFinite(weight)) rows.push({ sector, weight_pct: weight });
  }
  return rows;
}

// "2330,半導體" -> { "2330": "半導體" }
function parseMap(text: string) {
  const map: Record<string, string> = {};
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const parts = trimmed.split(/[,\t]|\s{2,}/).map((p) => p.trim()).filter(Boolean);
    if (parts.length < 2) continue;
    map[parts[0]] = parts.slice(1).join(" ").trim();
  }
  return map;
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
    try {
      const [attribution, config] = await Promise.all([
        getSectorAttribution(),
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
        body: JSON.stringify({
          taiex_weights: parseWeights(taiexText),
          sector_map: parseMap(mapText),
        }),
      });
      if (!response.ok) throw new Error(`Save failed (${response.status})`);
      setSavedMsg("已儲存。重新計算中…");
      await load();
      setSavedMsg("已儲存產業設定，之後每天自動套用。");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save sector config");
    } finally {
      setBusy(null);
    }
  }

  const rows = data?.rows ?? [];

  return (
    <section className="border-t border-hairline px-4 py-4 sm:px-5">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="th-label">產業配置比較</p>
          <h3 className="reader-heading mt-1 font-semibold text-neutral-30">
            基金的產業佈局 vs 台灣加權指數，差在哪裡
          </h3>
        </div>
        <button
          type="button"
          onClick={() => setShowEditor((v) => !v)}
          className={`min-h-9 self-start rounded-(--radius-ctl) border border-elevated bg-page px-3 py-1.5 text-[13px] font-semibold text-neutral-40 ${buttonMotion}`}
        >
          {showEditor ? "收合設定" : "設定加權指數產業權重"}
        </button>
      </div>

      {data?.summary_zh_hant && (
        <p className="reader-body mt-3 text-neutral-50">{data.summary_zh_hant}</p>
      )}

      {data?.has_benchmark && data.allocation_total_pct !== null && (
        <p className="mt-2 font-mono text-[15px] font-semibold">
          <span className="th-label mr-2 align-middle">產業配置效果合計</span>
          <span className={`align-middle ${tone(data.allocation_total_pct)}`}>
            {signed(data.allocation_total_pct)}
          </span>
        </p>
      )}

      {data && data.unmapped_weight_pct > 0.01 && (
        <p className="reader-meta mt-2 text-flag">
          有 {pct(data.unmapped_weight_pct)} 持股尚未對應到產業。上傳含「產業別」欄位的持股檔，或在下方「股票對照產業」貼上對照，即可完整計算。
        </p>
      )}

      {error && <p className="reader-body mt-3 text-down">{error}</p>}

      {rows.length > 0 && (
        <div className="mt-3 overflow-x-auto rounded-(--radius-ctl) border border-hairline bg-page/50">
          <table className="w-full min-w-[560px] border-collapse text-[13px]">
            <thead>
              <tr className="border-b border-hairline text-left">
                <th className="th-label px-3 py-2 font-normal">產業</th>
                <th className="th-label px-3 py-2 text-right font-normal">基金</th>
                <th className="th-label px-3 py-2 text-right font-normal">指數</th>
                <th className="th-label px-3 py-2 text-right font-normal">差異</th>
                <th className="th-label px-3 py-2 text-right font-normal">當日</th>
                <th className="th-label px-3 py-2 text-right font-normal">配置效果</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {rows.map((row) => (
                <tr key={row.sector}>
                  <td className="reader-body px-3 py-2 text-neutral-40">{row.sector}</td>
                  <td className="px-3 py-2 text-right font-mono text-neutral-50">{pct(row.etf_weight_pct)}</td>
                  <td className="px-3 py-2 text-right font-mono text-neutral-70">{pct(row.benchmark_weight_pct)}</td>
                  <td className={`px-3 py-2 text-right font-mono ${tone(row.weight_diff_pct)}`}>
                    {signed(row.weight_diff_pct)}
                  </td>
                  <td className={`px-3 py-2 text-right font-mono ${tone(row.sector_return_pct)}`}>
                    {signed(row.sector_return_pct)}
                  </td>
                  <td className={`px-3 py-2 text-right font-mono font-semibold ${tone(row.allocation_effect_pct)}`}>
                    {signed(row.allocation_effect_pct)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="reader-meta mt-2 text-neutral-90">
        「配置效果」= (基金權重 − 指數權重) × 該產業當日漲跌。正值代表你的產業配置相對指數有利（少配跌的、多配漲的）。
        產業當日漲跌來自 TWSE 類股指數；這是教育性績效歸因，不構成投資建議。
      </p>

      {showEditor && (
        <div className="mt-3 grid gap-3 rounded-(--radius-ctl) border border-hairline bg-page/50 px-3 py-3 lg:grid-cols-2">
          <label className="block">
            <span className="th-label">台灣加權指數產業權重（每行：產業,權重）</span>
            <textarea
              value={taiexText}
              onChange={(e) => setTaiexText(e.target.value)}
              rows={8}
              placeholder={"半導體,55\n金融保險,15\n電子零組件,8"}
              className="mt-1 w-full resize-y rounded-(--radius-ctl) border border-elevated bg-page px-3 py-2 font-mono text-[12px] leading-relaxed text-neutral-40 outline-none focus:border-action"
            />
            <span className="reader-meta mt-1 block text-neutral-90">
              從 TAIFEX/TWSE 公布的加權指數產業分布填入即可，約每月更新一次。
            </span>
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
            <span className="reader-meta mt-1 block text-neutral-90">
              只有在持股檔沒有「產業別」欄位時才需要。
            </span>
          </label>
          <div className="lg:col-span-2">
            <button
              type="button"
              onClick={save}
              disabled={busy !== null}
              className={`min-h-9 rounded-(--radius-ctl) border border-action bg-action px-4 py-1.5 text-[13px] font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50 ${buttonMotion}`}
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
