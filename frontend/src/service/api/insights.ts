import { request } from '../request';

export interface InsightsAssigneeCount {
  assigneeId: string | null;
  assigneeName: string;
  count: number;
}

export interface InsightsCycleSnapshot {
  cycleId: string;
  cycleName: string;
  issueCount: number;
  completedCount: number;
  estimatePointsSum: number;
}

export interface InsightsDayBucket {
  date: string;
  created: number;
  completed: number;
}

export interface InsightsSummary {
  statusCounts: Record<string, number>;
  priorityCounts: Record<string, number>;
  assigneeCounts: InsightsAssigneeCount[];
  cycleSnapshot: InsightsCycleSnapshot | null;
  createdVsCompleted: InsightsDayBucket[];
}

export function fetchInsightsSummary(params?: { cycleId?: string; assigneeLimit?: number }) {
  return request<InsightsSummary>({
    url: '/api/insights/summary',
    method: 'get',
    params: {
      cycleId: params?.cycleId,
      assigneeLimit: params?.assigneeLimit
    }
  });
}

/** 开放 Issue 数（非 resolved/closed） */
export function countOpenFromStatus(statusCounts: Record<string, number> | undefined | null): number {
  if (!statusCounts) return 0;
  const done = new Set(['resolved', 'closed']);
  return Object.entries(statusCounts).reduce((sum, [status, n]) => (done.has(status) ? sum : sum + Number(n || 0)), 0);
}

/** 近 N 日 completed 合计 */
export function sumCompletedLastDays(rows: InsightsDayBucket[] | undefined | null, days: number): number {
  if (!rows?.length) return 0;
  return rows.slice(-days).reduce((sum, row) => sum + Number(row.completed || 0), 0);
}
