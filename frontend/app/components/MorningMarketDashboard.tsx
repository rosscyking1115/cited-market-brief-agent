import type {
  MarketStatus,
  MorningRadarPayload,
  NewsRankKind,
  PopularNewsItem,
  SnapshotTone,
} from "@/lib/api";
import OvernightRiskRail from "@/app/components/OvernightRiskRail";
import TopIndicesRail from "@/app/components/TopIndicesRail";

function statusText(status: MarketStatus) {
  if (status === "open") return "盤中";
  if (status === "lunch") return "午休";
  if (status === "closed") return "已收盤";
  if (status === "weekend") return "週末";
  return "未開盤";
}

function statusClass(status: MarketStatus) {
  if (status === "open") return "border-up/60 bg-up/10 text-up";
  if (status === "lunch") return "border-flag/60 bg-flag/10 text-flag";
  if (status === "closed") return "border-elevated text-neutral-70";
  if (status === "weekend") return "border-elevated text-neutral-90";
  return "border-action/60 bg-action/10 text-action";
}

function toneClass(tone: SnapshotTone) {
  if (tone === "up") return "text-up";
  if (tone === "down") return "text-down";
  if (tone === "pending") return "text-flag";
  return "text-neutral-70";
}

function snapshotStatusText(status: MorningRadarPayload["snapshots"][number]["source_status"]) {
  if (status === "eod") return "每日資料";
  if (status === "delayed") return "延遲行情";
  if (status === "live") return "即時";
  return "需授權";
}

function snapshotStatusClass(status: MorningRadarPayload["snapshots"][number]["source_status"]) {
  if (status === "planned") return "border-elevated text-neutral-90";
  if (status === "eod") return "border-action/50 bg-action/10 text-action";
  if (status === "delayed") return "border-flag/50 bg-flag/10 text-flag";
  return "border-up/50 bg-up/10 text-up";
}

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

