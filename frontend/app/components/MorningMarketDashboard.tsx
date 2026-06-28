"use client";

import { useEffect, useState } from "react";
import { useRegion } from "@/app/components/RegionProvider";
import { API_URL } from "@/lib/api";
import type {
  GlossaryItem,
  MarketClockItem,
  MarketStatus,
  MorningRadarPayload,
  OvernightRiskItem,
  PopularNewsItem,
  SnapshotTone,
} from "@/lib/api";
import {
  GROUP_LABELS,
  MARKET_LABELS,
  SECTION_LABELS,
  STATUS_LABELS,
  localizedClockNote,
  localizedDisclaimer,
  localizedGlossary,
  localizedHeadline,
  localizedNewsWhy,
  localizedRiskWhy,
  localizedSummary,
  radarLang,
  type RadarLang,
} from "@/lib/radar-i18n";
import type { RegionProfile } from "@/lib/regions";

const GROUP_ORDER: OvernightRiskItem["group"][] = [
  "volatility",
  "fx",
  "commodities",
  "rates",
  "futures",
];

function localeForRegion(lang: RadarLang) {
  if (lang === "tw") return "zh-Hant-TW";
  if (lang === "ko") return "ko-KR";
  return "en-GB";
}

function statusTone(status: MarketStatus) {
  if (status === "open") return "border-up/60 bg-up/10 text-up";
  if (status === "lunch") return "border-flag/50 bg-flag/10 text-flag";
  if (status === "not_open") return "border-action/50 bg-action/10 text-action";
  return "border-elevated text-neutral-90";
}

function valueTone(tone: SnapshotTone) {
  if (tone === "up") return "text-up";
  if (tone === "down") return "text-down";
  if (tone === "pending") return "text-neutral-90";
  return "text-neutral-40";
}

function marketLabel(market: string, lang: RadarLang) {
  return MARKET_LABELS[market]?.[lang] ?? market;
}

function currentFocus(items: MarketClockItem[], lang: RadarLang): string {
  const pick =
    items.find((item) => item.status === "open") ??
    items.find((item) => item.status === "not_open") ??
    items[0];
  if (!pick) return "";
  return `${marketLabel(pick.market, lang)} · ${STATUS_LABELS[pick.status][lang]}`;
}

