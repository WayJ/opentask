/** E50/E53: workspace business-hours helpers (client normalize / presets / exceptions). */

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

export const EXCEPTION_KINDS = ['closed', 'forced_open'] as const;
export type ExceptionKind = (typeof EXCEPTION_KINDS)[number];
export const MAX_EXCEPTIONS = 366;

export interface BhSegment {
  start: string;
  end: string;
}

export interface BusinessException {
  date: string;
  kind: ExceptionKind;
  windows?: BhSegment[];
}

export interface BusinessHours {
  enabled: boolean;
  windows: Record<WeekdayKey, BhSegment[]>;
  exceptions: BusinessException[];
}

const HHMM = /^([01]\d|2[0-3]):([0-5]\d)$/;
const DATE_RE = /^(\d{4})-(\d{2})-(\d{2})$/;

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

function validateDate(s: string): string {
  const raw = String(s || '').trim();
  const m = DATE_RE.exec(raw);
  if (!m) throw new Error(`非法日期: ${s}`);
  const y = Number(m[1]);
  const mo = Number(m[2]);
  const d = Number(m[3]);
  const dt = new Date(Date.UTC(y, mo - 1, d));
  if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== mo - 1 || dt.getUTCDate() !== d) {
    throw new Error(`非法日期: ${s}`);
  }
  return `${String(y).padStart(4, '0')}-${String(mo).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
}

function normalizeSegmentList(segs: BhSegment[] | null | undefined, label: string): BhSegment[] {
  const list = Array.isArray(segs) ? segs : [];
  if (list.length > 2) throw new Error(`${label} 每日最多 2 段`);
  const parsed = list.map(seg => {
    const start = String(seg?.start || '').trim();
    const end = String(seg?.end || '').trim();
    const sm = parseMinutes(start);
    const em = parseMinutes(end);
    if (sm >= em) throw new Error(`${label} 时段倒置或空: ${start}-${end}`);
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
  if (merged.length > 2) throw new Error(`${label} 每日最多 2 段`);
  return merged.map(({ start, end }) => ({ start, end }));
}

export function normalizeWindows(
  raw: Partial<Record<string, BhSegment[]>> | null | undefined
): Record<WeekdayKey, BhSegment[]> {
  const out = emptyWindows();
  const src = raw && typeof raw === 'object' ? raw : {};
  for (const key of WEEKDAY_KEYS) {
    out[key] = normalizeSegmentList((src[key] as BhSegment[] | undefined) || [], key);
  }
  return out;
}

export function normalizeExceptions(raw: unknown): BusinessException[] {
  if (raw == null) return [];
  if (!Array.isArray(raw)) throw new Error('exceptions 必须是数组');
  if (raw.length > MAX_EXCEPTIONS) throw new Error(`exceptions 最多 ${MAX_EXCEPTIONS} 条`);
  const seen = new Set<string>();
  const out: BusinessException[] = [];
  for (const item of raw) {
    if (!item || typeof item !== 'object') throw new Error('exception 必须是对象');
    const rec = item as Record<string, unknown>;
    const date = validateDate(String(rec.date ?? ''));
    const kind = String(rec.kind ?? '').trim() as ExceptionKind;
    if (!EXCEPTION_KINDS.includes(kind)) throw new Error(`未知 exception kind: ${kind}`);
    if (seen.has(date)) throw new Error(`重复 exception date: ${date}`);
    seen.add(date);
    const entry: BusinessException = { date, kind };
    if (kind === 'forced_open' && rec.windows != null) {
      entry.windows = normalizeSegmentList(rec.windows as BhSegment[], date);
    }
    out.push(entry);
  }
  out.sort((a, b) => a.date.localeCompare(b.date));
  return out;
}

/** Thin closed-day skip check for client preview / vitest. */
export function isClosedExceptionDay(date: string, exceptions: BusinessException[]): boolean {
  const d = String(date || '').trim();
  return exceptions.some(e => e.date === d && e.kind === 'closed');
}

export function normalizeBusinessHours(raw: Partial<BusinessHours> | null | undefined): BusinessHours {
  return {
    enabled: Boolean(raw?.enabled),
    windows: normalizeWindows(raw?.windows),
    exceptions: normalizeExceptions(raw?.exceptions ?? [])
  };
}

export function validateTimezoneClient(name: string | null | undefined): string | null {
  if (name == null) return null;
  const s = String(name).trim();
  if (!s) return null;
  if (!/^[A-Za-z_]+\/[A-Za-z0-9_\-+]+$/.test(s) && s !== 'UTC') {
    throw new Error(`非法 timezone: ${s}`);
  }
  return s;
}

/** E56: policy-level calendar overlay (partial inherit from WS). */
export interface PolicyCalendar {
  timezone?: string | null;
  windows?: Partial<Record<WeekdayKey, BhSegment[]>> | null;
  exceptions?: BusinessException[] | null;
}

export function normalizePolicyCalendar(
  raw: PolicyCalendar | Record<string, unknown> | null | undefined
): PolicyCalendar | null {
  if (raw == null) return null;
  if (typeof raw !== 'object') throw new Error('calendar 必须是对象或 null');
  const rec = raw as Record<string, unknown>;
  const keys = Object.keys(rec);
  if (!keys.length) return null;
  const out: PolicyCalendar = {};
  if ('timezone' in rec && rec.timezone != null) {
    out.timezone = validateTimezoneClient(String(rec.timezone));
  }
  if ('windows' in rec && rec.windows != null) {
    out.windows = normalizeWindows(rec.windows as Partial<Record<WeekdayKey, BhSegment[]>>);
  }
  if ('exceptions' in rec && rec.exceptions != null) {
    out.exceptions = normalizeExceptions(rec.exceptions);
  }
  return Object.keys(out).length ? out : null;
}

/** Merge policy overlay onto WS calendar for client preview / vitest (Q1a). */
export function mergeEffectiveCalendar(
  ws: { timezone?: string | null; businessHours?: BusinessHours | null },
  overlay: PolicyCalendar | null | undefined
): { timezone: string | null; windows: Record<WeekdayKey, BhSegment[]>; exceptions: BusinessException[] } | null {
  const bh = normalizeBusinessHours(ws.businessHours || null);
  if (!bh.enabled) return null;
  const cal = normalizePolicyCalendar(overlay ?? null) || {};
  const timezone =
    cal.timezone != null && cal.timezone !== ''
      ? String(cal.timezone)
      : ws.timezone
        ? String(ws.timezone)
        : null;
  const windows = cal.windows != null ? normalizeWindows(cal.windows) : bh.windows;
  const exceptions = cal.exceptions != null ? normalizeExceptions(cal.exceptions) : bh.exceptions;
  return { timezone, windows, exceptions };
}

export interface PackMergeResult {
  exceptions: BusinessException[];
  added: BusinessException[];
  replaced: Array<{ date: string; before: BusinessException; after: BusinessException }>;
  unchanged: BusinessException[];
  skipped: BusinessException[];
}

/** E58 Q3a: same date → pack wins; keep non-pack dates. */
export function mergeExceptionsPackWins(
  existing: unknown,
  packExceptions: unknown
): PackMergeResult {
  const base = normalizeExceptions(existing);
  const pack = normalizeExceptions(packExceptions);
  const byDate = new Map<string, BusinessException>();
  for (const e of base) byDate.set(e.date, { ...e, windows: e.windows ? [...e.windows] : undefined });
  const added: BusinessException[] = [];
  const replaced: Array<{ date: string; before: BusinessException; after: BusinessException }> = [];
  const unchanged: BusinessException[] = [];
  const skipped: BusinessException[] = [];
  const packDates = new Set(pack.map(e => e.date));
  for (const pe of pack) {
    const prev = byDate.get(pe.date);
    if (!prev) {
      byDate.set(pe.date, { ...pe, windows: pe.windows ? [...pe.windows] : undefined });
      added.push({ ...pe });
      continue;
    }
    const sameKind = prev.kind === pe.kind;
    const sameWin = JSON.stringify(prev.windows || null) === JSON.stringify(pe.windows || null);
    if (sameKind && sameWin) {
      unchanged.push({ ...prev });
    } else {
      byDate.set(pe.date, { ...pe, windows: pe.windows ? [...pe.windows] : undefined });
      replaced.push({ date: pe.date, before: { ...prev }, after: { ...pe } });
    }
  }
  for (const e of base) {
    if (!packDates.has(e.date)) unchanged.push({ ...e });
  }
  const exceptions = [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date));
  if (exceptions.length > MAX_EXCEPTIONS) {
    throw new Error(`exceptions 最多 ${MAX_EXCEPTIONS} 条`);
  }
  return { exceptions, added, replaced, unchanged, skipped };
}
