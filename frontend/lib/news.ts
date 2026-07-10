import type { PopularNewsItem } from "@/lib/api";

// News windows are cumulative time ranges: "1w" includes "1d", "1m" includes both.
export const NEWS_WINDOWS = ["1d", "1w", "1m"] as const;
export type NewsWindow = (typeof NEWS_WINDOWS)[number];

const rank = (w: string) => (NEWS_WINDOWS as readonly string[]).indexOf(w);

/**
 * Items whose window falls within (≤) the given window, deduped by url (falling
 * back to title). A single publisher's week/month-only most-read finance is often
 * empty, so the cumulative set keeps every tab populated with real articles.
 */
export function cumulativeNewsItems(
  items: PopularNewsItem[],
  windowKey: NewsWindow,
): PopularNewsItem[] {
  const seen = new Set<string>();
  return items
    .filter((item) => rank(item.window) <= rank(windowKey))
    .filter((item) => {
      const key = item.url ?? item.title;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}
