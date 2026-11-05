import { describe, expect, it } from 'vitest';
import { E64_HOLIDAY_PACK_KEYS, filterHolidayPackRows } from './holidayPacks';

describe('E64 holiday packs', () => {
  it('lists EU/UK and 2027 keys', () => {
    for (const key of [
      'EU:2026',
      'UK:2026',
      'CN:2027',
      'US:2027',
      'EU:2027',
      'UK:2027',
      'CN:2026',
      'US:2026'
    ]) {
      expect(E64_HOLIDAY_PACK_KEYS).toContain(key);
    }
  });

  it('filters by region and year', () => {
    const rows = [
      { region: 'CN', year: 2026 },
      { region: 'EU', year: 2026 },
      { region: 'EU', year: 2027 },
      { region: 'UK', year: 2026 }
    ];
    expect(filterHolidayPackRows(rows, { region: 'eu', year: 2027 })).toEqual([
      { region: 'EU', year: 2027 }
    ]);
    expect(filterHolidayPackRows(rows, { region: 'UK' })).toHaveLength(1);
    expect(filterHolidayPackRows(rows)).toHaveLength(4);
  });
});
