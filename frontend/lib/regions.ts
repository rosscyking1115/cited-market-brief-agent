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
  editionSubtitle: string;
  newsTitle: string;
  newsHelper: string;
  oneHourLabel: string;
  dayLabel: string;
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
    editionSubtitle:
      "台灣版會優先整理台股、亞洲開盤、美元台幣、油金利率與全球科技新聞。",
    newsTitle: "先看過去 1 小時，再看 24 小時的重要市場新聞",
    newsHelper: "只顯示有連結和來源的新聞。沒有官方人氣資料時，不假裝成「閱讀最多」。",
    oneHourLabel: "1 小時",
    dayLabel: "24 小時",
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
    editionSubtitle:
      "한국판은 코스피/코스닥, 반도체·배터리, 원화, 미국 장 마감과 아시아 개장을 먼저 봅니다.",
    newsTitle: "최근 1시간 뉴스와 24시간 주요 시장 뉴스를 먼저 확인합니다",
    newsHelper: "출처와 링크가 있는 뉴스만 보여줍니다. 공식 인기 데이터가 없으면 가장 많이 읽은 뉴스라고 표시하지 않습니다.",
    oneHourLabel: "1시간",
    dayLabel: "24시간",
  },
  UK: {
    region: "UK",
    label: "United Kingdom",
    shortLabel: "UK",
    languageLabel: "English",
    briefLocale: "original",
    timeZone: "Europe/London",
    marketAnchor: "London",
    editionTitle: "Market News",
    editionSubtitle:
      "UK edition prioritises London morning context: US close, sterling, gilts, FTSE sectors, Europe and global macro.",
    newsTitle: "Start with the last hour, then the 24-hour market tape",
    newsHelper: "Only linked source-backed stories are shown. If official popularity data is missing, we avoid calling it most read.",
    oneHourLabel: "1 hour",
    dayLabel: "24 hours",
  },
  EU: {
    region: "EU",
    label: "Europe",
    shortLabel: "EU",
    languageLabel: "English",
    briefLocale: "original",
    timeZone: "Europe/Brussels",
    marketAnchor: "Brussels",
    editionTitle: "Market News",
    editionSubtitle:
      "Europe edition prioritises the European open: US close, euro, Bunds, STOXX sectors, energy and global macro.",
    newsTitle: "Start with the last hour, then the 24-hour market tape",
    newsHelper: "Only linked source-backed stories are shown. If official popularity data is missing, we avoid calling it most read.",
    oneHourLabel: "1 hour",
    dayLabel: "24 hours",
  },
};

export const DEFAULT_REGION: UserRegion = "TW";

export function regionProfile(region: UserRegion): RegionProfile {
  return REGION_PROFILES[region] ?? REGION_PROFILES[DEFAULT_REGION];
}
