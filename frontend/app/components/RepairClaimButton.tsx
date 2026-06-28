"use client";

import { useState } from "react";

export default function RepairClaimButton({
  claimId,
  apiUrl,
  live,
}: {
  claimId: string;
  apiUrl: string;
  live: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);

  async function repair() {
    if (!live || busy) return;
    setBusy(true);
    setError(false);
    try {
      const res = await fetch(`${apiUrl}/claims/${claimId}/repair`, { method: "POST" });
      if (!res.ok) throw new Error();
      window.location.reload();
    } catch {
      setError(true);
      setBusy(false);
    }
  }

  return (
    <span className="inline-flex items-center gap-2">
      <button
        type="button"
        onClick={repair}
        disabled={!live || busy}
        className="rounded-(--radius-ctl) border border-action/70 px-2 py-0.5 text-[11px] font-medium text-action transition-colors hover:bg-action hover:text-white disabled:opacity-40"
        title="Rewrite this claim using only its stored evidence quote"
      >
        {busy ? "Repairing..." : "Repair"}
      </button>
      {error && <span className="text-[11px] text-down">failed</span>}
    </span>
  );
}
