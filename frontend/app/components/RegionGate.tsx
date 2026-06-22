"use client";

import type { ReactNode } from "react";
import { useRegion } from "@/app/components/RegionProvider";

// The Taiwan edition is the focused consumer view (news + ETF tool only). These
// gates keep the developer/analyst surface — the SEC-brief module, market context
// rails, plan blocks, and internal badges — for the other regions only. Both gates
// return null on the first (server + client) render for TW, so there is no
// hydration mismatch: TW defaults match on server and client.

export function HideOnTaiwan({ children }: { children: ReactNode }) {
  const { profile } = useRegion();
  if (profile.region === "TW") return null;
  return <>{children}</>;
}

export function ShowOnTaiwan({ children }: { children: ReactNode }) {
  const { profile } = useRegion();
  if (profile.region !== "TW") return null;
  return <>{children}</>;
}
