"use client";

import { useRegion } from "@/app/components/RegionProvider";
import { RADAR_COPY, radarLang } from "@/lib/radar-i18n";

export default function RadarDataStatus({ isDemo }: { isDemo: boolean }) {
  const { region } = useRegion();
  const lang = radarLang(region);
  const label = isDemo ? RADAR_COPY.demoData[lang] : RADAR_COPY.sourcedData[lang];

  return (
    <div className="flex justify-end">
      <span
        role="status"
        data-testid="data-provenance"
        className="rounded-(--radius-ctl) border border-elevated bg-card px-2 py-1 font-mono text-[11px] font-semibold text-neutral-70"
      >
        {label}
      </span>
    </div>
  );
}
