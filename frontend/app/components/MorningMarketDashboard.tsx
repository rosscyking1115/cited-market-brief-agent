import type { MorningRadarPayload, NewsRankKind, PopularNewsItem } from "@/lib/api";

function rankKindText(kind: NewsRankKind) {
  if (kind === "most_read") return "閱讀最多";
  if (kind === "most_viewed") return "觀看最多";
  if (kind === "most_covered") return "最多報導";
  if (kind === "trending") return "趨勢";
  return "最新";
}

function formatTaipei(value: string) {
  return new Intl.DateTimeFormat("zh-Hant-TW", {
    timeZone: "Asia/Taipei",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

function publishedText(value: string | null) {
  if (!value) return null;
  try {
    return `${formatTaipei(value)} 台北`;
  } catch {
    return null;
  }
}

function NewsGroup({ label, items }: { label: string; items: PopularNewsItem[] }) {
  if (items.length === 0) return null;

  return (
    <div className="rounded-(--radius-ctl) border border-hairline bg-page/50">
      <div className="flex items-center justify-between gap-3 border-b border-hairline px-3 py-2">
        <p className="th-label">{label}</p>
        <span className="font-mono text-[10px] text-neutral-90">{items.length} rows</span>
      </div>
      <div className="divide-y divide-hairline">
        {items.map((item) => (
          <article key={`${item.window}-${item.rank}-${item.source}-${item.url ?? item.title}`} className="grid grid-cols-[28px_1fr] gap-2 px-3 py-3">
            <span className="font-mono text-[12px] text-neutral-90">{item.rank}</span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="rounded-(--radius-ctl) border border-elevated px-1.5 py-0.5 font-mono text-[10px] text-neutral-90">
                  {rankKindText(item.rank_kind)}
                </span>
                <span className="rounded-(--radius-ctl) border border-elevated px-1.5 py-0.5 font-mono text-[10px] text-neutral-90">
                  {item.source}
                </span>
                <span className="rounded-(--radius-ctl) border border-elevated px-1.5 py-0.5 text-[10px] text-neutral-90">
                  {item.category}
                </span>
              </div>
              {item.url ? (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  className="reader-body mt-1 block font-semibold text-neutral-40 hover:text-action"
                >
                  {item.title_zh_hant}
                </a>
              ) : (
                <h3 className="reader-body mt-1 font-semibold text-neutral-40">{item.title_zh_hant}</h3>
              )}
              <div className="mt-1 flex flex-wrap items-center gap-2">
                {publishedText(item.published_at) && (
                  <span className="reader-meta font-mono text-neutral-90">{publishedText(item.published_at)}</span>
                )}
                <span className="reader-meta font-mono text-neutral-90">{item.source_status}</span>
              </div>
              <p className="reader-meta mt-1 text-neutral-90">{item.why}</p>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function PopularNewsRail({ items }: { items: PopularNewsItem[] }) {
  const realItems = items.filter((item) => item.url);
  const oneHour = realItems.filter((item) => item.window === "1h");
  const day = realItems.filter((item) => item.window === "24h");
  const sourceCount = new Set(realItems.map((item) => item.source)).size;
  const categories = Array.from(new Set(realItems.map((item) => item.category))).slice(0, 8);

  return (
    <section className="border-t border-hairline px-4 py-4 sm:px-5">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="th-label">新聞雷達</p>
          <h2 className="reader-heading mt-1 font-semibold text-neutral-30">
            先看過去 1 小時，再看 24 小時的重要市場新聞
          </h2>
        </div>
        <p className="reader-meta max-w-xl text-neutral-90">
          只顯示有連結和來源的新聞。沒有官方人氣資料時，不假裝成「閱讀最多」。
        </p>
      </div>

      {realItems.length > 0 ? (
        <>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="rounded-(--radius-ctl) border border-action/50 bg-action/10 px-2 py-1 font-mono text-[10px] text-action">
              {realItems.length} headlines
            </span>
            <span className="rounded-(--radius-ctl) border border-elevated px-2 py-1 font-mono text-[10px] text-neutral-90">
              {sourceCount} sources
            </span>
            {categories.map((category) => (
              <span key={category} className="rounded-(--radius-ctl) border border-elevated px-2 py-1 text-[11px] text-neutral-70">
                {category}
              </span>
            ))}
          </div>
          <div className="mt-3 grid gap-3 lg:grid-cols-2">
            <NewsGroup label="1 小時" items={oneHour} />
            <NewsGroup label="24 小時" items={day} />
          </div>
        </>
      ) : (
        <div className="mt-3 rounded-(--radius-ctl) border border-hairline bg-page/50 px-4 py-4">
          <p className="reader-body font-semibold text-neutral-40">目前沒有可顯示的市場新聞</p>
          <p className="reader-meta mt-1 text-neutral-90">
            系統不再顯示 BBC/GDELT/NYT 的假占位資料；等來源真的回傳新聞時，這裡才會出現可點擊標題。
          </p>
        </div>
      )}
    </section>
  );
}

export default function MorningMarketDashboard({ radar }: { radar: MorningRadarPayload }) {
  return (
    <section className="overflow-hidden rounded-(--radius-card) border border-hairline bg-card">
      <div className="border-b border-hairline px-4 py-4 sm:px-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <p className="th-label">媽媽早晨市場雷達 · Taipei morning</p>
            <h1 className="mt-2 font-serif text-2xl font-semibold leading-tight text-neutral-30 sm:text-3xl">
              市場新聞
            </h1>
            <p className="reader-body mt-2 max-w-3xl text-neutral-70">
              這裡只放真的有來源、可點開閱讀的新聞。未授權的指數行情、空白風險數字、詞彙解釋和總經占位區先移除，避免首頁看起來很多但實際不能用。
            </p>
          </div>
          <div className="shrink-0 rounded-(--radius-ctl) border border-elevated bg-page/60 px-3 py-2">
            <p className="th-label">資料時間</p>
            <p className="mt-1 font-mono text-[15px] font-semibold text-neutral-40">
              {formatTaipei(radar.generated_at)} 台北
            </p>
          </div>
        </div>
      </div>

      <PopularNewsRail items={radar.popular_news} />
    </section>
  );
}
