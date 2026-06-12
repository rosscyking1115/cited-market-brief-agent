"use client";

// Brief canvas (Phase 3): per-section accept / edit / reject / needs-source actions
// plus brief approval. Approval is blocked until every section is resolved
// (needs_source blocks — that's the review discipline the audit trail sells).

import { useRef, useState } from "react";
import type { ReactNode } from "react";
import ApprovalChecklist from "@/app/components/ApprovalChecklist";
import type { BriefLocale, BriefTranslation, ClaimRow, BriefSectionData, SectionEdit } from "@/lib/api";

const ACTIONS = [
  { action: "accept", label: "✓ Accept", cls: "border-up/60 text-up" },
  { action: "edit", label: "✎ Edit", cls: "border-action/60 text-action" },
  { action: "reject", label: "✗ Reject", cls: "border-down/60 text-down" },
  { action: "needs_source", label: "⚑ Needs source", cls: "border-flag/60 text-flag" },
] as const;

const LOCALES: { locale: BriefLocale; label: string; helper: string }[] = [
  { locale: "original", label: "Original", helper: "English source of record" },
  { locale: "zh-Hant", label: "繁中", helper: "Traditional Chinese reading aid" },
  { locale: "ko", label: "한국어", helper: "Korean reading aid" },
];

const TRANSLATION_TIMEOUT_MS = 95000;

const HIGHLIGHT_CATEGORIES = [
  {
    id: "risk",
    label: "Risk / pressure",
    className: "analyst-highlight analyst-highlight-risk",
    pattern:
      /\b(risk|risks|warning|warnings|pressure|pressures|inflation|cost|costs|restriction|restrictions|regulation|regulations|control|controls|decline|declined|decelerated|loss|losses|competition|competitive|volatile|volatility|blocked|flagged|materially reduce|licensing requirements)\b/gi,
  },
  {
    id: "driver",
    label: "Drivers / upside",
    className: "analyst-highlight analyst-highlight-driver",
    pattern:
      /\b(growth|grew|increase|increased|up|rose|higher|improvement|improved|demand|revenue|margin|guidance|opportunity|opportunities|leadership|AI|HPC|datacenter|hyperscaler|buildout|buildouts|accelerator|accelerators)\b/gi,
  },
  {
    id: "evidence",
    label: "Data / evidence",
    className: "analyst-highlight analyst-highlight-evidence",
    pattern:
      /\b(10-Q|8-K|SEC|EDGAR|FRED|CPI|yield|Treasury|bps|basis points|vintage|filing|filings|disclosed|reported|print|quarter|May|June|January|2026|20\d{2}|[\d.]+%|C-\d{3})\b/gi,
  },
] as const;

type HighlightMatch = {
  start: number;
  end: number;
  className: string;
};

function sentenceHighlightRanges(text: string): HighlightMatch[] {
  const ranges: HighlightMatch[] = [];
  const sentencePattern = /[^.!?。！？]+(?:[.!?。！？]+|$)/g;
  for (const sentence of text.matchAll(sentencePattern)) {
    const value = sentence[0];
    const start = sentence.index ?? 0;
    const trimmedStartOffset = value.search(/\S/);
    if (trimmedStartOffset === -1) continue;
    const leading = start + trimmedStartOffset;
    const trailing = start + value.length - (value.match(/\s*$/)?.[0].length ?? 0);
    const normalized = value.trim();
    const category = HIGHLIGHT_CATEGORIES.find((item) => {
      item.pattern.lastIndex = 0;
      return item.pattern.test(normalized);
    });
    if (category) {
      ranges.push({
        start: leading,
        end: trailing,
        className: category.className,
      });
    }
  }
  return ranges;
}

function HighlightToggle({
  enabled,
  onToggle,
}: {
  enabled: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="mt-5 rounded-(--radius-ctl) border border-hairline bg-page/60 px-3 py-3 sm:px-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="th-label">Analyst highlights</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {HIGHLIGHT_CATEGORIES.map((category) => (
              <span key={category.id} className="inline-flex items-center gap-1.5 text-[12px] text-neutral-70">
                <span className={category.className} aria-hidden>
                  Aa
                </span>
                {category.label}
              </span>
            ))}
          </div>
        </div>
        <button
          type="button"
          onClick={onToggle}
          aria-pressed={enabled}
          className={`min-h-9 rounded-(--radius-ctl) border px-3 py-1.5 text-[12px] font-medium transition-colors ${
            enabled
              ? "border-action bg-action text-white"
              : "border-elevated text-neutral-70 hover:border-action hover:text-neutral-30"
          }`}
        >
          {enabled ? "Hide highlights" : "Show highlights"}
        </button>
      </div>
    </div>
  );
}

