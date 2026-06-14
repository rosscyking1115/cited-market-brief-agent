import type { ChangesPayload } from "@/lib/api";

type MarketTile = {
  label: string;
  value: string;
  detail: string;
  tone: "up" | "down" | "flat" | "flag";
};

function formatNumber(value: number | null) {
  if (value == null) return "—";
  return Math.abs(value) >= 100 ? value.toLocaleString("en-US", { maximumFractionDigits: 1 }) : value.toFixed(2);
}

function seriesLabel(seriesId: string) {
  return (
    {
      CPIAUCSL: "美國 CPI",
      DGS10: "美國 10 年債",
      VIXCLS: "VIX 波動率",
      DCOILWTICO: "WTI 原油",
      DEXJPUS: "美元/日圓",
      DEXCHUS: "美元/人民幣",
      DTWEXBGS: "廣義美元",
      TOTBKCR: "美國銀行信貸",
      GASREGW: "美國汽油",
    }[seriesId] ?? seriesId
  );
}

function macroTiles(changes: ChangesPayload): MarketTile[] {
  const tiles = changes.macro_deltas.slice(0, 4).map((delta) => {
    const change = delta.change;
    return {
      label: seriesLabel(delta.series_id),
      value: formatNumber(delta.latest_value),
      detail:
        change == null
          ? delta.latest_date ?? "最新"
          : `${change >= 0 ? "+" : "-"}${formatNumber(Math.abs(change))}${delta.change_pct != null ? ` (${Math.abs(delta.change_pct).toFixed(2)}%)` : ""}`,
      tone: change == null ? "flat" : change >= 0 ? "up" : "down",
    } satisfies MarketTile;
  });

  if (tiles.length > 0) return tiles;

  return [
    { label: "新增公司文件", value: String(changes.new_documents.length), detail: "SEC EDGAR", tone: changes.new_documents.length ? "flag" : "flat" },
    { label: "公司文件變化", value: String(changes.filing_diffs.length), detail: "和上次相比", tone: changes.filing_diffs.length ? "flag" : "flat" },
  ];
}

function toneClass(tone: MarketTile["tone"]) {
  if (tone === "up") return "text-up";
  if (tone === "down") return "text-down";
  if (tone === "flag") return "text-flag";
  return "text-neutral-70";
}

export default function MarketContextStrip({ changes }: { changes: ChangesPayload }) {
  const tiles = macroTiles(changes);

  return (
    <section className="overflow-hidden rounded-(--radius-card) border border-hairline bg-card">
      <div className="flex flex-col gap-2 border-b border-hairline px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="th-label">昨天到今天的資料更新</p>
          <h2 className="reader-heading mt-1 text-[15px] font-semibold text-neutral-30">
            這裡只放「真的有新資料」的總經與公司文件訊號
          </h2>
        </div>
        <p className="reader-meta max-w-xl text-[11px] leading-relaxed text-neutral-90">
          如果數字有變或公司申報有新文件，這裡會提醒；沒有變化時，就把注意力留給新聞與市場雷達。
        </p>
      </div>
      <div className="grid grid-cols-2 divide-x divide-y divide-hairline sm:grid-cols-4 sm:divide-y-0">
        {tiles.map((tile) => (
          <div key={tile.label} className="min-w-0 px-4 py-3">
            <p className="th-label truncate">{tile.label}</p>
            <p className={`mt-1 font-mono text-[18px] font-semibold ${toneClass(tile.tone)}`}>{tile.value}</p>
            <p className="reader-meta mt-0.5 truncate font-mono text-[10px] text-neutral-90">{tile.detail}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
