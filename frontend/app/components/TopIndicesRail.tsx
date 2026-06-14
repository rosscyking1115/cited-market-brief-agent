"use client";

import { useEffect, useMemo, useState } from "react";
import type { SnapshotTone, TopIndexItem } from "@/lib/api";

const STORAGE_KEY = "cmb-top-indices-v1";
const ALL_REGIONS = "全部";

type Preferences = {
  pinned: string[];
  hidden: string[];
};

function toneClass(tone: SnapshotTone) {
  if (tone === "up") return "text-up";
  if (tone === "down") return "text-down";
  if (tone === "pending") return "text-flag";
  return "text-neutral-70";
}

function readPreferences(): Preferences {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { pinned: [], hidden: [] };
    const parsed = JSON.parse(raw) as Partial<Preferences>;
    return {
      pinned: Array.isArray(parsed.pinned) ? parsed.pinned.filter(Boolean) : [],
      hidden: Array.isArray(parsed.hidden) ? parsed.hidden.filter(Boolean) : [],
    };
  } catch {
    return { pinned: [], hidden: [] };
  }
}

function savePreferences(preferences: Preferences) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
}

export default function TopIndicesRail({ items }: { items: TopIndexItem[] }) {
  const [preferences, setPreferences] = useState<Preferences>({ pinned: [], hidden: [] });
  const [region, setRegion] = useState(ALL_REGIONS);
  const [showHidden, setShowHidden] = useState(false);

  useEffect(() => {
    setPreferences(readPreferences());
  }, []);

  function updatePreferences(next: Preferences) {
    setPreferences(next);
    savePreferences(next);
  }

  function togglePinned(symbol: string) {
    const pinned = preferences.pinned.includes(symbol)
      ? preferences.pinned.filter((item) => item !== symbol)
      : [symbol, ...preferences.pinned];
    updatePreferences({ ...preferences, pinned });
  }

  function toggleHidden(symbol: string) {
    const hidden = preferences.hidden.includes(symbol)
      ? preferences.hidden.filter((item) => item !== symbol)
      : [symbol, ...preferences.hidden];
    const pinned = preferences.pinned.filter((item) => item !== symbol);
    updatePreferences({ pinned, hidden });
  }

  function reset() {
    updatePreferences({ pinned: [], hidden: [] });
    setRegion(ALL_REGIONS);
    setShowHidden(false);
  }

  const regions = useMemo(
    () => [ALL_REGIONS, ...Array.from(new Set(items.map((item) => item.region)))],
    [items],
  );

  const visibleItems = useMemo(() => {
    const filtered = items.filter((item) => {
      if (region !== ALL_REGIONS && item.region !== region) return false;
      if (!showHidden && preferences.hidden.includes(item.symbol)) return false;
      return true;
    });
    return [...filtered].sort((a, b) => {
      const aPinned = preferences.pinned.includes(a.symbol);
      const bPinned = preferences.pinned.includes(b.symbol);
      if (aPinned !== bPinned) return aPinned ? -1 : 1;
      return a.rank - b.rank;
    });
  }, [items, preferences.hidden, preferences.pinned, region, showHidden]);

  const groupedRegions = Array.from(new Set(visibleItems.map((item) => item.region)));
  const hiddenCount = preferences.hidden.length;

  return (
    <section className="border-t border-hairline px-4 py-4 sm:px-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="th-label">Top 20 指數</p>
          <h2 className="reader-heading mt-1 font-semibold text-neutral-30">
            先看現貨股市指數；把不需要的藏起來
          </h2>
          <p className="reader-meta mt-1 max-w-2xl text-neutral-90">
            偏好設定只存在這台裝置。期貨、油金、匯率會放在另一條 Overnight Risk rail。
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {regions.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setRegion(item)}
              aria-pressed={region === item}
              className={`min-h-8 rounded-(--radius-ctl) border px-2.5 py-1 text-[12px] font-medium ${
                region === item
                  ? "border-action bg-action text-white"
                  : "border-elevated text-neutral-70 hover:border-action hover:text-neutral-30"
              }`}
            >
              {item}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setShowHidden((current) => !current)}
            aria-pressed={showHidden}
            title="Show or hide hidden indices"
            className={`min-h-8 min-w-8 rounded-(--radius-ctl) border px-2 py-1 font-mono text-[12px] ${
              showHidden
                ? "border-flag bg-flag text-white"
                : "border-elevated text-neutral-70 hover:border-flag hover:text-flag"
            }`}
          >
            {showHidden ? "◉" : "○"}
          </button>
          <button
            type="button"
            onClick={reset}
            className="min-h-8 rounded-(--radius-ctl) border border-elevated px-2.5 py-1 text-[12px] font-medium text-neutral-70 hover:border-action hover:text-neutral-30"
          >
            Reset
          </button>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <span className="rounded-(--radius-ctl) border border-elevated px-2 py-1 font-mono text-[10px] text-neutral-90">
          {visibleItems.length}/{items.length} visible
        </span>
        {preferences.pinned.length > 0 && (
          <span className="rounded-(--radius-ctl) border border-action/60 px-2 py-1 font-mono text-[10px] text-action">
            {preferences.pinned.length} pinned
          </span>
        )}
        {hiddenCount > 0 && (
          <span className="rounded-(--radius-ctl) border border-flag/60 px-2 py-1 font-mono text-[10px] text-flag">
            {hiddenCount} hidden
          </span>
        )}
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-3">
        {groupedRegions.map((groupRegion) => (
          <div key={groupRegion} className="rounded-(--radius-ctl) border border-hairline bg-page/50">
            <p className="th-label border-b border-hairline px-3 py-2">{groupRegion}</p>
            <div className="divide-y divide-hairline">
              {visibleItems
                .filter((item) => item.region === groupRegion)
                .map((item) => {
                  const pinned = preferences.pinned.includes(item.symbol);
                  const hidden = preferences.hidden.includes(item.symbol);
                  return (
                    <div
                      key={item.symbol}
                      className={`grid grid-cols-[28px_1fr_auto] gap-2 px-3 py-2 ${
                        hidden ? "opacity-45" : ""
                      }`}
                    >
                      <span className="font-mono text-[11px] text-neutral-90">{item.rank}</span>
                      <div className="min-w-0">
                        <div className="flex min-w-0 items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => togglePinned(item.symbol)}
                            title={pinned ? "Unpin" : "Pin"}
                            aria-pressed={pinned}
                            className={`h-7 w-7 shrink-0 rounded-(--radius-ctl) border font-mono text-[13px] ${
                              pinned
                                ? "border-action bg-action text-white"
                                : "border-elevated text-neutral-70 hover:border-action hover:text-action"
                            }`}
                          >
                            {pinned ? "★" : "☆"}
                          </button>
                          <p className="reader-body min-w-0 truncate font-semibold text-neutral-40">
                            {item.local_name}
                          </p>
                        </div>
                        <p className="reader-meta mt-0.5 truncate font-mono text-neutral-90">
                          {item.symbol} · {item.name}
                        </p>
                      </div>
                      <div className="flex items-start gap-2 text-right">
                        <div>
                          <p className={`font-mono text-[12px] font-semibold ${toneClass(item.tone)}`}>
                            {item.value}
                          </p>
                          <p className="reader-meta text-neutral-90">{item.source_status}</p>
                        </div>
                        <button
                          type="button"
                          onClick={() => toggleHidden(item.symbol)}
                          title={hidden ? "Show index" : "Hide index"}
                          aria-pressed={hidden}
                          className={`h-7 w-7 rounded-(--radius-ctl) border font-mono text-[12px] ${
                            hidden
                              ? "border-flag bg-flag text-white"
                              : "border-elevated text-neutral-70 hover:border-flag hover:text-flag"
                          }`}
                        >
                          {hidden ? "↺" : "×"}
                        </button>
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
