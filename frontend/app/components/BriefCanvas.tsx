"use client";

// Brief canvas (Phase 3): per-section accept / edit / reject / needs-source actions
// plus brief approval. Approval is blocked until every section is resolved
// (needs_source blocks — that's the review discipline the audit trail sells).

import { useState } from "react";
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

function ClaimChips({ text, claims }: { text: string; claims: ClaimRow[] }) {
  const paragraphs = text
    .split(/\n{2,}/)
    .map((part) => part.trim())
    .filter(Boolean);

  return (
    <div className="brief-prose mt-2">
      {paragraphs.map((paragraph, i) => (
        <p key={`${paragraph.slice(0, 24)}-${i}`}>
          <InlineMarkdown text={paragraph} claims={claims} />
        </p>
      ))}
    </div>
  );
}

function InlineMarkdown({ text, claims }: { text: string; claims: ClaimRow[] }) {
  const parts = text.split(/(\[#\d+\]|\[C-\d+\]\(#evidence-ledger\)|\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((part, i) => {
        const match = /^\[#(\d+)\]$/.exec(part) ?? /^\[C-(\d+)\]\(#evidence-ledger\)$/.exec(part);
        if (!match) {
          const strong = /^\*\*([^*]+)\*\*$/.exec(part);
          return strong ? <strong key={i}>{strong[1]}</strong> : <span key={i}>{part}</span>;
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
  const [translationBusy, setTranslationBusy] = useState(false);
  const [translationError, setTranslationError] = useState("");

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
    if (nextLocale === "original" || translations[nextLocale]) return;
    if (!live) {
      setTranslationError("Translation needs the live API connection.");
      return;
    }
    setTranslationBusy(true);
    try {
      const res = await fetch(`${apiUrl}/briefs/${briefId}/translations/${nextLocale}`);
      if (!res.ok) throw new Error("translation request failed");
      const payload = (await res.json()) as BriefTranslation;
      setTranslations((prev) => ({ ...prev, [nextLocale]: payload }));
    } catch {
      setTranslationError("Could not load this translation. Keep using Original for the audited text.");
    } finally {
      setTranslationBusy(false);
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

      <div className="mt-5 rounded-(--radius-ctl) border border-hairline bg-page/60 px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="th-label">Reader language</p>
            <p className="mt-1 text-[12px] leading-relaxed text-neutral-70">
              English stays visible as the accurate source; translations are reading aids.
            </p>
          </div>
          <div className="flex items-center gap-1 rounded-(--radius-ctl) border border-elevated p-1">
            {LOCALES.map((item) => (
              <button
                key={item.locale}
                type="button"
                aria-pressed={locale === item.locale}
                title={item.helper}
                onClick={() => selectLocale(item.locale)}
                disabled={translationBusy && locale !== item.locale}
                className={`min-w-20 rounded-(--radius-ctl) px-2.5 py-1 text-[12px] font-medium transition-colors disabled:opacity-50 ${
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
          <p className="mt-2 text-[12px] leading-relaxed text-neutral-90">
            {translationBusy && "Translating the brief..."}
            {translationError || activeTranslation?.disclaimer}
          </p>
        )}
      </div>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-hairline pt-4">
        <span className="th-label">
          Review · status{" "}
          <span className={approved ? "text-up" : "text-neutral-50"}>{status}</span>
        </span>
        <div className="flex items-center gap-2">
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
            className={`mt-5 max-w-4xl rounded-(--radius-ctl) border-l-2 pl-5 ${
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
            <div className="flex items-baseline justify-between gap-3">
              <h3 className="text-base font-semibold text-neutral-30">{section.title}</h3>
              <div className="flex shrink-0 items-center gap-1.5">
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
                      className={`rounded-(--radius-ctl) border px-2 py-1 text-[11px] transition-opacity disabled:opacity-40 ${
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
                />
                {activeTranslation?.sections[i] && (
                  <div className="reader-translation mt-3 rounded-(--radius-ctl) border border-hairline bg-page/70 px-4 py-3">
                    <p className="th-label mb-1">
                      {activeTranslation.label} reading aid
                    </p>
                    <h4 className="text-[14px] font-semibold text-neutral-40">
                      {activeTranslation.sections[i].title}
                    </h4>
                    <ClaimChips
                      text={activeTranslation.sections[i].content_markdown}
                      claims={claims}
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
