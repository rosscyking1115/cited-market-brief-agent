"use client";

import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import {
  DEFAULT_REGION,
  REGION_PROFILES,
  REGION_STORAGE_KEY,
  regionQueryValue,
  resolveRegionPreference,
  regionProfile,
  type RegionProfile,
  type UserRegion,
} from "@/lib/regions";

type RegionContextValue = {
  region: UserRegion;
  profile: RegionProfile;
  ready: boolean;
  needsChoice: boolean;
  chooseRegion: (region: UserRegion) => void;
};

const RegionContext = createContext<RegionContextValue | null>(null);

const REGION_ORDER: UserRegion[] = ["TW", "KR", "UK", "EU"];

export function RegionProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [region, setRegion] = useState<UserRegion>(DEFAULT_REGION);
  const [ready, setReady] = useState(false);
  const [needsChoice, setNeedsChoice] = useState(false);

  useEffect(() => {
    const saved = window.localStorage.getItem(REGION_STORAGE_KEY) as UserRegion | null;
    const resolved = resolveRegionPreference(pathname === "/" ? window.location.search : "", saved);
    setRegion(resolved.region);
    setNeedsChoice(pathname === "/" && resolved.needsChoice);
    if (pathname === "/" && resolved.source === "url") {
      window.localStorage.setItem(REGION_STORAGE_KEY, resolved.region);
    }
    setReady(true);
  }, [pathname]);

  useEffect(() => {
    function syncFromHistory() {
      const resolved = resolveRegionPreference(
        pathname === "/" ? window.location.search : "",
        window.localStorage.getItem(REGION_STORAGE_KEY),
      );
      setRegion(resolved.region);
      setNeedsChoice(pathname === "/" && resolved.needsChoice);
    }
    window.addEventListener("popstate", syncFromHistory);
    return () => window.removeEventListener("popstate", syncFromHistory);
  }, [pathname]);

  function chooseRegion(nextRegion: UserRegion) {
    setRegion(nextRegion);
    setNeedsChoice(false);
    window.localStorage.setItem(REGION_STORAGE_KEY, nextRegion);
    if (pathname === "/") {
      const url = new URL(window.location.href);
      url.searchParams.set("region", regionQueryValue(nextRegion));
      window.history.replaceState(window.history.state, "", url);
    }
    document.documentElement.dataset.region = nextRegion.toLowerCase();
  }

  useEffect(() => {
    document.documentElement.dataset.region = pathname === "/brief" ? "brief" : region.toLowerCase();
    document.documentElement.lang =
      pathname === "/brief" ? "en" : region === "TW" ? "zh-Hant" : region === "KR" ? "ko" : "en";
  }, [pathname, region]);

  const value = useMemo(
    () => ({
      region,
      profile: regionProfile(region),
      ready,
      needsChoice,
      chooseRegion,
    }),
    [needsChoice, ready, region],
  );

  return (
    <RegionContext.Provider value={value}>
      {children}
      <RegionPrompt />
    </RegionContext.Provider>
  );
}

export function useRegion() {
  const value = useContext(RegionContext);
  if (!value) throw new Error("useRegion must be used inside RegionProvider");
  return value;
}

function RegionPrompt() {
  const { chooseRegion, needsChoice, ready } = useRegion();
  const pathname = usePathname();
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    const shouldOpen = pathname === "/" && ready && needsChoice;
    if (shouldOpen && !dialog.open) dialog.showModal();
    if (!shouldOpen && dialog.open) dialog.close();
  }, [needsChoice, pathname, ready]);

  return (
    <dialog
        ref={dialogRef}
        onCancel={(event) => event.preventDefault()}
        onKeyDown={(event) => {
          if (event.key !== "Tab") return;
          const buttons = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>("button:not([disabled])"));
          const first = buttons[0];
          const last = buttons.at(-1);
          if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last?.focus();
          } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first?.focus();
          }
        }}
        aria-labelledby="region-title"
        aria-describedby="region-description"
        className="m-auto w-[calc(100%-1.5rem)] max-w-xl rounded-(--radius-modal) border border-elevated bg-card p-4 text-neutral-30 shadow-2xl backdrop:bg-black/55 sm:p-5"
      >
        <p className="th-label">Choose your edition</p>
        <h2 id="region-title" className="mt-2 font-serif text-xl font-semibold leading-tight text-neutral-30">
          Which region are you reading from?
        </h2>
        <p id="region-description" className="reader-body mt-2 text-[14px] leading-relaxed text-neutral-70">
          The page language, labels, and market focus will adapt automatically. You can change this later.
        </p>

        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          {REGION_ORDER.map((item) => {
            const profile = REGION_PROFILES[item];
            return (
              <button
                key={item}
                type="button"
                onClick={() => chooseRegion(item)}
                className="rounded-(--radius-ctl) border border-elevated bg-page px-3 py-3 text-left transition-[border-color,box-shadow,transform] hover:border-action hover:shadow-md active:translate-y-px"
              >
                <span className="font-mono text-[11px] text-action">{profile.shortLabel}</span>
                <span className="ml-2 font-semibold text-neutral-40">{profile.label}</span>
                <span className="reader-meta mt-1 block text-neutral-90">
                  {profile.languageLabel} · {profile.marketAnchor}
                </span>
              </button>
            );
          })}
        </div>
    </dialog>
  );
}

export function RegionSwitcher({ label = "Region", ariaLabel = "Choose region edition" }: { label?: string; ariaLabel?: string }) {
  const { chooseRegion, profile, region } = useRegion();

  return (
    <label className="flex items-center gap-1.5 rounded-(--radius-ctl) border border-elevated bg-page px-2 py-1 text-[11px] text-neutral-70 transition-shadow hover:shadow-md">
      <span className="th-label hidden sm:inline">{label}</span>
      <select
        value={region}
        onChange={(event) => chooseRegion(event.target.value as UserRegion)}
        className="bg-transparent font-mono text-[11px] text-neutral-40 outline-none"
        aria-label={ariaLabel}
      >
        {REGION_ORDER.map((item) => (
          <option key={item} value={item}>
            {REGION_PROFILES[item].shortLabel}
          </option>
        ))}
      </select>
      <span className="hidden text-neutral-90 md:inline">{profile.marketAnchor}</span>
    </label>
  );
}
