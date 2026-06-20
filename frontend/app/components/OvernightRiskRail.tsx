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

function statusText(status: OvernightRiskItem["source_status"]) {
  if (status === "eod") return "每日資料";
  if (status === "delayed") return "延遲行情";
  if (status === "live") return "即時";
  return "待資料";
}

function statusClass(status: OvernightRiskItem["source_status"]) {
  if (status === "planned") return "border-elevated text-neutral-90";
  if (status === "eod") return "border-action/50 bg-action/10 text-action";
  if (status === "delayed") return "border-flag/50 bg-flag/10 text-flag";
  return "border-up/50 bg-up/10 text-up";
}

export default function OvernightRiskRail({ items }: { items: OvernightRiskItem[] }) {
  const [group, setGroup] = useState<string>(ALL_GROUPS);
  const displayItems = items.filter((item) => item.source_status !== "planned");
  const groups = useMemo(
    () => [ALL_GROUPS, ...Array.from(new Set(displayItems.map((item) => item.group)))],
    [displayItems],
  );
  const visible = displayItems.filter((item) => group === ALL_GROUPS || item.group === group);

  return (
    <section className="border-t border-hairline px-4 py-4 sm:px-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="th-label">Overnight Risk</p>
          <h2 className="reader-heading mt-1 font-semibold text-neutral-30">
            匯率、油價、VIX、利率另外看
          </h2>
          <p className="reader-meta mt-1 max-w-2xl text-neutral-90">
            只保留目前能從公開或延遲資料取得的風險訊號；付費期貨與現貨指數行情先不顯示。
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
        {visible.length === 0 && (
          <div className="rounded-(--radius-ctl) border border-hairline bg-page/50 px-3 py-3 md:col-span-2 xl:col-span-4">
            <p className="reader-body font-semibold text-neutral-40">目前沒有可顯示的隔夜風險數字</p>
            <p className="reader-meta mt-1 text-neutral-90">
              FRED 或延遲匯率資料更新後會出現在這裡；需要正式授權的指數與期貨行情已移除。
            </p>
          </div>
        )}
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
                <span
                  className={`mt-1 inline-block rounded-(--radius-ctl) border px-1.5 py-0.5 font-mono text-[10px] ${statusClass(
                    item.source_status,
                  )}`}
                >
                  {statusText(item.source_status)}
                </span>
              </div>
            </div>
            <p className="reader-meta mt-2 text-neutral-90">{item.why}</p>
            <p className="reader-meta mt-2 font-mono text-neutral-90">
              {item.source_status === "planned" ? "等待可用資料" : `source: ${item.source}`}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
