import { describe, expect, it } from "vitest";
import {
  RADAR_GLOSSARY,
  RADAR_HEADLINE,
  RADAR_SUMMARY,
  MARKET_LABELS,
  localizedGlossary,
  localizedHeadline,
  localizedSummary,
  radarLang,
} from "@/lib/radar-i18n";

describe("radarLang", () => {
  it("maps region to language", () => {
    expect(radarLang("TW")).toBe("tw");
    expect(radarLang("KR")).toBe("ko");
    expect(radarLang("UK")).toBe("en");
    expect(radarLang("EU")).toBe("en");
  });
});

describe("localized* fallbacks", () => {
  const twHeadline = "今天先看全球市場";
  const twSummary = ["一", "二", "三"];
  const twGlossary = [{ term: "費半", english: "SOX", meaning: "…" }];

  it("Taiwan passes the API payload through unchanged", () => {
    expect(localizedHeadline("tw", twHeadline)).toBe(twHeadline);
    expect(localizedSummary("tw", twSummary)).toEqual(twSummary);
    expect(localizedGlossary("tw", twGlossary)).toEqual(twGlossary);
  });

  it("non-Taiwan editions use the localized constants, not the payload", () => {
    expect(localizedHeadline("en", twHeadline)).toBe(RADAR_HEADLINE.en);
    expect(localizedHeadline("ko", twHeadline)).toBe(RADAR_HEADLINE.ko);
    expect(localizedSummary("ko", twSummary)).toEqual(RADAR_SUMMARY.ko);
    expect(localizedGlossary("en", twGlossary)).toEqual(RADAR_GLOSSARY.en);
  });
});

describe("legacy market labels", () => {
  it("does not imply mainland-China coverage for the HKEX session", () => {
    expect(MARKET_LABELS["香港 / A股"]).toEqual({
      tw: "香港",
      ko: "홍콩",
      en: "Hong Kong",
    });
  });
});
