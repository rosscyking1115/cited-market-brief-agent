"use client";

import { usePathname } from "next/navigation";
import { useRegion } from "@/app/components/RegionProvider";
import { RADAR_COPY, radarLang } from "@/lib/radar-i18n";

export default function SkipLink() {
  const pathname = usePathname();
  const { region } = useRegion();
  const lang = pathname === "/brief" ? "en" : radarLang(region);

  return (
    <a href="#main-content" className="skip-link">
      {RADAR_COPY.skipMain[lang]}
    </a>
  );
}
