import { describe, expect, it } from "vitest";
import type { PopularNewsItem } from "@/lib/api";
import { cumulativeNewsItems } from "@/lib/news";

const mk = (
  window: PopularNewsItem["window"],
  url: string | null,
  title = "t",
): PopularNewsItem => ({
  rank: 1,
  title,
  title_zh_hant: title,
  source: "S",
  url,
  published_at: null,
  window,
  rank_kind: "most_viewed",
  source_status: "rss",
  category: "市場",
  why: "",
  rights_note: "",
});

describe("cumulativeNewsItems", () => {
  const items = [
    mk("1d", "a"),
    mk("1w", "b"),
    mk("1m", "c"),
  ];

  it("1d returns only same-day items", () => {
    expect(cumulativeNewsItems(items, "1d").map((i) => i.url)).toEqual(["a"]);
  });

  it("1w is cumulative (today + this week)", () => {
    expect(cumulativeNewsItems(items, "1w").map((i) => i.url)).toEqual(["a", "b"]);
  });

  it("1m includes everything", () => {
    expect(cumulativeNewsItems(items, "1m").map((i) => i.url)).toEqual(["a", "b", "c"]);
  });

  it("dedupes by url, keeping the earliest (narrower) window", () => {
    const dupes = [mk("1d", "x"), mk("1w", "x"), mk("1m", "y")];
    const out = cumulativeNewsItems(dupes, "1m");
    expect(out.map((i) => [i.url, i.window])).toEqual([
      ["x", "1d"],
      ["y", "1m"],
    ]);
  });

  it("falls back to title for dedupe when url is null", () => {
    const dupes = [mk("1d", null, "same"), mk("1w", null, "same")];
    expect(cumulativeNewsItems(dupes, "1w")).toHaveLength(1);
  });
});
