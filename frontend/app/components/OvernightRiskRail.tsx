"use client";

import { useMemo, useState } from "react";
import type { OvernightRiskItem, SnapshotTone } from "@/lib/api";

const ALL_GROUPS = "全部";

const GROUP_LABELS: Record<OvernightRiskItem["group"], string> = {
  futures: "期貨",
  volatility: "波動",
  fx: "匯率",
  commodities: "商品",
  rates: "利率",
};

function toneClass(tone: SnapshotTone) {
  if (tone === "up") return "text-up";
  if (tone === "down") return "text-down";
  if (tone === "pending") return "text-flag";
  return "text-neutral-70";
}

export default function OvernightRiskRail({ items }: { items: OvernightRiskItem[] }) {
  const [group, setGroup] = useState<string>(ALL_GROUPS);
  const groups = useMemo(
    () => [ALL_GROUPS, ...Array.from(new Set(items.map((item) => item.group)))],
    [items],
  );
  const visible = items.filter((item) => group === ALL_GROUPS || item.group === group);

  return (
    <section className="border-t border-hairline px-4 py-4 sm:px-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="th-label">Overnight Risk</p>
          <h2 className="reader-heading mt-1 font-semibold text-neutral-30">
            期貨、匯率、油金、VIX、利率另外看
          </h2>
          <p className="reader-meta mt-1 max-w-2xl text-neutral-90">
            這些不是現貨股市指數；它們常在台灣早上提供隔夜風險情緒，但需確認行情授權。
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {groups.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setGroup(item)}
              aria-pressed={group === item}
              className={`min-h-8 rounded-(--radius-ctl) border px-2.5 py-1 text-[12px] font-medium ${
                group === item
                  ? "border-action bg-action text-white"
                  : "border-elevated text-neutral-70 hover:border-action hover:text-neutral-30"
              }`}
            >
              {item === ALL_GROUPS ? item : GROUP_LABELS[item as OvernightRiskItem["group"]]}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {visible.map((item) => (
          <article key={item.symbol} className="rounded-(--radius-ctl) border border-hairline bg-page/50 px-3 py-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="th-label">{GROUP_LABELS[item.group]}</p>
                <h3 className="reader-body mt-1 truncate font-semibold text-neutral-40">
                  {item.local_name}
                </h3>
                <p className="reader-meta mt-0.5 truncate font-mono text-neutral-90">
                  {item.symbol} · {item.name}
                </p>
              </div>
              <div className="text-right">
                <p className={`font-mono text-[15px] font-semibold ${toneClass(item.tone)}`}>
                  {item.value}
                </p>
                <p className="reader-meta text-neutral-90">{item.source_status}</p>
              </div>
            </div>
            <p className="reader-meta mt-2 text-neutral-90">{item.why}</p>
            <p className="reader-meta mt-2 font-mono text-neutral-90">{item.rights_note}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