function PopularNewsRail({ items }: { items: PopularNewsItem[] }) {
  const oneHour = items.filter((item) => item.window === "1h");
  const day = items.filter((item) => item.window === "24h");
  const sourceCount = new Set(items.map((item) => item.source)).size;
  const categories = Array.from(new Set(items.map((item) => item.category))).slice(0, 8);

  return (
    <section className="border-t border-hairline px-4 py-4 sm:px-5">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="th-label">新聞雷達 · 多來源掃描</p>
          <h2 className="reader-heading mt-1 font-semibold text-neutral-30">
            先看過去 1 小時，再看 24 小時被最多媒體報導的題目
          </h2>
        </div>
        <p className="reader-meta max-w-xl text-neutral-90">
          BBC 用作最新標題；GDELT 用作多來源趨勢/覆蓋度。沒有官方人氣資料前，不標示為閱讀最多。
        </p>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <span className="rounded-(--radius-ctl) border border-action/50 bg-action/10 px-2 py-1 font-mono text-[10px] text-action">
          {items.length} headlines
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
        {[
          ["1 小時", oneHour],
          ["24 小時", day],
        ].map(([label, group]) => (
          <div key={label as string} className="rounded-(--radius-ctl) border border-hairline bg-page/50">
            <div className="flex items-center justify-between gap-3 border-b border-hairline px-3 py-2">
              <p className="th-label">{label as string}</p>
              <span className="font-mono text-[10px] text-neutral-90">{(group as PopularNewsItem[]).length} rows</span>
            </div>
            <div className="divide-y divide-hairline">
              {(group as PopularNewsItem[]).map((item) => (
                <article key={`${item.window}-${item.rank}-${item.source}`} className="grid grid-cols-[28px_1fr] gap-2 px-3 py-3">
                  <span className="font-mono text-[12px] text-neutral-90">{item.rank}</span>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="rounded-(--radius-ctl) border border-elevated px-1.5 py-0.5 font-mono text-[10px] text-neutral-90">
                        {rankKindText(item.rank_kind)}
                      </span>
                      <span className="rounded-(--radius-ctl) border border-elevated px-1.5 py-0.5 font-mono text-[10px] text-neutral-90">
                        {item.source}
                      </span>
                      <span className="rounded-(--radius-ctl) border border-elevated px-1.5 py-0.5 font-mono text-[10px] text-neutral-90">
                        {item.source_status}
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
                      <span className="reader-meta text-neutral-90">{item.category}</span>
                      {publishedText(item.published_at) && (
                        <span className="reader-meta font-mono text-neutral-90">{publishedText(item.published_at)}</span>
                      )}
                    </div>
                    <p className="reader-meta mt-1 text-neutral-90">{item.why}</p>
                    <p className="reader-meta mt-1 font-mono text-neutral-90">
                      link out only · {item.rights_note}
                    </p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function MorningMarketDashboard({ radar }: { radar: MorningRadarPayload }) {
  const activeSnapshots = radar.snapshots.filter((item) => item.source_status !== "planned");
  const plannedSnapshots = radar.snapshots.filter((item) => item.source_status === "planned");

  return (
    <section className="overflow-hidden rounded-(--radius-card) border border-hairline bg-card">
      <div className="border-b border-hairline px-4 py-4 sm:px-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <p className="th-label">媽媽早晨市場雷達 · Taipei morning</p>
            <h1 className="mt-2 font-serif text-2xl font-semibold leading-tight text-neutral-30 sm:text-3xl">
              {radar.headline}
            </h1>
            <p className="reader-body mt-2 max-w-3xl text-neutral-70">
              目標是把 StockQ、Yahoo Finance、新聞、財報與總經資料濃縮到一個早晨頁面；目前已建立正式資料欄位，下一步接行情來源。
            </p>
          </div>
          <div className="shrink-0 rounded-(--radius-ctl) border border-elevated bg-page/60 px-3 py-2">
            <p className="th-label">資料時間</p>
            <p className="mt-1 font-mono text-[15px] font-semibold text-neutral-40">
              {formatTaipei(radar.generated_at)} 台北
            </p>
            <p className="reader-meta mt-1 text-neutral-90">目前焦點：{radar.current_focus}</p>
          </div>
        </div>

        <div className="mt-4 grid gap-3 lg:grid-cols-3">
          {radar.summary_points.map((line, index) => (
            <div key={line} className="rounded-(--radius-ctl) border border-hairline bg-page/50 px-3 py-3">
              <p className="th-label">早盤重點 {index + 1}</p>
              <p className="reader-body mt-1 text-neutral-40">{line}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-0 lg:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
        <div className="border-b border-hairline lg:border-b-0 lg:border-r">
          <div className="border-b border-hairline px-4 py-3 sm:px-5">
            <p className="th-label">全球市場時鐘</p>
            <p className="reader-body mt-1 text-neutral-70">
              以台北時間排列：日本、韓國先開，接著台灣、香港/A股、歐洲、美國。
            </p>
          </div>
          <div className="grid divide-y divide-hairline">
            {radar.market_clock.map((item) => (
              <div key={item.market} className="grid gap-2 px-4 py-3 sm:grid-cols-[96px_1fr_auto] sm:items-center sm:px-5">
                <div>
                  <p className="reader-heading font-semibold text-neutral-30">{item.market}</p>
                  <p className="reader-meta mt-0.5 font-mono text-neutral-90">{item.window}</p>
                </div>
                <div className="min-w-0">
                  <p className="reader-body text-neutral-50">{item.label}</p>
                  <p className="reader-meta mt-0.5 text-neutral-90">{item.note}</p>
                </div>
                <span className={`w-fit rounded-(--radius-ctl) border px-2 py-1 font-mono text-[11px] ${statusClass(item.status)}`}>
                  {statusText(item.status)}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="border-b border-hairline px-4 py-3 sm:px-5">
            <p className="th-label">目前可用的市場快照</p>
            <p className="reader-body mt-1 text-neutral-70">
              先顯示已接入的匯率、油價、VIX、利率等資料；正式指數行情先藏到待授權區。
            </p>
          </div>
          <div className="grid grid-cols-1 divide-y divide-hairline sm:grid-cols-2 sm:divide-x sm:divide-y-0 lg:grid-cols-1 lg:divide-x-0 lg:divide-y">
            {(activeSnapshots.length ? activeSnapshots : []).map((item) => (
              <div key={`${item.label}-${item.local_name}`} className="min-w-0 px-4 py-3 sm:px-5">
                <div className="flex items-baseline justify-between gap-3">
                  <p className="th-label">{item.local_name}</p>
                  <span className="font-mono text-[10px] text-neutral-90">{item.label}</span>
                </div>
                <p className={`mt-1 font-mono text-[18px] font-semibold ${toneClass(item.tone)}`}>
                  {item.value}
                </p>
                <p className="reader-meta mt-1 text-neutral-90">{item.change}</p>
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  <span
                    className={`rounded-(--radius-ctl) border px-1.5 py-0.5 font-mono text-[10px] ${snapshotStatusClass(
                      item.source_status,
                    )}`}
                  >
                    {snapshotStatusText(item.source_status)}
                  </span>
                  <span className="reader-meta font-mono text-neutral-90">
                    {item.source_status === "planned" ? "授權後顯示行情" : `source: ${item.source}`}
                  </span>
                </div>
              </div>
            ))}
            {activeSnapshots.length === 0 && (
              <div className="px-4 py-3 sm:px-5">
                <p className="reader-body font-semibold text-neutral-40">目前沒有可顯示的已授權快照</p>
                <p className="reader-meta mt-1 text-neutral-90">請看下方 Overnight Risk；FRED/Alpha 有資料時會自動出現在這裡。</p>
              </div>
            )}
            {plannedSnapshots.length > 0 && (
              <details className="px-4 py-3 sm:px-5">
                <summary className="cursor-pointer reader-body font-semibold text-neutral-40">
                  待接授權行情 ({plannedSnapshots.length})
                </summary>
                <div className="mt-2 grid gap-2">
                  {plannedSnapshots.map((item) => (
                    <div key={`${item.label}-${item.local_name}`} className="rounded-(--radius-ctl) border border-hairline bg-page/50 px-2 py-2">
                      <div className="flex items-baseline justify-between gap-3">
                        <p className="reader-body font-semibold text-neutral-40">{item.local_name}</p>
                        <span className="font-mono text-[10px] text-neutral-90">{item.label}</span>
                      </div>
                      <p className="reader-meta mt-1 text-neutral-90">{item.change}</p>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        </div>
      </div>

      <PopularNewsRail items={radar.popular_news} />

      <OvernightRiskRail items={radar.overnight_risk} />

      <TopIndicesRail items={radar.top_indices} />

      <div className="grid gap-0 border-t border-hairline lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="border-b border-hairline px-4 py-4 sm:px-5 lg:border-b-0 lg:border-r">
          <p className="th-label">今日要知道的事</p>
          <div className="mt-3 grid gap-3">
            {radar.stories.map((story) => (
              <article key={story.title} className="rounded-(--radius-ctl) border border-hairline bg-page/50 px-3 py-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <h2 className="reader-heading font-semibold text-neutral-30">{story.title}</h2>
                  <span className="rounded-(--radius-ctl) border border-elevated px-2 py-0.5 font-mono text-[10px] text-neutral-90">
                    {story.tag}
                  </span>
                </div>
                <p className="reader-body mt-2 text-neutral-70">{story.why}</p>
              </article>
            ))}
          </div>
        </div>

        <aside className="px-4 py-4 sm:px-5">
          <p className="th-label">詞彙小字典</p>
          <div className="mt-3 grid gap-2">
            {radar.glossary.map((item) => (
              <details key={item.term} className="rounded-(--radius-ctl) border border-hairline bg-page/50 px-3 py-2">
                <summary className="cursor-pointer reader-body font-semibold text-neutral-40">
                  {item.term} <span className="font-mono text-[11px] font-normal text-neutral-90">{item.english}</span>
                </summary>
                <p className="reader-body mt-2 text-neutral-70">{item.meaning}</p>
              </details>
            ))}
          </div>
          <p className="reader-meta mt-3 text-neutral-90">{radar.disclaimer}</p>
        </aside>
      </div>
    </section>
  );
}
