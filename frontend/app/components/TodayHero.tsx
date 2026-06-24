import type { FundAttributionPayload } from "@/lib/api";

// Bright on-hero figures (TW convention: gain = red, loss = green).
function heroFigureColor(value: number) {
  return value >= 0 ? "#FF7A6E" : "#6FE0B0";
}

function signed(value: number, decimals = 2) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(decimals)}`;
}

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
  headline,
  overview,
  attribution,
}: {
  headline: string;
  overview: string | null;
  attribution: FundAttributionPayload | null;
}) {
  const gist = overview?.trim();
  return (
    <section
      className="mt-5 overflow-hidden rounded-[10px] sm:mt-6"
      style={{
        background: "linear-gradient(135deg, var(--hero-bg), var(--hero-bg-2))",
        boxShadow: "var(--shadow-hero)",
      }}
    >
      <div className="grid lg:grid-cols-[1.35fr_1fr]">
        {/* LEFT — AI 今日重點 gist */}
        <div className="p-5 sm:p-7 lg:border-r" style={{ borderColor: "var(--hero-line)" }}>
          <div className="flex items-center gap-2">
            <span
              className="grid h-5 w-5 place-items-center rounded-full"
              style={{ background: "rgba(255,255,255,.1)" }}
            >
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
              今日重點 · AI 摘要
            </span>
          </div>

          <h2 className="reader-heading mt-3 text-[21px] sm:text-[25px]" style={{ color: "var(--hero-fg)" }}>
            {headline}
          </h2>
          {gist ? (
            <p className="mt-2.5 text-[14px] leading-relaxed sm:text-[15px]" style={{ color: "#CBD8E6" }}>
              {gist}
            </p>
          ) : (
            <p className="mt-2.5 text-[14px] leading-relaxed" style={{ color: "#A9BDD2" }}>
              今日市場摘要會在新聞與行情回傳後自動生成。
            </p>
          )}
        </div>

        {/* RIGHT — fund headline vs TAIEX */}
        <div className="relative p-5 sm:p-7">
          {attribution ? (
            <FundHeadline a={attribution} />
          ) : (
            <div className="flex h-full flex-col justify-center">
              <span className="th-label" style={{ color: "var(--hero-muted)" }}>
                相對表現 · 今日
              </span>
              <p className="mt-2 text-[15px]" style={{ color: "#CBD8E6" }}>
                設定你的基金後，這裡會顯示今日相對加權指數的表現。
              </p>
              <a
                href="#fund"
                className="group mt-4 inline-flex items-center gap-1.5 text-[13px] font-semibold"
                style={{ color: "#9FC6EC" }}
              >
                前往設定
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="transition-transform group-hover:translate-x-0.5" aria-hidden>
                  <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </a>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function FundHeadline({ a }: { a: FundAttributionPayload }) {
  const active = a.active_return_pct;
  const color = heroFigureColor(active);
  return (
    <>
      <div className="flex items-baseline justify-between gap-2">
        <span className="th-label" style={{ color: "var(--hero-muted)" }}>
          相對表現 · 今日
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
        {a.benchmark_name}{" "}
        <span className="font-mono">{signed(a.benchmark_return_pct)}%</span>
      </p>

      <p className="mt-3 text-[13.5px] leading-relaxed" style={{ color: "#A9BDD2" }}>
        持股可解釋{" "}
        <strong style={{ color: "var(--hero-fg)", fontWeight: 600 }}>{signed(a.explained_return_pct)}%</strong>
        ，殘差{" "}
        <strong style={{ color: "var(--hero-fg)", fontWeight: 600 }}>{signed(a.residual_pct)}%</strong>。
      </p>

      <a
        href="#fund"
        className="group mt-4 inline-flex items-center gap-1.5 text-[13px] font-semibold"
        style={{ color: "#9FC6EC" }}
      >
        查看歸因明細
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="transition-transform group-hover:translate-x-0.5" aria-hidden>
          <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </a>
    </>
  );
}
