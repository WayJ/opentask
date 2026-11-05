/** E64: known static holiday pack keys (region:year). */
export const E64_HOLIDAY_PACK_KEYS = [
  'CN:2026',
  'US:2026',
  'EU:2026',
  'UK:2026',
  'CN:2027',
  'US:2027',
  'EU:2027',
  'UK:2027'
] as const;

export function filterHolidayPackRows<T extends { region: string; year: number }>(
  rows: T[],
  opts?: { region?: string; year?: number | null }
): T[] {
  const region = opts?.region?.trim() ? opts.region.trim().toUpperCase() : null;
  const year =
    opts?.year === undefined || opts?.year === null || Number.isNaN(Number(opts.year))
      ? null
      : Number(opts.year);
  return rows.filter(r => {
    if (region && r.region.toUpperCase() !== region) return false;
    if (year !== null && r.year !== year) return false;
    return true;
  });
}
