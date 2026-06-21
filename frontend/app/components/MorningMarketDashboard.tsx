"use client";

import { useRegion } from "@/app/components/RegionProvider";
import type { MorningRadarPayload, NewsRankKind, PopularNewsItem } from "@/lib/api";
import type { RegionProfile, UserRegion } from "@/lib/regions";

const RANK_KIND_LABELS: Record<UserRegion, Record<NewsRankKind, string>> = {
  TW: {
    most_read: "閱讀最多",
    most_viewed: "觀看最多",
    most_covered: "最多報導",
    trending: "趨勢",
    latest: "最新",
  },
  KR: {
    most_read: "많이 읽음",
    most_viewed: "많이 봄",
    most_covered: "최다 보도",
    trending: "트렌드",
    latest: "최신",
  },
  UK: {
    most_read: "Most read",
    most_viewed: "Most viewed",
    most_covered: "Most covered",
    trending: "Trending",
    latest: "Latest",
  },
  EU: {
    most_read: "Most read",
    most_viewed: "Most viewed",
    most_covered: "Most covered",
    trending: "Trending",
    latest: "Latest",
  },
};

function localeForRegion(region: UserRegion) {
  if (region === "TW") return "zh-Hant-TW";
  if (region === "KR") return "ko-KR";
  if (region === "UK") return "en-GB";
  return "en-GB";
}

function rankKindText(kind: NewsRankKind, region: UserRegion) {
  return RANK_KIND_LABELS[region][kind];
}

function formatInRegion(value: string, profile: RegionProfile) {
  return new Intl.DateTimeFormat(localeForRegion(profile.region), {
    timeZone: profile.timeZone,
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

function publishedText(value: string | null, profile: RegionProfile) {
  if (!value) return null;
  try {
    return `${formatInRegion(value, profile)} ${profile.marketAnchor}`;
  } catch {
    return null;
  }
}

function newsTitle(item: PopularNewsItem, profile: RegionProfile) {
  return profile.region === "TW" ? item.title_zh_hant || item.title : item.title;
}

function emptyNewsText(profile: RegionProfile) {
  if (profile.region === "TW") {
    return {
      title: "目前沒有可顯示的市場新聞",
      body: "系統不再顯示 BBC/GDELT/NYT 的假占位資料；等來源真的回傳新聞時，這裡才會出現可點擊標題。",
    };
  }
  if (profile.region === "KR") {
    return {
      title: "아직 표시할 시장 뉴스가 없습니다",
      body: "가짜 자리표시자는 숨깁니다. 실제 링크와 출처가 들어오면 이곳에 표시됩니다.",
    };
  }
  return {
    title: "No market news to show yet",
    body: "Placeholder stories stay hidden. Linked, source-backed headlines will appear here when the feeds return them.",
  };
}

function NewsGroup({
  label,
  items,
  profile,
}: {
  label: string;
  items: PopularNewsItem[];
  profile: RegionProfile;
}) {
  if (items.length === 0) return null;

  return (
    <div className="rounded-(--radius-ctl) border border-hairline bg-page/50">
      <div className="flex items-center justify-between gap-3 border-b border-hairline px-3 py-2">
        <p className="th-label">{label}</p>
        <span className="font-mono text-[10px] text-neutral-90">{items.length} rows</span>
      </div>
      <div className="divide-y divide-hairline">
        {items.map((item) => (
          <article
            key={`${item.window}-${item.rank}-${item.source}-${item.url ?? item.title}`}
            className="grid grid-cols-[28px_1fr] gap-2 px-3 py-3"
          >
            <span className="font-mono text-[12px] text-neutral-90">{item.rank}</span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="rounded-(--radius-ctl) border border-elevated px-1.5 py-0.5 font-mono text-[10px] text-neutral-90">
                  {rankKindText(item.rank_kind, profile.region)}
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
                  className="reader-body mt-1 block font-semibold text-neutral-40 transition-colors hover:text-action"
                >
                  {newsTitle(item, profile)}
                </a>
              ) : (
                <h3 className="reader-body mt-1 font-semibold text-neutral-40">
                  {newsTitle(item, profile)}
                </h3>
              )}
              <div className="mt-1 flex flex-wrap items-center gap-2">
                {publishedText(item.published_at, profile) && (
                  <span className="reader-meta font-mono text-neutral-90">
                    {publishedText(item.published_at, profile)}
                  </span>
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

function PopularNewsRail({ items, profile }: { items: PopularNewsItem[]; profile: RegionProfile }) {
  const realItems = items.filter((item) => item.url);
  const oneHour = realItems.filter((item) => item.window === "1h");
  const day = realItems.filter((item) => item.window === "24h");
  const sourceCount = new Set(realItems.map((item) => item.source)).size;
  const categories = Array.from(new Set(realItems.map((item) => item.category))).slice(0, 8);
  const empty = emptyNewsText(profile);

  return (
    <section className="border-t border-hairline px-4 py-4 sm:px-5">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="th-label">{profile.editionTitle}</p>
          <h2 className="reader-heading mt-1 font-semibold text-neutral-30">
            {profile.newsTitle}
          </h2>
        </div>
        <p className="reader-meta max-w-xl text-neutral-90">{profile.newsHelper}</p>
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
              <span
                key={category}
                className="rounded-(--radius-ctl) border border-elevated px-2 py-1 text-[11px] text-neutral-70"
              >
                {category}
              </span>
            ))}
          </div>
          <div className="mt-3 grid gap-3 lg:grid-cols-2">
            <NewsGroup label={profile.oneHourLabel} items={oneHour} profile={profile} />
            <NewsGroup label={profile.dayLabel} items={day} profile={profile} />
          </div>
        </>
      ) : (
        <div className="mt-3 rounded-(--radius-ctl) border border-hairline bg-page/50 px-4 py-4">
          <p className="reader-body font-semibold text-neutral-40">{empty.title}</p>
          <p className="reader-meta mt-1 text-neutral-90">{empty.body}</p>
        </div>
      )}
    </section>
  );
}

export default function MorningMarketDashboard({ radar }: { radar: MorningRadarPayload }) {
  const { profile } = useRegion();

  return (
    <section className="overflow-hidden rounded-(--radius-card) border border-hairline bg-card">
      <div className="border-b border-hairline px-4 py-4 sm:px-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <p className="th-label">
              {profile.label} morning radar · {profile.marketAnchor}
            </p>
            <h1 className="mt-2 font-serif text-2xl font-semibold leading-tight text-neutral-30 sm:text-3xl">
              {profile.editionTitle}
            </h1>
            <p className="reader-body mt-2 max-w-3xl text-neutral-70">
              {profile.editionSubtitle}
            </p>
          </div>
          <div className="shrink-0 rounded-(--radius-ctl) border border-elevated bg-page/60 px-3 py-2">
            <p className="th-label">{profile.region === "KR" ? "데이터 시간" : "Data time"}</p>
            <p className="mt-1 font-mono text-[15px] font-semibold text-neutral-40">
              {formatInRegion(radar.generated_at, profile)} {profile.marketAnchor}
            </p>
          </div>
        </div>
      </div>

      <PopularNewsRail items={radar.popular_news} profile={profile} />
    </section>
  );
}
