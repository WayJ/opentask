import { describe, expect, it } from 'vitest';
import {
  buildInsightsSummaryParams,
  canEditReport,
  countOpenFromStatus,
  filtersToSummaryParams,
  insightsExportUrl,
  normalizeLabelIds,
  partitionReports,
  sumCompletedLastDays,
  sumVelocityPoints,
  type InsightsSavedReport
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

  it('normalizeLabelIds dedupes and drops empties', () => {
    expect(normalizeLabelIds(undefined)).toEqual([]);
    expect(normalizeLabelIds([])).toEqual([]);
    expect(normalizeLabelIds([1, '2', 1, null, '', 3])).toEqual([1, 2, 3]);
  });

  it('buildInsightsSummaryParams prefers labelIds comma OR; empty = no filter', () => {
    expect(buildInsightsSummaryParams({ labelIds: [] })).toEqual({});
    expect(buildInsightsSummaryParams({ labelIds: [3, 5] })).toEqual({ labelIds: '3,5' });
    // labelIds wins over labelId when both present at helper level
    expect(buildInsightsSummaryParams({ labelId: 9, labelIds: [1, 2] })).toEqual({ labelIds: '1,2' });
  });

  it('filtersToSummaryParams round-trips report filters', () => {
    expect(filtersToSummaryParams({})).toEqual({});
    expect(
      filtersToSummaryParams({
        projectId: 'p1',
        labelIds: [1, 1, 2],
        cycleId: 'c9',
        assigneeLimit: 8
      })
    ).toEqual({
      projectId: 'p1',
      labelIds: [1, 2],
      cycleId: 'c9',
      assigneeLimit: 8
    });
    const params = filtersToSummaryParams({ labelIds: [4, 5] });
    expect(buildInsightsSummaryParams(params)).toEqual({ labelIds: '4,5' });
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
    expect(insightsExportUrl({ labelIds: [3, 5] })).toBe('/api/insights/export.csv?labelIds=3%2C5');
  });
});

describe('insights shared reports helpers (E61)', () => {
  const base = (over: Partial<InsightsSavedReport>): InsightsSavedReport => ({
    id: over.id || 'r1',
    workspaceId: 'w1',
    ownerUserId: over.ownerUserId || 'u1',
    name: over.name || 'R',
    filters: over.filters || {},
    isDefault: Boolean(over.isDefault),
    visibility: over.visibility || 'personal',
    canEdit: over.canEdit,
    ...over
  });

  it('partitionReports splits mine vs team shared', () => {
    const rows = [
      base({ id: 'a', ownerUserId: 'me', visibility: 'personal', canEdit: true }),
      base({ id: 'b', ownerUserId: 'me', visibility: 'workspace', canEdit: true }),
      base({ id: 'c', ownerUserId: 'peer', visibility: 'workspace', canEdit: false }),
      base({ id: 'd', ownerUserId: 'peer', visibility: 'personal', canEdit: false })
    ];
    const { mine, shared } = partitionReports(rows, 'me');
    expect(mine.map(r => r.id).sort()).toEqual(['a', 'b']);
    expect(shared.map(r => r.id)).toEqual(['c']);
  });

  it('canEditReport prefers canEdit flag then ownerUserId', () => {
    expect(canEditReport(base({ canEdit: false, ownerUserId: 'me' }), 'me')).toBe(false);
    expect(canEditReport(base({ canEdit: true, ownerUserId: 'peer' }), 'me')).toBe(true);
    expect(canEditReport(base({ ownerUserId: 'me' }), 'me')).toBe(true);
    expect(canEditReport(base({ ownerUserId: 'peer' }), 'me')).toBe(false);
  });

  it('fork filters round-trip via filtersToSummaryParams', () => {
    const report = base({
      filters: { projectId: 'p1', labelIds: [9, 9, 3], cycleId: 'c1' },
      visibility: 'workspace',
      canEdit: false,
      ownerUserId: 'peer'
    });
    const params = filtersToSummaryParams(report.filters);
    expect(params).toEqual({ projectId: 'p1', labelIds: [9, 3], cycleId: 'c1' });
    expect(buildInsightsSummaryParams(params)).toEqual({
      projectId: 'p1',
      labelIds: '9,3',
      cycleId: 'c1'
    });
  });
});
