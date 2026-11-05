/** E76: http(s) URL helpers for Issue external links. */

export function isHttpUrl(url: string): boolean {
  const normalized = (url || '').trim();
  if (!normalized) return false;
  try {
    const parsed = new URL(normalized);
    return (parsed.protocol === 'http:' || parsed.protocol === 'https:') && Boolean(parsed.hostname);
  } catch {
    return false;
  }
}

export function hostnameFromUrl(url: string): string {
  const normalized = (url || '').trim();
  if (!normalized) return '';
  try {
    const parsed = new URL(normalized);
    return parsed.hostname || normalized;
  } catch {
    return normalized;
  }
}
