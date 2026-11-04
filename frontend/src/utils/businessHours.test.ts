import { describe, expect, it } from 'vitest';
import {
  MAX_EXCEPTIONS,
  WEEKDAY_KEYS,
  isClosedExceptionDay,
  normalizeBusinessHours,
  normalizeExceptions,
  normalizeWindows,
  validateTimezoneClient,
  weekdayPreset0918
} from './businessHours';

describe('businessHours helpers', () => {
  it('exposes mon..sun keys', () => {
    expect(WEEKDAY_KEYS).toEqual(['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']);
  });

  it('preset is weekday 09-18', () => {
    const p = weekdayPreset0918();
    expect(p.mon).toEqual([{ start: '09:00', end: '18:00' }]);
    expect(p.sat).toEqual([]);
  });

  it('merges overlapping segments', () => {
    const out = normalizeWindows({
      mon: [
        { start: '09:00', end: '12:00' },
        { start: '11:00', end: '14:00' }
      ]
    });
    expect(out.mon).toEqual([{ start: '09:00', end: '14:00' }]);
  });

  it('rejects inverted and >2 segments', () => {
    expect(() => normalizeWindows({ mon: [{ start: '18:00', end: '09:00' }] })).toThrow(/倒置/);
    expect(() =>
      normalizeWindows({
        mon: [
          { start: '09:00', end: '10:00' },
          { start: '11:00', end: '12:00' },
          { start: '13:00', end: '14:00' }
        ]
      })
    ).toThrow(/2/);
  });

  it('defaults business hours disabled with empty exceptions', () => {
    const bh = normalizeBusinessHours(null);
    expect(bh.enabled).toBe(false);
    expect(bh.windows.sun).toEqual([]);
    expect(bh.exceptions).toEqual([]);
  });

  it('validates timezone shape', () => {
    expect(validateTimezoneClient('Asia/Shanghai')).toBe('Asia/Shanghai');
    expect(validateTimezoneClient('')).toBeNull();
    expect(() => validateTimezoneClient('NotAZone')).toThrow(/timezone/);
  });

  it('normalizes exceptions and rejects dup/bad kind/date', () => {
    const out = normalizeExceptions([
      { date: '2026-11-07', kind: 'forced_open', windows: [{ start: '10:00', end: '12:00' }] },
      { date: '2026-11-06', kind: 'closed' }
    ]);
    expect(out[0]).toEqual({ date: '2026-11-06', kind: 'closed' });
    expect(out[1].kind).toBe('forced_open');
    expect(() =>
      normalizeExceptions([
        { date: '2026-11-05', kind: 'closed' },
        { date: '2026-11-05', kind: 'forced_open' }
      ])
    ).toThrow(/重复/);
    expect(() => normalizeExceptions([{ date: '2026-11-05', kind: 'holiday' }])).toThrow(/kind/);
    expect(() => normalizeExceptions([{ date: '2026-13-40', kind: 'closed' }])).toThrow(/日期/);
  });

  it('closed day skip helper', () => {
    const ex = normalizeExceptions([{ date: '2026-10-01', kind: 'closed' }]);
    expect(isClosedExceptionDay('2026-10-01', ex)).toBe(true);
    expect(isClosedExceptionDay('2026-10-02', ex)).toBe(false);
  });

  it('rejects more than MAX_EXCEPTIONS', () => {
    const many = Array.from({ length: MAX_EXCEPTIONS + 1 }, (_, i) => {
      const day = (i % 28) + 1;
      const month = Math.floor(i / 28) + 1;
      return { date: `2028-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`, kind: 'closed' as const };
    });
    expect(() => normalizeExceptions(many)).toThrow(/366/);
  });
});
