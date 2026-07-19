import { describe, expect, it } from "vitest";
import {
  CATEGORY_LABELS,
  CLOCK_NOTES,
  orderedMarketIds,
  RADAR_COPY,
  localizedClockNote,
  localizedNewsCopy,
  visibleRiskSymbols,
} from "@/lib/radar-i18n";
import { resolveRegionPreference } from "@/lib/regions";

describe("region preference precedence", () => {
  it("lets a valid URL edition override a saved preference", () => {
    expect(resolveRegionPreference("?region=kr", "UK")).toEqual({
      region: "KR",
      needsChoice: false,
      source: "url",
    });
  });

  it("falls back to valid storage when the URL has no valid edition", () => {
    expect(resolveRegionPreference("?region=unknown", "EU")).toEqual({
      region: "EU",
      needsChoice: false,
      source: "storage",
    });
  });

  it("shows the chooser only when neither source has a valid edition", () => {
    expect(resolveRegionPreference("", null)).toEqual({
      region: "TW",
      needsChoice: true,
      source: "default",
    });
  });
});

describe("typed radar catalogue", () => {
  it("has every structural label in all supported languages", () => {
    for (const values of Object.values(RADAR_COPY)) {
      expect(Object.keys(values).sort()).toEqual(["en", "ko", "tw"]);
      expect(Object.values(values).every((value) => value.trim().length > 0)).toBe(true);
    }
  });

  it("keeps the English structural shell free of Chinese copy", () => {
    const english = Object.values(RADAR_COPY).map((value) => value.en).join(" ");
    expect(english).not.toMatch(/[\u3400-\u9fff]/u);
  });
});

describe("truthful regional scope", () => {
  const symbols = ["VIX", "USD/TWD", "USD/JPY", "USD-BROAD", "WTI", "US10Y"];

  it("keeps Taiwan-specific FX only in Taiwan", () => {
    expect(visibleRiskSymbols("TW", symbols)).toContain("USD/TWD");
    expect(visibleRiskSymbols("KR", symbols)).toEqual(["VIX", "USD-BROAD", "WTI", "US10Y"]);
    expect(visibleRiskSymbols("UK", symbols)).toEqual(["VIX", "USD-BROAD", "WTI", "US10Y"]);
  });

  it("orders seven separate exchanges around the selected edition", () => {
    expect(orderedMarketIds("UK")).toEqual(["lse", "xetra", "nyse", "jpx", "krx", "twse", "hkex"]);
    expect(orderedMarketIds("EU").slice(0, 2)).toEqual(["xetra", "lse"]);
    expect(orderedMarketIds("KR")[0]).toBe("krx");
  });
});

describe("original-language news fallback", () => {
  it("labels a source-title placeholder in the Taiwan edition as original language", () => {
    expect(
      localizedNewsCopy("tw", {
        title: "Markets steady as inflation cools",
        title_zh_hant: "Markets steady as inflation cools",
        title_ko: null,
        summary: "Investors await the central bank.",
        summary_zh: null,
        summary_ko: null,
      }),
    ).toEqual({
      title: "Markets steady as inflation cools",
      summary: "Investors await the central bank.",
      isOriginalLanguage: true,
      titleIsOriginalLanguage: true,
      summaryIsOriginalLanguage: true,
    });
  });

  it("labels an English summary when only the Taiwan headline was translated", () => {
    expect(
      localizedNewsCopy("tw", {
        title: "Markets steady as inflation cools",
        title_zh_hant: "通膨降溫，市場持穩",
        title_ko: null,
        summary: "Investors await the central bank.",
        summary_zh: null,
        summary_ko: null,
      }),
    ).toEqual({
      title: "通膨降溫，市場持穩",
      summary: "Investors await the central bank.",
      isOriginalLanguage: true,
      titleIsOriginalLanguage: false,
      summaryIsOriginalLanguage: true,
    });
  });

  it("labels an untranslated Korean-edition headline as original language", () => {
    expect(
      localizedNewsCopy("ko", {
        title: "Markets steady as inflation cools",
        title_zh_hant: "",
        title_ko: null,
        summary: "Investors await the central bank.",
        summary_zh: null,
        summary_ko: null,
      }),
    ).toEqual({
      title: "Markets steady as inflation cools",
      summary: "Investors await the central bank.",
      isOriginalLanguage: true,
      titleIsOriginalLanguage: true,
      summaryIsOriginalLanguage: true,
    });
  });
});

describe("backend narrative catalogue coverage", () => {
  it("localizes every category emitted by the market-radar backend", () => {
    const backendCategories = ["市場", "半導體", "商品", "宏觀", "公司"];
    expect(backendCategories.map((category) => CATEGORY_LABELS[category]?.en)).toEqual([
      "Markets",
      "Semiconductors",
      "Commodities",
      "Macro",
      "Companies",
    ]);
    expect(CATEGORY_LABELS["宏觀"]?.ko).toBe("거시경제");
    expect(CATEGORY_LABELS["公司"]?.ko).toBe("기업");
  });

  it("keys every localized clock note by a stable market ID", () => {
    expect(Object.keys(CLOCK_NOTES).sort()).toEqual(
      ["hkex", "jpx", "krx", "lse", "nyse", "twse", "xetra"],
    );
    expect(localizedClockNote("en", "hkex", "香港需求、政策與港股科技股。")).toBe(
      "Hong Kong demand, market policy and HK tech.",
    );
  });
});
