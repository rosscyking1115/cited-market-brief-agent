"use client";

import { useRegion } from "@/app/components/RegionProvider";
import type { FundAttributionPayload, MorningRadarPayload } from "@/lib/api";
import {
  MARKET_LABELS,
  STATUS_LABELS,
  localizedHeadline,
  localizedSummary,
  radarLang,
  type RadarLang,
} from "@/lib/radar-i18n";

// Bright on-hero figures (TW convention: gain = red, loss = green).
function heroFigureColor(value: number) {
  return value >= 0 ? "#FF7A6E" : "#6FE0B0";
}

function signed(value: number, decimals = 2) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(decimals)}`;
}

const COPY: Record<
  RadarLang,
  { today: string; rel: string; now: string; emptyGist: string; detailLink: string; setupPrompt: string; setupLink: string }
> = {
  tw: {
    today: "今日重點 · AI 摘要",
    rel: "相對表現 · 今日",
    now: "目前焦點",
    emptyGist: "今日市場摘要會在新聞與行情回傳後自動生成。",
    detailLink: "查看歸因明細",
    setupPrompt: "設定你的基金後，這裡會顯示今日相對加權指數的表現。",
    setupLink: "前往設定",
  },
  ko: {
    today: "오늘의 핵심 · AI 요약",
    rel: "상대 성과 · 오늘",
    now: "현재 포커스",
    emptyGist: "오늘의 시장 요약은 뉴스와 시세가 들어오면 자동 생성됩니다.",
    detailLink: "기여도 상세 보기",
    setupPrompt: "펀드를 설정하면 오늘 벤치마크 대비 성과가 여기에 표시됩니다.",
    setupLink: "설정으로",
  },
  en: {
    today: "Today's brief · AI summary",
    rel: "Relative · today",
    now: "Now",
    emptyGist: "Today's market summary is generated once news and prices arrive.",
    detailLink: "See attribution detail",
    setupPrompt: "Set up your fund and today's performance vs the benchmark shows here.",
    setupLink: "Set up",
  },
};

function Arrow({ up, color, size = 22 }: { up: boolean; color: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ color }} aria-hidden>
      <path
        d={up ? "M12 19V5M12 5l-5 5M12 5l5 5" : "M12 5v14M12 19l-5-5M12 19l5-5"}
        stroke="currentColor"
        strokeWidth={2.2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function TodayHero({
  radar,
  attribution,
}: {
  radar: MorningRadarPayload;
  attribution: FundAttributionPayload | null;
}) {
  const { profile } = useRegion();
  const lang = radarLang(profile.region);
  const copy = COPY[lang];

  const headline = localizedHeadline(lang, radar.headline);
  const gist =
    lang === "tw"
      ? radar.today_overview?.trim() || copy.emptyGist
      : localizedSummary(lang, radar.summary_points).join(" ");
  // Right rail: TW shows fund-vs-TAIEX; other editions show the live market focus.
  const showFund = lang === "tw";

  return (
    <section
      className="mt-5 overflow-hidden rounded-[10px] sm:mt-6"
      style={{
        background: "linear-gradient(135deg, var(--hero-bg), var(--hero-bg-2))",
        boxShadow: "var(--shadow-hero)",
      }}
    >
      <div className="grid lg:grid-cols-[1.35fr_1fr]">
        {/* LEFT — AI gist */}
        <div className="p-5 sm:p-7 lg:border-r" style={{ borderColor: "var(--hero-line)" }}>
          <div className="flex items-center gap-2">
            <span className="grid h-5 w-5 place-items-center rounded-full" style={{ background: "rgba(255,255,255,.1)" }}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" style={{ color: "var(--hero-fg)" }} aria-hidden>
                <path
                  d="M12 3l2.2 4.8L19 9l-3.6 3.3.9 4.9L12 14.9 7.7 17.2l.9-4.9L5 9l4.8-1.2L12 3Z"
                  stroke="currentColor"
                  strokeWidth={1.6}
                  strokeLinejoin="round"
                />
              </svg>
            </span>
            <span className="th-label" style={{ color: "var(--hero-muted)" }}>
              {copy.today}
            </span>
          </div>

          <h2 className="reader-heading mt-3 text-[21px] sm:text-[25px]" style={{ color: "var(--hero-fg)" }}>
            {headline}
          </h2>
          <p className="mt-2.5 text-[14px] leading-relaxed sm:text-[15px]" style={{ color: "#CBD8E6" }}>
            {gist}
          </p>
        </div>

        {/* RIGHT — fund headline (TW) or market focus (other editions) */}
        <div className="relative p-5 sm:p-7">
          {showFund && attribution ? (
            <FundHeadline a={attribution} copy={copy} />
          ) : showFund ? (
            <div className="flex h-full flex-col justify-center">
              <span className="th-label" style={{ color: "var(--hero-muted)" }}>
                {copy.rel}
              </span>
              <p className="mt-2 text-[15px]" style={{ color: "#CBD8E6" }}>
                {copy.setupPrompt}
              </p>
              <a href="#fund" className="group mt-4 inline-flex items-center gap-1.5 text-[13px] font-semibold" style={{ color: "#9FC6EC" }}>
                {copy.setupLink}
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="transition-transform group-hover:translate-x-0.5" aria-hidden>
                  <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </a>
            </div>
          ) : (
            <FocusPanel radar={radar} lang={lang} copy={copy} anchor={profile.marketAnchor} />
          )}
        </div>
      </div>
    </section>
  );
}

function FocusPanel({
  radar,
  lang,
  copy,
  anchor,
}: {
  radar: MorningRadarPayload;
  lang: RadarLang;
  copy: (typeof COPY)[RadarLang];
  anchor: string;
}) {
  const pick =
    radar.market_clock.find((item) => item.status === "open") ??
    radar.market_clock.find((item) => item.status === "not_open") ??
    radar.market_clock[0];
  const focus = pick ? `${MARKET_LABELS[pick.market]?.[lang] ?? pick.market} · ${STATUS_LABELS[pick.status][lang]}` : anchor;
  return (
    <div className="flex h-full flex-col justify-center">
      <span className="th-label" style={{ color: "var(--hero-muted)" }}>
        {copy.now}
      </span>
      <p className="mt-2 font-mono text-[22px] font-semibold leading-tight sm:text-[26px]" style={{ color: "var(--hero-fg)" }}>
        {focus}
      </p>
      <p className="mt-2 text-[13.5px]" style={{ color: "#A9BDD2" }}>
        {anchor} · {radar.timezone}
      </p>
    </div>
  );
}

function FundHeadline({ a, copy }: { a: FundAttributionPayload; copy: (typeof COPY)[RadarLang] }) {
  const active = a.active_return_pct;
  const color = heroFigureColor(active);
  return (
    <>
      <div className="flex items-baseline justify-between gap-2">
        <span className="th-label" style={{ color: "var(--hero-muted)" }}>
          {copy.rel}
        </span>
        <span className="font-mono text-[12.5px]" style={{ color: "var(--hero-muted)" }}>
          {a.as_of}
        </span>
      </div>

      <div className="mt-2 flex items-end gap-2">
        <span className="font-mono font-semibold leading-none" style={{ color, fontSize: "clamp(44px,8vw,64px)" }}>
          {signed(active)}
        </span>
        <span className="mb-2 font-mono text-[20px]" style={{ color }}>
          %
        </span>
        <span className="mb-3">
          <Arrow up={active >= 0} color={color} />
        </span>
      </div>

      <p className="mt-1 text-[14px]" style={{ color: "#CBD8E6" }}>
        {a.fund_name}{" "}
        <span className="font-mono" style={{ color }}>
          {signed(a.fund_return_pct)}%
        </span>
        {"　"}
        {active >= 0 ? "領先" : "落後"}
        {"　"}
        {a.benchmark_name} <span className="font-mono">{signed(a.benchmark_return_pct)}%</span>
      </p>

      <p className="mt-3 text-[13.5px] leading-relaxed" style={{ color: "#A9BDD2" }}>
        持股可解釋 <strong style={{ color: "var(--hero-fg)", fontWeight: 600 }}>{signed(a.explained_return_pct)}%</strong>
        ，殘差 <strong style={{ color: "var(--hero-fg)", fontWeight: 600 }}>{signed(a.residual_pct)}%</strong>。
      </p>

      <a href="#fund" className="group mt-4 inline-flex items-center gap-1.5 text-[13px] font-semibold" style={{ color: "#9FC6EC" }}>
        {copy.detailLink}
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="transition-transform group-hover:translate-x-0.5" aria-hidden>
          <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </a>
    </>
  );
}
