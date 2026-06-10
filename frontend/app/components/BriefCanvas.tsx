"use client";

// Brief canvas (Phase 3): per-section accept / edit / reject / needs-source actions
// plus brief approval. Approval is blocked until every section is resolved
// (needs_source blocks — that's the review discipline the audit trail sells).

import { useState } from "react";
import type { ClaimRow, BriefSectionData, SectionEdit } from "@/lib/api";

const ACTIONS = [
  { action: "accept", label: "✓ Accept", cls: "border-up/60 text-up" },
  { action: "edit", label: "✎ Edit", cls: "border-action/60 text-action" },
  { action: "reject", label: "✗ Reject", cls: "border-down/60 text-down" },
  { action: "needs_source", label: "⚑ Needs source", cls: "border-flag/60 text-flag" },
] as const;

function ClaimChips({ text, claims }: { text: string; claims: ClaimRow[] }) {
  const parts = text.split(/(\[#\d+\])/g);
  return (
    <p className="mt-1.5 leading-relaxed text-neutral-50">
      {parts.map((part, i) => {
        const match = /^\[#(\d+)\]$/.exec(part);
        if (!match) return <span key={i}>{part}</span>;
        const idx = Number(match[1]);
        const ok = claims.find((c) => c.index === idx)?.support_status === "supported";
        return (
          <a
            key={i}
            href="#ledger"
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
    </p>
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

  const resolved = sections.every((_, i) => {
    const e = edits[String(i)];
    return e && e.action !== "needs_source";
  });
  const approved = status === "approved";

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
    if (!live || approved || !resolved || busy) return;
    setBusy(true);
    try {
      const res = await fetch(`${apiUrl}/briefs/${briefId}/approve`, { method: "POST" });
      if (res.ok) setStatus("approved");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="mt-4 flex items-center justify-between border-t border-hairline pt-3">
        <span className="th-label">
          Review · status{" "}
          <span className={approved ? "text-up" : "text-neutral-50"}>{status}</span>
        </span>
        <button
          type="button"
          onClick={approve}
          disabled={!live || approved || !resolved || busy}
          title={
            approved
              ? "Approved"
              : resolved
                ? "Approve brief"
                : "Resolve every section first (needs-source blocks approval)"
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

      {sections.map((section, i) => {
        const edit = edits[String(i)];
        const isEditing = editing === i;
        return (
          <section
            key={section.title + i}
            className={`mt-4 rounded-(--radius-ctl) border-l-2 pl-4 ${
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
              <h3 className="text-sm font-semibold text-neutral-30">{section.title}</h3>
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
                      className={`rounded-(--radius-ctl) border px-1.5 py-0.5 text-[10px] transition-opacity disabled:opacity-40 ${
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
              <ClaimChips
                text={edit?.action === "edit" && edit.content ? edit.content : section.content_markdown}
                claims={claims}
              />
            )}
          </section>
        );
      })}
    </div>
  );
}
