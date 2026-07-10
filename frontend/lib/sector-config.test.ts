import { describe, expect, it } from "vitest";
import { parseMap, parseWeights } from "@/lib/sector-config";

describe("parseWeights", () => {
  it("parses comma-separated rows and strips %", () => {
    expect(parseWeights("半導體,38.5\n金融保險, 16.8%")).toEqual([
      { sector: "半導體", weight_pct: 38.5 },
      { sector: "金融保險", weight_pct: 16.8 },
    ]);
  });

  it("parses space-separated rows", () => {
    expect(parseWeights("半導體  38.5")).toEqual([{ sector: "半導體", weight_pct: 38.5 }]);
  });

  it("skips blank and malformed lines", () => {
    expect(parseWeights("\n半導體,38\nnot-a-weight\n  \n金融,x")).toEqual([
      { sector: "半導體", weight_pct: 38 },
    ]);
  });
});

describe("parseMap", () => {
  it("maps stock code to sector", () => {
    expect(parseMap("2330,半導體\n2882, 金融保險")).toEqual({
      "2330": "半導體",
      "2882": "金融保險",
    });
  });

  it("ignores lines without a mapping", () => {
    expect(parseMap("2330\n\n2454,半導體")).toEqual({ "2454": "半導體" });
  });
});
