import { describe, expect, it } from 'vitest';
import { countOpenFromStatus, sumCompletedLastDays } from './insights';

describe('insights helpers', () => {
  it('countOpenFromStatus excludes done', () => {
    expect(
      countOpenFromStatus({
        open: 2,
        in_progress: 1,
        resolved: 4,
        closed: 1
      })
    ).toBe(3);
  });

  it('sumCompletedLastDays uses trailing window', () => {
    const rows = [
      { date: '2026-10-20', created: 1, completed: 9 },
      { date: '2026-10-21', created: 0, completed: 1 },
      { date: '2026-10-22', created: 2, completed: 3 }
    ];
    expect(sumCompletedLastDays(rows, 2)).toBe(4);
    expect(sumCompletedLastDays(rows, 7)).toBe(13);
  });
});
