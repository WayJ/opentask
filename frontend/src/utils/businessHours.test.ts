import { describe, expect, it } from 'vitest';
import {
  MAX_EXCEPTIONS,
  WEEKDAY_KEYS,
  isClosedExceptionDay,
  mergeEffectiveCalendar,
  normalizeBusinessHours,
  normalizeExceptions,
  normalizePolicyCalendar,
  mergeExceptionsPackWins,
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

describe('E56 policy calendar overlay', () => {
  it('normalizePolicyCalendar empty ≡ null; partial fields; rejects bad tz/kind', () => {
    expect(normalizePolicyCalendar(null)).toBeNull();
    expect(normalizePolicyCalendar({})).toBeNull();
    expect(normalizePolicyCalendar({ timezone: 'UTC' })).toEqual({ timezone: 'UTC' });
    expect(() => normalizePolicyCalendar({ timezone: 'NotAZone' })).toThrow(/timezone/);
    expect(() =>
      normalizePolicyCalendar({ exceptions: [{ date: '2026-11-05', kind: 'holiday' as never }] })
    ).toThrow(/kind/);
  });

  it('mergeEffectiveCalendar empty overlay ≡ WS; partial override; enabled=false → null', () => {
    const ws = {
      timezone: 'Asia/Shanghai',
      businessHours: {
        enabled: true,
        windows: weekdayPreset0918(),
        exceptions: [{ date: '2026-10-01', kind: 'closed' as const }]
      }
    };
    const full = mergeEffectiveCalendar(ws, null);
    expect(full?.timezone).toBe('Asia/Shanghai');
    expect(full?.exceptions[0].date).toBe('2026-10-01');
    const tzOnly = mergeEffectiveCalendar(ws, { timezone: 'UTC' });
    expect(tzOnly?.timezone).toBe('UTC');
    expect(tzOnly?.exceptions[0].date).toBe('2026-10-01');
    const exOnly = mergeEffectiveCalendar(ws, {
      exceptions: [{ date: '2026-11-07', kind: 'forced_open' }]
    });
    expect(exOnly?.timezone).toBe('Asia/Shanghai');
    expect(exOnly?.exceptions).toEqual([{ date: '2026-11-07', kind: 'forced_open' }]);
    expect(
      mergeEffectiveCalendar(
        { timezone: 'Asia/Shanghai', businessHours: { enabled: false, windows: weekdayPreset0918(), exceptions: [] } },
        { timezone: 'UTC', windows: weekdayPreset0918() }
      )
    ).toBeNull();
  });
});

describe('E58 holiday pack merge', () => {
  it('pack wins same date; keeps non-pack; filters via normalize', () => {
    const out = mergeExceptionsPackWins(
      [
        { date: '2026-10-01', kind: 'closed' },
        { date: '2026-06-01', kind: 'closed' }
      ],
      [
        { date: '2026-10-01', kind: 'forced_open' },
        { date: '2026-10-02', kind: 'closed' }
      ]
    );
    const by = Object.fromEntries(out.exceptions.map(e => [e.date, e]));
    expect(by['2026-10-01'].kind).toBe('forced_open');
    expect(by['2026-06-01']).toBeTruthy();
    expect(by['2026-10-02']).toBeTruthy();
    expect(out.replaced.some(r => r.date === '2026-10-01')).toBe(true);
    expect(out.added.some(a => a.date === '2026-10-02')).toBe(true);
    expect(out.unchanged.some(u => u.date === '2026-06-01')).toBe(true);
  });
});
