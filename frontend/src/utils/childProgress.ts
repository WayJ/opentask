/** E70: format / percent helpers for childProgress payloads. */

export interface ChildProgressLike {
  total: number;
  done: number;
  open?: number;
  percent: number | null;
}

export function formatChildProgress(cp?: ChildProgressLike | null): string | null {
  if (!cp || !cp.total) return null;
  return `${cp.done}/${cp.total}`;
}

export function formatChildProgressLabel(cp?: ChildProgressLike | null): string | null {
  const base = formatChildProgress(cp);
  if (!base || !cp) return null;
  if (cp.percent == null) return base;
  return `${base} (${cp.percent}%)`;
}

export function childProgressPercent(cp?: ChildProgressLike | null): number {
  if (!cp || !cp.total) return 0;
  return cp.percent ?? 0;
}
