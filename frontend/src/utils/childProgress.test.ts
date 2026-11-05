import { describe, expect, it } from 'vitest';
import { childProgressPercent, formatChildProgress, formatChildProgressLabel } from './childProgress';

describe('childProgress', () => {
  it('returns null for empty / missing', () => {
    expect(formatChildProgress(null)).toBeNull();
    expect(formatChildProgress(undefined)).toBeNull();
    expect(formatChildProgress({ total: 0, done: 0, open: 0, percent: null })).toBeNull();
    expect(formatChildProgressLabel(null)).toBeNull();
  });

  it('formats mixed and all-done', () => {
    expect(formatChildProgress({ total: 5, done: 3, open: 2, percent: 60 })).toBe('3/5');
    expect(formatChildProgressLabel({ total: 5, done: 3, open: 2, percent: 60 })).toBe('3/5 (60%)');
    expect(formatChildProgress({ total: 3, done: 3, open: 0, percent: 100 })).toBe('3/3');
    expect(childProgressPercent({ total: 5, done: 3, open: 2, percent: 60 })).toBe(60);
    expect(childProgressPercent({ total: 0, done: 0, percent: null })).toBe(0);
  });
});
