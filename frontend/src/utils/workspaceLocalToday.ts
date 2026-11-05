/** E67: workspace IANA tz → local calendar day (YYYY-MM-DD). Empty/invalid → UTC. */

export function resolveWorkspaceTzClient(tz: string | null | undefined): string {
  const s = (tz ?? '').trim();
  if (!s) return 'UTC';
  try {
    Intl.DateTimeFormat('en-US', { timeZone: s }).format(new Date());
    return s;
  } catch {
    return 'UTC';
  }
}

export function localTodayIso(tz: string | null | undefined, now: Date = new Date()): string {
  const zone = resolveWorkspaceTzClient(tz);
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: zone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).formatToParts(now);
  const y = parts.find(p => p.type === 'year')?.value;
  const m = parts.find(p => p.type === 'month')?.value;
  const d = parts.find(p => p.type === 'day')?.value;
  return `${y}-${m}-${d}`;
}
