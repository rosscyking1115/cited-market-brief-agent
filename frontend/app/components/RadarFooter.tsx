"use client";

import { useRegion } from "@/app/components/RegionProvider";
import { RADAR_COPY, radarLang } from "@/lib/radar-i18n";

export default function RadarFooter() {
  const { profile } = useRegion();
  const lang = radarLang(profile.region);
  const sourceNote =
    lang === "tw"
      ? "來源標題保留發布者連結；翻譯僅供閱讀輔助。"
      : lang === "ko"
        ? "출처 헤드라인은 게시자 링크를 유지하며 번역은 읽기 보조용입니다."
        : "Source headlines remain linked to their publishers; translations are reading aids.";
  return (
    <footer className="reader-meta px-1 pb-6 text-[11px] leading-relaxed text-neutral-90">
      {RADAR_COPY.notAdvice[lang]} {RADAR_COPY.holidayCaveat[lang]} {sourceNote}
    </footer>
  );
}
