"use client";

import { useRegion } from "@/app/components/RegionProvider";
import { RADAR_COPY, radarLang } from "@/lib/radar-i18n";

export default function RadarFooter() {
  const { profile } = useRegion();
  const lang = radarLang(profile.region);
  // Radar news translations are NOT the brief translations. The automatic
  // structure-and-citation checks run on the brief path only
  // (app/briefs/translation.py); nothing checks these summaries at all. Saying
  // here what the brief says would be a false claim, so this states the limit
  // and claims nothing.
  const sourceNote =
    lang === "tw"
      ? "來源標題保留發布者連結；翻譯摘要未經評估。"
      : lang === "ko"
        ? "출처 헤드라인은 게시자 링크를 유지하며, 번역 요약은 평가되지 않았습니다."
        : "Source headlines remain linked to their publishers; translated summaries are not evaluated.";
  return (
    <footer className="reader-meta px-1 pb-6 text-[11px] leading-relaxed text-neutral-90">
      {RADAR_COPY.notAdvice[lang]} {RADAR_COPY.holidayCaveat[lang]} {sourceNote}
    </footer>
  );
}