function formatInRegion(value: string, profile: RegionProfile, lang: RadarLang) {
  return new Intl.DateTimeFormat(localeForRegion(lang), {
    timeZone: profile.timeZone,
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

function publishedText(value: string | null, profile: RegionProfile, lang: RadarLang) {
  if (!value) return null;
  try {
    return formatInRegion(value, profile, lang);
  } catch {
    return null;
  }
}

function newsTitle(item: PopularNewsItem, lang: RadarLang) {
  return lang === "tw" ? item.title_zh_hant || item.title : item.title;
}

function emptyNewsText(lang: RadarLang) {
  if (lang === "tw") {
    return {
      title: "目前沒有可顯示的市場新聞",
      body: "等財經來源回傳新聞時，這裡才會出現可點擊標題。",
    };
  }
  if (lang === "ko") {
    return {
      title: "아직 표시할 시장 뉴스가 없습니다",
      body: "실제 링크와 출처가 들어오면 이곳에 표시됩니다.",
    };
  }
  return {
    title: "No market news to show yet",
    body: "Linked, source-backed headlines will appear here when the feeds return them.",
  };
}

function periodNoteText(lang: RadarLang, label: string) {
  if (lang === "tw") return `本期單篇熱門文章較少；以上為 AI 整理的${label}重點，個別新聞可參考今日列表。`;
  if (lang === "ko") return `이 기간의 개별 인기 기사는 적습니다. 위 ${label} 요약을 참고하고, 개별 기사는 오늘 탭을 확인하세요.`;
  return `Few standout articles for this window — see the ${label} summary above; individual reads are on the Today tab.`;
}

function StarIcon({ className }: { className?: string }) {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <path
        d="M12 3l2.2 4.8L19 9l-3.6 3.3.9 4.9L12 14.9 7.7 17.2l.9-4.9L5 9l4.8-1.2L12 3Z"
        stroke="currentColor"
        strokeWidth={1.6}
        strokeLinejoin="round"
      />
    </svg>
  );
}

// --- News card (redesign) --------------------------------------------------

function NewsCard({
  item,
  index,
  profile,
  lang,
}: {
  item: PopularNewsItem;
  index: number;
  profile: RegionProfile;
  lang: RadarLang;
}) {
  const why = localizedNewsWhy(lang, item.rank_kind, item.why);
  const published = publishedText(item.published_at, profile, lang);
  const summary = lang === "tw" ? (item.summary_zh ?? item.summary) : item.summary;
  const Wrapper = item.url ? "a" : "div";
  return (
    <Wrapper
      {...(item.url ? { href: item.url, target: "_blank", rel: "noreferrer" } : {})}
      className="group block rounded-(--radius-card) border border-hairline bg-card p-4 shadow-[var(--shadow-soft)] transition-[transform,box-shadow,border-color] hover:-translate-y-0.5 hover:border-action/40 hover:shadow-[var(--shadow-lift)]"
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 w-5 shrink-0 font-mono text-[15px] font-semibold leading-none text-neutral-90">
          {index + 1}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center rounded-(--radius-ctl) bg-action-soft px-1.5 py-0.5 text-[11px] font-semibold text-action">
              {item.source}
            </span>
            <span className="text-[11px] font-medium text-neutral-70">{item.category}</span>
            {published && (
              <span className="reader-meta ml-auto font-mono text-neutral-90" suppressHydrationWarning>
                {published}
              </span>
            )}
          </div>
          <h3 className="reader-heading mt-1.5 text-[16px] text-neutral-30 [text-underline-offset:3px] group-hover:underline">
            {newsTitle(item, lang)}
          </h3>
          {summary && (
            <p className="reader-body mt-1 line-clamp-2 text-[13.5px] text-neutral-50">{summary}</p>
          )}
          {why && (
            <div className="mt-2 flex items-center gap-1.5">
              <StarIcon className="shrink-0 text-action" />
              <span className="reader-meta text-neutral-70">{why}</span>
            </div>
          )}
        </div>
      </div>
    </Wrapper>
  );
}

// --- News rail (tabs + chips + card grid) -----------------------------------

function NewsRail({
  items,
  profile,
  lang,
  framed,
  overviews,
}: {
  items: PopularNewsItem[];
  profile: RegionProfile;
  lang: RadarLang;
  framed?: boolean; // non-TW renders inside the dashboard card with a top divider
  overviews?: Record<string, string | null>; // window key -> period report (TW)
}) {
  const realItems = items.filter((item) => item.url);
  const periodLabels: Record<string, string> =
    lang === "tw"
      ? { "1d": "今日", "1w": "本週", "1m": "本月" }
      : lang === "ko"
        ? { "1d": "오늘", "1w": "이번 주", "1m": "이번 달" }
        : { "1d": "Today", "1w": "This week", "1m": "This month" };
  // Windows are cumulative time ranges: 本週 includes today + this week's most-read,
  // 本月 includes everything. A single publisher's week/month-only most-read finance
  // is often empty, so showing the rolling (deduped) set keeps every tab populated
  // with real articles instead of a summary-only card.
  const winRank = (w: string) => ["1d", "1w", "1m"].indexOf(w);
  const groups = (["1d", "1w", "1m"] as const)
    .map((key) => {
      const seen = new Set<string>();
      const items = realItems
        .filter((i) => winRank(i.window) <= winRank(key))
        .filter((i) => {
          const dedupeKey = i.url ?? i.title;
          if (seen.has(dedupeKey)) return false;
          seen.add(dedupeKey);
          return true;
        });
      return { key, label: periodLabels[key], items };
    })
    .filter((group) => group.items.length > 0 || Boolean(overviews?.[group.key]));

  const [activeTab, setActiveTab] = useState("1d");
  const [activeCat, setActiveCat] = useState<string | null>(null);
  const active = groups.find((group) => group.key === activeTab) ?? groups[0];
  const cats = active ? Array.from(new Set(active.items.map((i) => i.category))) : [];
  const shown =
    active && activeCat && cats.includes(activeCat)
      ? active.items.filter((i) => i.category === activeCat)
      : (active?.items ?? []);
  const allLabel = lang === "tw" ? "全部" : lang === "ko" ? "전체" : "All";
  const empty = emptyNewsText(lang);

  const headerTitle = lang === "tw" ? "市場新聞" : profile.editionTitle;
  const headerMeta =
    lang === "tw"
      ? "今日最值得閱讀的財經要聞"
      : lang === "ko"
        ? "오늘 가장 읽을 만한 시장 뉴스"
        : "Today's most decision-relevant finance reads";

  return (
    <section className={framed ? "border-t border-hairline px-4 py-4 sm:px-5" : "mt-9"}>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-serif text-[20px] font-semibold text-neutral-30">{headerTitle}</h2>
          <p className="reader-meta mt-0.5 text-neutral-70">{headerMeta}</p>
        </div>
        {groups.length > 1 && (
          <div className="inline-flex rounded-[6px] border border-hairline bg-page/60 p-0.5">
            {groups.map((group) => (
              <button
                key={group.key}
                type="button"
                onClick={() => {
                  setActiveTab(group.key);
                  setActiveCat(null);
                }}
                className={`cursor-pointer rounded-(--radius-ctl) px-3 py-1.5 text-[13px] font-medium transition-colors ${
                  active?.key === group.key
                    ? "bg-card text-neutral-30 shadow-[var(--shadow-soft)]"
                    : "text-neutral-90 hover:text-neutral-50"
                }`}
              >
                {group.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {cats.length > 1 && (
        <div className="hide-scroll mt-3 flex gap-2 overflow-x-auto pb-1">
          <button
            type="button"
            onClick={() => setActiveCat(null)}
            className={`cursor-pointer whitespace-nowrap rounded-full border px-3 py-1 text-[13px] font-medium transition-colors ${
              activeCat === null
                ? "border-action bg-action text-white"
                : "border-hairline text-neutral-70 hover:text-neutral-50"
            }`}
          >
            {allLabel}
          </button>
          {cats.map((category) => (
            <button
              key={category}
              type="button"
              onClick={() => setActiveCat(category)}
              className={`cursor-pointer whitespace-nowrap rounded-full border px-3 py-1 text-[13px] font-medium transition-colors ${
                activeCat === category
                  ? "border-action bg-action text-white"
                  : "border-hairline text-neutral-70 hover:text-neutral-50"
              }`}
            >
              {category}
            </button>
          ))}
        </div>
      )}

      {active && overviews?.[active.key] && (
        <div className="mt-3 rounded-(--radius-card) border border-action/30 bg-action-soft px-4 py-3">
          <p className="th-label text-action">{active.label}重點 · AI 摘要</p>
          <p className="reader-body mt-1 text-neutral-50">{overviews[active.key]}</p>
          <p className="reader-meta mt-1 text-neutral-90">AI 依{active.label}頭條整理，僅供快速掌握，不構成投資建議。</p>
        </div>
      )}

      {active && shown.length > 0 ? (
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          {shown.map((item, index) => (
            <NewsCard
              key={`${item.rank_kind}-${item.source}-${item.url ?? item.title}`}
              item={item}
              index={index}
              profile={profile}
              lang={lang}
            />
          ))}
        </div>
      ) : active && overviews?.[active.key] ? (
        <p className="reader-meta mt-3 text-neutral-70">{periodNoteText(lang, active.label)}</p>
      ) : (
        <div className="mt-3 rounded-(--radius-card) border border-hairline bg-card px-4 py-5 shadow-[var(--shadow-soft)]">
          <p className="reader-body font-semibold text-neutral-30">{empty.title}</p>
          <p className="reader-meta mt-1 text-neutral-70">{empty.body}</p>
        </div>
      )}
    </section>
  );
}

// --- Non-TW context sections (analyst editions) ----------------------------

function MorningSummary({ radar, lang }: { radar: MorningRadarPayload; lang: RadarLang }) {
  const headline = localizedHeadline(lang, radar.headline);
  const points = localizedSummary(lang, radar.summary_points);
  const focus = lang === "tw" ? radar.current_focus : currentFocus(radar.market_clock, lang);

  return (
    <div className="border-b border-hairline px-4 py-4 sm:px-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <h2 className="font-serif text-lg font-semibold leading-tight text-neutral-30 sm:text-xl">{headline}</h2>
          <ul className="mt-2 grid gap-1.5">
            {points.map((point) => (
              <li key={point} className="reader-body grid grid-cols-[14px_1fr] gap-2 text-neutral-50">
                <span className="mt-2 block h-1 w-1 rounded-full bg-action" aria-hidden />
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="shrink-0 rounded-(--radius-ctl) border border-elevated bg-page/60 px-3 py-2">
          <p className="th-label">{SECTION_LABELS.focus[lang]}</p>
          <p className="mt-1 font-mono text-[14px] font-semibold text-neutral-40">{focus}</p>
        </div>
      </div>
    </div>
  );
}

function MarketClock({ items, lang }: { items: MarketClockItem[]; lang: RadarLang }) {
  if (items.length === 0) return null;
  return (
    <section className="border-t border-hairline px-4 py-4 sm:px-5">
      <p className="th-label">{SECTION_LABELS.clock[lang]}</p>
      <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((item) => {
          const note = localizedClockNote(lang, item.market, item.note);
          return (
            <article key={item.market} className="rounded-(--radius-ctl) border border-hairline bg-page/50 px-3 py-2.5">
              <div className="flex items-center justify-between gap-2">
                <p className="reader-body font-semibold text-neutral-40">{marketLabel(item.market, lang)}</p>
                <span className={`shrink-0 rounded-(--radius-ctl) border px-1.5 py-0.5 font-mono text-[10px] ${statusTone(item.status)}`}>
                  {STATUS_LABELS[item.status][lang]}
                </span>
              </div>
              <p className="reader-meta mt-1 font-mono text-neutral-90">{item.label}</p>
              <p className="reader-meta mt-0.5 font-mono text-[10px] text-neutral-90">{item.window}</p>
              {note && <p className="reader-meta mt-1 text-neutral-70">{note}</p>}
            </article>
          );
        })}
      </div>
    </section>
  );
}

function OvernightRiskRail({ items, lang }: { items: OvernightRiskItem[]; lang: RadarLang }) {
  if (items.length === 0) return null;
  const groups = GROUP_ORDER.map((group) => ({
    group,
    rows: items.filter((item) => item.group === group),
  })).filter((entry) => entry.rows.length > 0);

  return (
    <section className="border-t border-hairline px-4 py-4 sm:px-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="th-label">{SECTION_LABELS.risk[lang]}</p>
        <span className="reader-meta font-mono text-[10px] text-neutral-90">{items.length} rows</span>
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        {groups.map(({ group, rows }) => (
          <div key={group} className="rounded-(--radius-ctl) border border-hairline bg-page/50">
            <div className="border-b border-hairline px-3 py-1.5">
              <p className="th-label">{GROUP_LABELS[group][lang]}</p>
            </div>
            <div className="divide-y divide-hairline">
              {rows.map((row) => (
                <div key={row.symbol} className="px-3 py-2">
                  <div className="grid grid-cols-[1fr_auto] items-baseline gap-2">
                    <p className="reader-body min-w-0 truncate font-semibold text-neutral-40">
                      {lang === "tw" ? row.local_name : row.name}
                    </p>
                    <span className={`shrink-0 font-mono text-[14px] font-semibold ${valueTone(row.tone)}`}>{row.value}</span>
                  </div>
                  <div className="mt-0.5 grid grid-cols-[1fr_auto] items-baseline gap-2">
                    <span className="reader-meta truncate font-mono text-[10px] text-neutral-90">{row.source}</span>
                    <span className={`shrink-0 font-mono text-[11px] ${valueTone(row.tone)}`}>{row.change}</span>
                  </div>
                  {lang === "tw" && <p className="reader-meta mt-1 text-neutral-70">{localizedRiskWhy(lang, row.symbol, row.why)}</p>}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Glossary({ items, lang }: { items: GlossaryItem[]; lang: RadarLang }) {
  if (items.length === 0) return null;
  return (
    <section className="border-t border-hairline px-4 py-4 sm:px-5">
      <p className="th-label">{SECTION_LABELS.glossary[lang]}</p>
      <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((item) => (
          <article key={item.term} className="rounded-(--radius-ctl) border border-hairline bg-page/50 px-3 py-2">
            <p className="reader-body font-semibold text-neutral-40">
              {item.term}
              <span className="ml-1.5 font-mono text-[10px] font-normal text-neutral-90">{item.english}</span>
            </p>
            <p className="reader-meta mt-1 text-neutral-70">{item.meaning}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export default function MorningMarketDashboard({ radar: initialRadar }: { radar: MorningRadarPayload }) {
  const { profile } = useRegion();
  const lang = radarLang(profile.region);
  const isTW = profile.region === "TW";
  const [radar, setRadar] = useState(initialRadar);

  // Refresh from the API on the client (same-origin /api) so live data always wins
  // even if the server render fell back to demo data.
  useEffect(() => {
    let cancelled = false;
    fetch(`${API_URL}/market-radar`, { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : null))
      .then((data: MorningRadarPayload | null) => {
        if (data && !cancelled) setRadar(data);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // Taiwan consumer edition: a clean standalone news section (hero is above it).
  // The 今日 report is in the hero; the 本週/本月 reports surface in their tabs.
  if (isTW) {
    return (
      <NewsRail
        items={radar.popular_news}
        profile={profile}
        lang={lang}
        overviews={{ "1w": radar.week_overview ?? null, "1m": radar.month_overview ?? null }}
      />
    );
  }

  // Other editions keep the full analyst layout (summary, clock, risk, news, glossary).
  const glossary = localizedGlossary(lang, radar.glossary);
  const disclaimer = localizedDisclaimer(lang, radar.disclaimer);
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
            <p className="reader-body mt-2 max-w-3xl text-neutral-70">{profile.editionSubtitle}</p>
          </div>
          <div className="shrink-0 rounded-(--radius-ctl) border border-elevated bg-page/60 px-3 py-2">
            <p className="th-label">{SECTION_LABELS.dataTime[lang]}</p>
            <p className="mt-1 font-mono text-[15px] font-semibold text-neutral-40" suppressHydrationWarning>
              {formatInRegion(radar.generated_at, profile, lang)} {profile.marketAnchor}
            </p>
          </div>
        </div>
      </div>

      <MorningSummary radar={radar} lang={lang} />
      <MarketClock items={radar.market_clock} lang={lang} />
      <OvernightRiskRail items={radar.overnight_risk} lang={lang} />
      <NewsRail items={radar.popular_news} profile={profile} lang={lang} framed />
      <Glossary items={glossary} lang={lang} />

      {disclaimer && (
        <p className="reader-meta border-t border-hairline px-4 py-3 text-neutral-90 sm:px-5">{disclaimer}</p>
      )}
    </section>
  );
}
