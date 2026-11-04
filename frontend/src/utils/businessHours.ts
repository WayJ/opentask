/** E50: workspace business-hours helpers (client normalize / presets). */

export const WEEKDAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;
export type WeekdayKey = (typeof WEEKDAY_KEYS)[number];

export const WEEKDAY_LABELS: Record<WeekdayKey, string> = {
  mon: '周一',
  tue: '周二',
  wed: '周三',
  thu: '周四',
  fri: '周五',
  sat: '周六',
  sun: '周日'
};

export interface BhSegment {
  start: string;
  end: string;
}

export interface BusinessHours {
  enabled: boolean;
  windows: Record<WeekdayKey, BhSegment[]>;
}

const HHMM = /^([01]\d|2[0-3]):([0-5]\d)$/;

export function emptyWindows(): Record<WeekdayKey, BhSegment[]> {
  return {
    mon: [],
    tue: [],
    wed: [],
    thu: [],
    fri: [],
    sat: [],
    sun: []
  };
}

export function weekdayPreset0918(): Record<WeekdayKey, BhSegment[]> {
  const w = emptyWindows();
  for (const d of ['mon', 'tue', 'wed', 'thu', 'fri'] as WeekdayKey[]) {
    w[d] = [{ start: '09:00', end: '18:00' }];
  }
  return w;
}

function parseMinutes(s: string): number {
  const m = HHMM.exec(String(s || '').trim());
  if (!m) throw new Error(`非法 HH:MM: ${s}`);
  return Number(m[1]) * 60 + Number(m[2]);
}

export function normalizeWindows(
  raw: Partial<Record<string, BhSegment[]>> | null | undefined
): Record<WeekdayKey, BhSegment[]> {
  const out = emptyWindows();
  const src = raw && typeof raw === 'object' ? raw : {};
  for (const key of WEEKDAY_KEYS) {
    const segs = (src[key] as BhSegment[] | undefined) || [];
    if (!Array.isArray(segs)) throw new Error(`${key} windows 必须是数组`);
    if (segs.length > 2) throw new Error(`${key} 每日最多 2 段`);
    const parsed = segs.map(seg => {
      const start = String(seg?.start || '').trim();
      const end = String(seg?.end || '').trim();
      const sm = parseMinutes(start);
      const em = parseMinutes(end);
      if (sm >= em) throw new Error(`${key} 时段倒置或空: ${start}-${end}`);
      return { start, end, sm, em };
    });
    parsed.sort((a, b) => a.sm - b.sm);
    const merged: { start: string; end: string; sm: number; em: number }[] = [];
    for (const item of parsed) {
      const last = merged[merged.length - 1];
      if (last && item.sm <= last.em) {
        if (item.em > last.em) {
          last.em = item.em;
          last.end = item.end;
        }
      } else {
        merged.push({ ...item });
      }
    }
    if (merged.length > 2) throw new Error(`${key} 每日最多 2 段`);
    out[key] = merged.map(({ start, end }) => ({ start, end }));
  }
  return out;
}

export function normalizeBusinessHours(raw: Partial<BusinessHours> | null | undefined): BusinessHours {
  return {
    enabled: Boolean(raw?.enabled),
    windows: normalizeWindows(raw?.windows)
  };
}

export function validateTimezoneClient(name: string | null | undefined): string | null {
  if (name == null) return null;
  const s = String(name).trim();
  if (!s) return null;
  // thin client check — full IANA validation is BE; reject obvious junk
  if (!/^[A-Za-z_]+\/[A-Za-z0-9_\-+]+$/.test(s) && s !== 'UTC') {
    throw new Error(`非法 timezone: ${s}`);
  }
  return s;
}
