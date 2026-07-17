import type { BriefLocale } from "@/lib/api";

export type UserRegion = "TW" | "KR" | "UK" | "EU";

export type RegionProfile = {
  region: UserRegion;
  label: string;
  shortLabel: string;
  languageLabel: string;
  briefLocale: BriefLocale;
  timeZone: string;
  marketAnchor: string;
  editionTitle: string;
};

export const REGION_STORAGE_KEY = "cmb-region-v1";

export const REGION_PROFILES: Record<UserRegion, RegionProfile> = {
  TW: {
    region: "TW",
    label: "Taiwan",
    shortLabel: "TW",
    languageLabel: "繁體中文",
    briefLocale: "zh-Hant",
    timeZone: "Asia/Taipei",
    marketAnchor: "台北",
    editionTitle: "市場新聞",
  },
  KR: {
    region: "KR",
    label: "Korea",
    shortLabel: "KR",
    languageLabel: "한국어",
    briefLocale: "ko",
    timeZone: "Asia/Seoul",
    marketAnchor: "서울",
    editionTitle: "시장 뉴스",
  },
  UK: {
    region: "UK",
    label: "United Kingdom",
    shortLabel: "UK",
    languageLabel: "English",
    briefLocale: "original",
    timeZone: "Europe/London",
    marketAnchor: "London",
    editionTitle: "Market news",
  },
  EU: {
    region: "EU",
    label: "Europe",
    shortLabel: "EU",
    languageLabel: "English",
    briefLocale: "original",
    timeZone: "Europe/Brussels",
    marketAnchor: "Brussels",
    editionTitle: "Market news",
  },
};

export const DEFAULT_REGION: UserRegion = "TW";

export function regionProfile(region: UserRegion): RegionProfile {
  return REGION_PROFILES[region] ?? REGION_PROFILES[DEFAULT_REGION];
}
