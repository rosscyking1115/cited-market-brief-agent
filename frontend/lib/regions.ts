import type { BriefLocale, MarketId } from "@/lib/api";

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
  primaryMarketId: MarketId;
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
    primaryMarketId: "twse",
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
    primaryMarketId: "krx",
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
    primaryMarketId: "lse",
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
    primaryMarketId: "xetra",
  },
};

export const DEFAULT_REGION: UserRegion = "TW";

export function regionProfile(region: UserRegion): RegionProfile {
  return REGION_PROFILES[region] ?? REGION_PROFILES[DEFAULT_REGION];
}

export type RegionResolution = {
  region: UserRegion;
  needsChoice: boolean;
  source: "url" | "storage" | "default";
};

const QUERY_REGIONS: Record<string, UserRegion> = {
  tw: "TW",
  kr: "KR",
  uk: "UK",
  eu: "EU",
};

export function isUserRegion(value: string | null): value is UserRegion {
  return value !== null && value in REGION_PROFILES;
}

export function regionQueryValue(region: UserRegion): string {
  return region.toLowerCase();
}

export function resolveRegionPreference(search: string, saved: string | null): RegionResolution {
  const query = new URLSearchParams(search).get("region")?.toLowerCase() ?? "";
  const fromUrl = QUERY_REGIONS[query];
  if (fromUrl) return { region: fromUrl, needsChoice: false, source: "url" };
  if (isUserRegion(saved)) return { region: saved, needsChoice: false, source: "storage" };
  return { region: DEFAULT_REGION, needsChoice: true, source: "default" };
}
