"use client";

import { useRegion } from "@/app/components/RegionProvider";
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
  RANK_KIND_LABELS,
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
    return `${formatInRegion(value, profile, lang)} ${profile.marketAnchor}`;
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
      body: "系統不再顯示 BBC/GDELT/NYT 的假占位資料；等來源真的回傳新聞時，這裡才會出現可點擊標題。",
    };
  }
  if (lang === "ko") {
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

// --- Morning summary -------------------------------------------------------

function MorningSummary({ radar, lang }: { radar: MorningRadarPayload; lang: RadarLang }) {
  const headline = localizedHeadline(lang, radar.headline);
  const points = localizedSummary(lang, radar.summary_points);
  const focus = lang === "tw" ? radar.current_focus : currentFocus(radar.market_clock, lang);

  return (
    <div className="border-b border-hairline px-4 py-4 sm:px-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <h2 className="font-serif text-lg font-semibold leading-tight text-neutral-30 sm:text-xl">
            {headline}
          </h2>
          <ul className="mt-2 grid gap-1.5">
            {points.map((point) => (
              <li key={point} className="reader-body grid grid-cols-[14px_1fr] gap-2 text-neutral-70">
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

// --- Market clock ----------------------------------------------------------

function MarketClock({ items, lang }: { items: MarketClockItem[]; lang: RadarLang }) {
  if (items.length === 0) return null;

  return (
    <section className="border-t border-hairline px-4 py-4 sm:px-5">
      <p className="th-label">{SECTION_LABELS.clock[lang]}</p>
      <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((item) => {
          const note = localizedClockNote(lang, item.market, item.note);
          return (
            <article
              key={item.market}
              className="rounded-(--radius-ctl) border border-hairline bg-page/50 px-3 py-2.5"
            >
              <div className="flex items-center justify-between gap-2">
                <p className="reader-body font-semibold text-neutral-40">{marketLabel(item.market, lang)}</p>
                <span
                  className={`shrink-0 rounded-(--radius-ctl) border px-1.5 py-0.5 font-mono text-[10px] ${statusTone(item.status)}`}
                >
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

// --- Overnight risk rail (FRED-hydrated where available) -------------------

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
              {rows.map((row) => {
                const why = localizedRiskWhy(lang, row.symbol, row.why);
                return (
                  <div key={row.symbol} className="px-3 py-2">
                    <div className="grid grid-cols-[1fr_auto] items-baseline gap-2">
                      <p className="reader-body min-w-0 truncate font-semibold text-neutral-40">
                        {lang === "tw" ? row.local_name : row.name}
                      </p>
                      <span className={`shrink-0 font-mono text-[14px] font-semibold ${valueTone(row.tone)}`}>
                        {row.value}
                      </span>
                    </div>
                    <div className="mt-0.5 grid grid-cols-[1fr_auto] items-baseline gap-2">
                      <span className="reader-meta truncate font-mono text-[10px] text-neutral-90">
                        {row.source}
                      </span>
                      <span className={`shrink-0 font-mono text-[11px] ${valueTone(row.tone)}`}>
                        {row.change}
                      </span>
                    </div>
                    {why && <p className="reader-meta mt-1 text-neutral-70">{why}</p>}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// --- Glossary --------------------------------------------------------------

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

// --- News rail -------------------------------------------------------------

function NewsGroup({
  label,
  items,
  profile,
  lang,
}: {
  label: string;
  items: PopularNewsItem[];
  profile: RegionProfile;
  lang: RadarLang;
}) {
  if (items.length === 0) return null;

  return (
    <div className="rounded-(--radius-ctl) border border-hairline bg-page/50">
      <div className="flex items-center justify-between gap-3 border-b border-hairline px-3 py-2">
        <p className="th-label">{label}</p>
        <span className="font-mono text-[10px] text-neutral-90">{items.length} rows</span>
      </div>
      <div className="divide-y divide-hairline">
        {items.map((item) => {
          const why = localizedNewsWhy(lang, item.source_status, item.why);
          return (
            <article
              key={`${item.window}-${item.rank}-${item.source}-${item.url ?? item.title}`}
              className="grid grid-cols-[28px_1fr] gap-2 px-3 py-3"
            >
              <span className="font-mono text-[12px] text-neutral-90">{item.rank}</span>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="rounded-(--radius-ctl) border border-elevated px-1.5 py-0.5 font-mono text-[10px] text-neutral-90">
                    {RANK_KIND_LABELS[lang][item.rank_kind]}
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
                    {newsTitle(item, lang)}
                  </a>
                ) : (
                  <h3 className="reader-body mt-1 font-semibold text-neutral-40">{newsTitle(item, lang)}</h3>
                )}
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  {publishedText(item.published_at, profile, lang) && (
                    <span className="reader-meta font-mono text-neutral-90">
                      {publishedText(item.published_at, profile, lang)}
                    </span>
                  )}
                  <span className="reader-meta font-mono text-neutral-90">{item.source_status}</span>
                </div>
                {why && <p className="reader-meta mt-1 text-neutral-90">{why}</p>}
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function PopularNewsRail({
  items,
  profile,
  lang,
}: {
  items: PopularNewsItem[];
  profile: RegionProfile;
  lang: RadarLang;
}) {
  const realItems = items.filter((item) => item.url);
  const oneHour = realItems.filter((item) => item.window === "1h");
  const day = realItems.filter((item) => item.window === "24h");
  const sourceCount = new Set(realItems.map((item) => item.source)).size;
  const categories = Array.from(new Set(realItems.map((item) => item.category))).slice(0, 8);
  const empty = emptyNewsText(lang);

  return (
    <section className="border-t border-hairline px-4 py-4 sm:px-5">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="th-label">{profile.editionTitle}</p>
          <h2 className="reader-heading mt-1 font-semibold text-neutral-30">{profile.newsTitle}</h2>
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
            <NewsGroup label={profile.oneHourLabel} items={oneHour} profile={profile} lang={lang} />
            <NewsGroup label={profile.dayLabel} items={day} profile={profile} lang={lang} />
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
  const lang = radarLang(profile.region);
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
            <p className="mt-1 font-mono text-[15px] font-semibold text-neutral-40">
              {formatInRegion(radar.generated_at, profile, lang)} {profile.marketAnchor}
            </p>
          </div>
        </div>
      </div>

      <MorningSummary radar={radar} lang={lang} />

      <MarketClock items={radar.market_clock} lang={lang} />

      <OvernightRiskRail items={radar.overnight_risk} lang={lang} />

      <PopularNewsRail items={radar.popular_news} profile={profile} lang={lang} />

      <Glossary items={glossary} lang={lang} />

      {disclaimer && (
        <p className="reader-meta border-t border-hairline px-4 py-3 text-neutral-90 sm:px-5">{disclaimer}</p>
      )}
    </section>
  );
}
