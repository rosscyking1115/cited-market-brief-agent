import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

function source(path: string): string {
  return readFileSync(resolve(process.cwd(), path), "utf8");
}

describe("public workspace routes", () => {
  it("keeps the company brief out of the radar route", () => {
    const root = source("app/page.tsx");
    expect(root).not.toContain("BriefCanvas");
    expect(root).not.toContain("EvidenceLedger");
    expect(root).not.toContain("Secondary module · Beta");
  });

  it("serves the brief from its own route without a region switcher", () => {
    const brief = source("app/brief/page.tsx");
    expect(brief).toContain("BriefCanvas");
    expect(brief).toContain("EvidenceLedger");
    expect(brief).not.toContain("RegionSwitcher");
  });

  it("keeps one server-resolved radar payload for truthful provenance", () => {
    const dashboard = source("app/components/MorningMarketDashboard.tsx");
    expect(dashboard).not.toContain("fetch(`${API_URL}/market-radar`");
    expect(dashboard).not.toContain("useState(initialRadar)");
  });
});
