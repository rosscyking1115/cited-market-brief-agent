"use client";

import FundHoldingsParser from "@/app/components/FundHoldingsParser";
import SectorAttributionPanel from "@/app/components/SectorAttributionPanel";
import type { FundAttributionPayload } from "@/lib/api";

// The fund + sector attribution tools are Taiwan-only (TWSE prices, TAIEX benchmark).
// page.tsx renders this inside <ShowOnTaiwan>, so it always shows the Taiwan sections.
export default function FundAttributionPanel({
  latest,
}: {
  latest: FundAttributionPayload | null;
}) {
  return (
    <>
      <FundHoldingsParser initialResult={latest} />
      <SectorAttributionPanel />
    </>
  );
}
