import { describe, expect, it } from 'vitest';
import {
  computeTimelineRange,
  isTimelineEmpty,
  issueTimelinePlacement,
  offsetDays,
  timelineDayWidth
} from './project-timeline';

describe('isTimelineEmpty', () => {
  it('true when no dates milestones or issues', () => {
    expect(isTimelineEmpty({ starts_at: null, target_date: null }, [], [])).toBe(true);
  });

  it('false when project has starts_at', () => {
    expect(isTimelineEmpty({ starts_at: '2026-11-01', target_date: null })).toBe(false);
  });

  it('false when milestones exist', () => {
    expect(isTimelineEmpty({}, [{ id: '1', target_date: null }])).toBe(false);
  });

  it('false when due issue exists', () => {
    expect(isTimelineEmpty({}, [], [{ id: '1', due_date: '2026-11-10' }])).toBe(false);
  });
});

describe('timelineDayWidth', () => {
  it('week wider than month', () => {
    expect(timelineDayWidth('week')).toBeGreaterThan(timelineDayWidth('month'));
  });
});

describe('computeTimelineRange', () => {
  it('returns null when empty', () => {
    expect(computeTimelineRange({})).toBeNull();
  });

  it('spans project dates with padding', () => {
    const range = computeTimelineRange(
      { starts_at: '2026-11-10T00:00:00.000Z', target_date: '2026-11-20T00:00:00.000Z' },
      { padDays: 2 }
    );
    expect(range).not.toBeNull();
    expect(offsetDays(range!.start, range!.end)).toBe(14); // 10 days span + 2+2 pad
  });
});


describe('issueTimelinePlacement (E73)', () => {
  it('bar when start and due', () => {
    expect(
      issueTimelinePlacement({
        id: '1',
        start_date: '2026-11-01',
        due_date: '2026-11-10'
      })
    ).toEqual({ kind: 'bar', start: '2026-11-01', end: '2026-11-10' });
  });

  it('dot when only due', () => {
    expect(issueTimelinePlacement({ id: '1', due_date: '2026-11-10' })).toEqual({
      kind: 'dot',
      at: '2026-11-10'
    });
  });

  it('null when only start', () => {
    expect(issueTimelinePlacement({ id: '1', start_date: '2026-11-01' })).toBeNull();
  });

  it('null when empty', () => {
    expect(issueTimelinePlacement({ id: '1' })).toBeNull();
  });
});

describe('isTimelineEmpty with start_date', () => {
  it('false when only start_date on issue', () => {
    expect(isTimelineEmpty({}, [], [{ id: '1', start_date: '2026-11-01' }])).toBe(false);
  });
});

describe('computeTimelineRange with start_date', () => {
  it('includes start_date in span', () => {
    const range = computeTimelineRange(
      {},
      {
        issues: [{ id: '1', start_date: '2026-11-01T00:00:00.000Z', due_date: '2026-11-10T00:00:00.000Z' }],
        padDays: 0
      }
    );
    expect(range).not.toBeNull();
    expect(offsetDays(range!.start, range!.end)).toBe(9);
  });
});
