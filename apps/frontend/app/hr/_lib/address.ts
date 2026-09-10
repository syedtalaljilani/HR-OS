const LABEL_PREFIX =
  /^\s*(head\s*office|registered\s*office|office|plant|factory|shop|plot|address)\s*[:.\-]+\s*/i;

function splitCleanLines(raw: string): string[] {
  const lines: string[] = [];
  for (const rawLine of raw.split(/\r?\n/)) {
    let line = rawLine.trim();
    // Drop appended map/website links (e.g. the "Map: <url>" convenience).
    line = line.replace(/^map\s*:\s*\S+.*$/i, "").trim();
    line = line.replace(LABEL_PREFIX, "").trim();
    if (line) lines.push(line);
  }
  return lines;
}

/**
 * Turn a freeform office-address string into a clean, geocodable query.
 *
 * Real-world values often carry labels or stray fragments ("Head Office:",
 * "Plot No," with no number) that make both OpenStreetMap and Google Maps fail
 * to find the place. Strips them so the remaining address geocodes reliably.
 */
export function cleanAddressQuery(raw: string): string {
  const joined = splitCleanLines(raw).join(", ");
  return joined
    // Standalone "plot no" / "plot" / "shop" fragments without a number.
    .replace(/\b(?:plot|shop)\s*(?:no\.?)?\s*(?=,|$)/gi, "")
    // "House/office/address" labels found mid-string (only when followed by a
    // separator like ":", so a real "Plot 09" is never eaten).
    .replace(/\b(?:head\s*office|registered\s*office|office|plant|factory|shop|plot|address)\s*[:.\-]+\s*/gi, "")
    // Collapse any duplicated/unattached separators left above.
    .replace(/(,\s*)+/g, ", ")
    .replace(/\s{2,}/g, " ")
    .replace(/^[,\s]+|[,\s]+$/g, "")
    .trim();
}

/**
 * Variations from most-specific to least-specific, so geocoders can succeed on
 * the tail of an address when the full string fails (e.g. estate or city only).
 */
export function addressSearchAttempts(raw: string): string[] {
  const cleaned = cleanAddressQuery(raw);
  if (!cleaned) return [];
  const parts = cleaned.split(",").map((p) => p.trim()).filter(Boolean);
  const attempts = [cleaned];
  for (let i = 1; i < Math.min(parts.length, 5); i++) {
    attempts.push(parts.slice(i).join(", "));
  }
  return Array.from(new Set(attempts));
}