function ClaimChips({
  text,
  claims,
  showHighlights,
}: {
  text: string;
  claims: ClaimRow[];
  showHighlights: boolean;
}) {
  const paragraphs = text
    .split(/\n{2,}/)
    .map((part) => part.trim())
    .filter(Boolean);

  return (
    <div className="brief-prose mt-2">
      {paragraphs.map((paragraph, i) => (
        <p key={`${paragraph.slice(0, 24)}-${i}`}>
          <InlineMarkdown text={paragraph} claims={claims} showHighlights={showHighlights} />
        </p>
      ))}
    </div>
  );
}

function InlineMarkdown({
  text,
  claims,
  showHighlights,
}: {
  text: string;
  claims: ClaimRow[];
  showHighlights: boolean;
}) {
  const tokenPattern = /(\[#\d+\]|\[C-\d+\]\(#evidence-ledger\)|\*\*[^*]+\*\*)/g;
  const parts: { text: string; start: number; strong: boolean }[] = [];
  let cursor = 0;
  for (const match of text.matchAll(tokenPattern)) {
    const start = match.index ?? 0;
    if (start > cursor) {
      parts.push({ text: text.slice(cursor, start), start: cursor, strong: false });
    }
    const raw = match[0];
    const strong = /^\*\*([^*]+)\*\*$/.exec(raw);
    parts.push({
      text: strong ? strong[1] : raw,
      start: strong ? start + 2 : start,
      strong: Boolean(strong),
    });
    cursor = start + raw.length;
  }
  if (cursor < text.length) {
    parts.push({ text: text.slice(cursor), start: cursor, strong: false });
  }

  const ranges = showHighlights ? sentenceHighlightRanges(text) : [];

  function renderTextSegment(part: { text: string; start: number; strong: boolean }, i: number) {
    if (!showHighlights || !part.text.trim()) return <span key={i}>{part.text}</span>;
    const segmentEnd = part.start + part.text.length;
    const matches = ranges
      .filter((range) => range.start < segmentEnd && range.end > part.start)
      .map((range) => ({
        start: Math.max(0, range.start - part.start),
        end: Math.min(part.text.length, range.end - part.start),
        className: range.className,
      }));
    if (matches.length === 0) return <span key={i}>{part.text}</span>;

    const nodes: ReactNode[] = [];
    let localCursor = 0;
    matches.forEach((range, index) => {
      if (range.start > localCursor) {
        nodes.push(<span key={`plain-${index}`}>{part.text.slice(localCursor, range.start)}</span>);
      }
      nodes.push(
        <mark key={`mark-${index}`} className={range.className}>
          {part.text.slice(range.start, range.end)}
        </mark>,
      );
      localCursor = range.end;
    });
    if (localCursor < part.text.length) {
      nodes.push(<span key="plain-tail">{part.text.slice(localCursor)}</span>);
    }
    return <span key={i}>{nodes}</span>;
  }

  return (
    <>
      {parts.map((part, i) => {
        const match = /^\[#(\d+)\]$/.exec(part.text) ?? /^\[C-(\d+)\]\(#evidence-ledger\)$/.exec(part.text);
        if (!match) {
          return renderTextSegment(part, i);
        }
        const idx = Number(match[1]);
        const ok = claims.find((c) => c.index === idx)?.support_status === "supported";
        return (
          <a
            key={i}
            href={`#claim-${String(idx).padStart(3, "0")}`}
            className={`mx-0.5 inline-block rounded-(--radius-ctl) border px-1 py-px align-middle font-mono text-[10px] leading-none ${
              ok
                ? "border-elevated text-neutral-90 hover:border-action hover:text-neutral-30"
                : "border-flag/60 text-flag"
            }`}
          >
            C-{String(idx).padStart(3, "0")}
            {!ok && " ⚑"}
          </a>
        );
      })}
    </>
  );
}

export default function BriefCanvas({
  briefId,
  sections,
  claims,
  initialEdits,
  initialStatus,
  apiUrl,
  live,
}: {
  briefId: string;
  sections: BriefSectionData[];
  claims: ClaimRow[];
  initialEdits: Record<string, SectionEdit>;
  initialStatus: string;
  apiUrl: string;
  live: boolean;
}) {
  const [edits, setEdits] = useState<Record<string, SectionEdit>>(initialEdits);
  const [status, setStatus] = useState(initialStatus);
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [locale, setLocale] = useState<BriefLocale>("original");
  const [translations, setTranslations] = useState<Record<string, BriefTranslation>>({});
  const [translationBusy, setTranslationBusy] = useState<BriefLocale | null>(null);
  const [translationError, setTranslationError] = useState("");
  const [showHighlights, setShowHighlights] = useState(false);
  const translationAbortRef = useRef<AbortController | null>(null);
  const translationRequestRef = useRef(0);

  const resolved = sections.every((_, i) => {
    const e = edits[String(i)];
    return e && e.action !== "needs_source";
  });
  const claimsReady = claims.every(
    (claim) => claim.support_status === "supported" && claim.citations.length > 0,
  );
  const approvable = resolved && claimsReady;
  const approved = status === "approved";
  const activeTranslation = locale === "original" ? null : translations[locale];

  async function selectLocale(nextLocale: BriefLocale) {
    setLocale(nextLocale);
    setTranslationError("");
    if (nextLocale === "original" || translations[nextLocale]) {
      translationRequestRef.current += 1;
      translationAbortRef.current?.abort();
      setTranslationBusy(null);
      return;
    }
    if (!live) {
      setTranslationError("Translation needs the live API connection.");
      return;
    }
    translationAbortRef.current?.abort();
    const requestId = translationRequestRef.current + 1;
    translationRequestRef.current = requestId;
    const controller = new AbortController();
    translationAbortRef.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), TRANSLATION_TIMEOUT_MS);
    setTranslationBusy(nextLocale);
    try {
      const res = await fetch(`${apiUrl}/briefs/${briefId}/translations/${nextLocale}`, {
        signal: controller.signal,
      });
      if (!res.ok) throw new Error("translation request failed");
      const payload = (await res.json()) as BriefTranslation;
      if (translationRequestRef.current !== requestId) return;
      setTranslations((prev) => ({ ...prev, [nextLocale]: payload }));
    } catch (error) {
      if (translationRequestRef.current !== requestId) return;
      setTranslationError(
        error instanceof DOMException && error.name === "AbortError"
          ? "Translation timed out. You can keep reading Original or try again."
          : "Could not load this translation. Keep using Original for the audited text.",
      );
    } finally {
      window.clearTimeout(timeout);
      if (translationRequestRef.current === requestId) {
        setTranslationBusy(null);
      }
    }
  }

  async function act(index: number, action: string, content?: string) {
    if (!live || approved || busy) return;
    setBusy(true);
    try {
      const res = await fetch(`${apiUrl}/briefs/${briefId}/sections/${index}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, content: content ?? null }),
      });
      if (res.ok) {
        setEdits((prev) => ({
          ...prev,
          [String(index)]: {
            action: action as SectionEdit["action"],
            content: content ?? null,
            at: new Date().toISOString(),
            by: "you",
          },
        }));
        setStatus("in_review");
        setEditing(null);
      }
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    if (!live || approved || !approvable || busy) return;
    setBusy(true);
    try {
      const res = await fetch(`${apiUrl}/briefs/${briefId}/approve`, { method: "POST" });
      if (res.ok) setStatus("approved");
    } finally {
      setBusy(false);
    }
  }

  async function acceptOpenSections() {
    if (!live || approved || busy) return;
    setBusy(true);
    try {
      const nextEdits = { ...edits };
      for (let i = 0; i < sections.length; i += 1) {
        const existing = nextEdits[String(i)];
        if (existing && existing.action !== "needs_source") continue;
        const res = await fetch(`${apiUrl}/briefs/${briefId}/sections/${i}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "accept", content: null }),
        });
        if (res.ok) {
          nextEdits[String(i)] = {
            action: "accept",
            content: null,
            at: new Date().toISOString(),
            by: "you",
          };
        }
      }
      setEdits(nextEdits);
      setStatus("in_review");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <ApprovalChecklist sectionsCount={sections.length} edits={edits} claims={claims} />

      <HighlightToggle
        enabled={showHighlights}
        onToggle={() => setShowHighlights((current) => !current)}
      />

      <div className="mt-5 rounded-(--radius-ctl) border border-hairline bg-page/60 px-3 py-3 sm:px-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="th-label">Reader language</p>
            <p className="reader-body mt-1 text-[12px] leading-relaxed text-neutral-70">
              English stays visible as the accurate source; translations are reading aids.
            </p>
          </div>
          <div className="grid w-full grid-cols-3 gap-1 rounded-(--radius-ctl) border border-elevated p-1 sm:w-auto sm:min-w-80">
            {LOCALES.map((item) => (
              <button
                key={item.locale}
                type="button"
                aria-pressed={locale === item.locale}
                title={item.helper}
                onClick={() => selectLocale(item.locale)}
                className={`min-h-8 rounded-(--radius-ctl) px-2 py-1 text-[12px] font-medium transition-colors sm:px-2.5 ${
                  locale === item.locale
                    ? "bg-action text-white"
                    : "text-neutral-70 hover:bg-card hover:text-neutral-30"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
        {(translationBusy || translationError || activeTranslation) && (
          <p className="reader-body mt-2 text-[12px] leading-relaxed text-neutral-90">
            {translationBusy && `Translating ${LOCALES.find((item) => item.locale === translationBusy)?.label}...`}
            {translationError || activeTranslation?.disclaimer}
          </p>
        )}
      </div>

      <div className="mt-5 flex flex-col gap-3 border-t border-hairline pt-4 sm:flex-row sm:items-center sm:justify-between">
        <span className="th-label">
          Review · status{" "}
          <span className={approved ? "text-up" : "text-neutral-50"}>{status}</span>
        </span>
        <div className="flex flex-wrap items-center gap-2">
          {!resolved && !approved && (
            <button
              type="button"
              onClick={acceptOpenSections}
              disabled={!live || busy}
              className="rounded-(--radius-ctl) border border-elevated px-3 py-1 text-[12px] font-medium text-neutral-70 transition-colors hover:border-up hover:text-up disabled:opacity-40"
            >
              Accept open sections
            </button>
          )}
          <button
            type="button"
            onClick={approve}
            disabled={!live || approved || !approvable || busy}
            title={
              approved
                ? "Approved"
                : approvable
                  ? "Approve brief"
                  : "Resolve sections and repair flagged or citationless claims first"
            }
            className={`rounded-(--radius-ctl) border px-3 py-1 text-[12px] font-medium transition-colors ${
              approved
                ? "border-up text-up"
                : "border-action text-action hover:bg-action hover:text-white disabled:opacity-40"
            }`}
          >
            {approved ? "✓ Approved" : "Approve brief"}
          </button>
        </div>
      </div>

      {sections.map((section, i) => {
        const edit = edits[String(i)];
        const isEditing = editing === i;
        return (
          <section
            key={section.title + i}
            className={`mt-5 max-w-4xl rounded-(--radius-ctl) border-l-2 pl-3 sm:pl-5 ${
              edit?.action === "accept"
                ? "border-up/70"
                : edit?.action === "reject"
                  ? "border-down/70"
                  : edit?.action === "needs_source"
                    ? "border-flag/70"
                    : edit?.action === "edit"
                      ? "border-action/70"
                      : "border-hairline"
            }`}
          >
            <div className="flex flex-col gap-2 sm:flex-row sm:items-baseline sm:justify-between sm:gap-3">
              <h3 className="reader-heading text-base font-semibold text-neutral-30">{section.title}</h3>
              <div className="flex shrink-0 flex-wrap items-center gap-1.5">
                {edit && (
                  <span className="mr-1 font-mono text-[10px] text-neutral-90">
                    {edit.action} · {edit.at.slice(0, 16).replace("T", " ")}
                  </span>
                )}
                {!approved &&
                  ACTIONS.map(({ action, label, cls }) => (
                    <button
                      key={action}
                      type="button"
                      disabled={!live || busy}
                      onClick={() => {
                        if (action === "edit") {
                          setEditing(isEditing ? null : i);
                          setDraft(edit?.content ?? section.content_markdown);
                        } else {
                          act(i, action);
                        }
                      }}
                      title={live ? undefined : "Connect the API to review"}
                      className={`min-h-8 rounded-(--radius-ctl) border px-2 py-1 text-[11px] transition-opacity disabled:opacity-40 ${
                        edit?.action === action ? cls : "border-elevated text-neutral-70 hover:text-neutral-30"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
              </div>
            </div>

            {isEditing ? (
              <div className="mt-2">
                <textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  rows={4}
                  className="w-full rounded-(--radius-ctl) border border-elevated bg-page p-2 font-mono text-[12px] text-neutral-30 focus:border-action"
                />
                <div className="mt-1.5 flex gap-2">
                  <button
                    type="button"
                    onClick={() => act(i, "edit", draft)}
                    className="rounded-(--radius-ctl) border border-action px-2 py-0.5 text-[11px] text-action hover:bg-action hover:text-white"
                  >
                    Save edit
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditing(null)}
                    className="rounded-(--radius-ctl) border border-elevated px-2 py-0.5 text-[11px] text-neutral-70"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <>
                <ClaimChips
                  text={edit?.action === "edit" && edit.content ? edit.content : section.content_markdown}
                  claims={claims}
                  showHighlights={showHighlights}
                />
                {activeTranslation?.sections[i] && (
                  <div className="reader-translation mt-3 rounded-(--radius-ctl) border border-hairline bg-page/70 px-3 py-3 sm:px-4">
                    <p className="th-label mb-1">
                      {activeTranslation.label} reading aid
                    </p>
                    <h4 className="text-[14px] font-semibold text-neutral-40">
                      {activeTranslation.sections[i].title}
                    </h4>
                    <ClaimChips
                      text={activeTranslation.sections[i].content_markdown}
                      claims={claims}
                      showHighlights={showHighlights}
                    />
                  </div>
                )}
              </>
            )}
          </section>
        );
      })}
    </div>
  );
}
