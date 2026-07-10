// Parsers for the set-once TAIEX sector-weight editor. Each accepts pasted text
// (one entry per line, comma / tab / multi-space separated) and is pure + testable.

export type SectorWeight = { sector: string; weight_pct: number };

/** Parse "sector, weight%" lines into weights, skipping blanks and malformed rows. */
export function parseWeights(text: string): SectorWeight[] {
  const rows: SectorWeight[] = [];
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const parts = trimmed
      .split(/[,\t]|\s{2,}|\s(?=[\d.]+%?$)/)
      .map((p) => p.trim())
      .filter(Boolean);
    if (parts.length < 2) continue;
    const weight = Number(parts[parts.length - 1].replace("%", ""));
    const sector = parts.slice(0, -1).join(" ").trim();
    if (sector && Number.isFinite(weight)) rows.push({ sector, weight_pct: weight });
  }
  return rows;
}

/** Parse "code, sector" lines into a stock-code → sector map. */
export function parseMap(text: string): Record<string, string> {
  const map: Record<string, string> = {};
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const parts = trimmed
      .split(/[,\t]|\s{2,}/)
      .map((p) => p.trim())
      .filter(Boolean);
    if (parts.length < 2) continue;
    map[parts[0]] = parts.slice(1).join(" ").trim();
  }
  return map;
}
