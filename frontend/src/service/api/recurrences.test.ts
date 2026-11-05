import { describe, expect, it } from 'vitest';
import { RECURRENCE_INTERVALS, formatNextRun } from './recurrences';

describe('recurrences helpers', () => {
  it('RECURRENCE_INTERVALS covers daily/weekly/monthly', () => {
    expect(RECURRENCE_INTERVALS).toContain('daily');
    expect(RECURRENCE_INTERVALS).toContain('weekly');
    expect(RECURRENCE_INTERVALS).toContain('monthly');
  });

  it('formatNextRun renders UTC-ish label', () => {
    expect(formatNextRun(null)).toBe('—');
    expect(formatNextRun('2026-11-04T10:00:00')).toContain('2026-11-04');
    expect(formatNextRun('2026-11-04T10:00:00')).toContain('UTC');
  });
});
