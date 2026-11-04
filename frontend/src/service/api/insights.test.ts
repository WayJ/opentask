import { describe, expect, it } from 'vitest';
import {
  buildInsightsSummaryParams,
  countOpenFromStatus,
  insightsExportUrl,
  sumCompletedLastDays,
  sumVelocityPoints
} from './insights';

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

  it('buildInsightsSummaryParams omits empty values', () => {
    expect(buildInsightsSummaryParams(undefined)).toEqual({});
    expect(buildInsightsSummaryParams({})).toEqual({});
    expect(
      buildInsightsSummaryParams({
        cycleId: '',
        projectId: null,
        labelId: undefined
      })
    ).toEqual({});
    expect(
      buildInsightsSummaryParams({
        cycleId: 'c1',
        projectId: 'p1',
        labelId: 7,
        assigneeLimit: 5
      })
    ).toEqual({ cycleId: 'c1', projectId: 'p1', labelId: 7, assigneeLimit: 5 });
  });

  it('sumVelocityPoints handles empty window', () => {
    expect(sumVelocityPoints(undefined)).toBe(0);
    expect(sumVelocityPoints([])).toBe(0);
    expect(
      sumVelocityPoints([
        { date: '2026-11-01', completedPoints: 3 },
        { date: '2026-11-02', completedPoints: 5 }
      ])
    ).toBe(8);
    expect(
      sumVelocityPoints(
        [
          { date: '2026-11-01', completedPoints: 3 },
          { date: '2026-11-02', completedPoints: 5 }
        ],
        1
      )
    ).toBe(5);
  });

  it('insightsExportUrl builds query', () => {
    expect(insightsExportUrl()).toBe('/api/insights/export.csv');
    expect(insightsExportUrl({ projectId: 'p1', labelId: 3 })).toBe(
      '/api/insights/export.csv?projectId=p1&labelId=3'
    );
  });
});
