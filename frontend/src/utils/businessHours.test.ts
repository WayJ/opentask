import { describe, expect, it } from 'vitest';
import {
  WEEKDAY_KEYS,
  normalizeBusinessHours,
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

  it('defaults business hours disabled', () => {
    const bh = normalizeBusinessHours(null);
    expect(bh.enabled).toBe(false);
    expect(bh.windows.sun).toEqual([]);
  });

  it('validates timezone shape', () => {
    expect(validateTimezoneClient('Asia/Shanghai')).toBe('Asia/Shanghai');
    expect(validateTimezoneClient('')).toBeNull();
    expect(() => validateTimezoneClient('NotAZone')).toThrow(/timezone/);
  });
});
