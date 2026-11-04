import { downloadRequest, request } from '../request';

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

export interface InsightsVelocityBucket {
  date: string;
  completedPoints: number;
}

export interface InsightsEstimateVelocity {
  windowDays: number;
  buckets: InsightsVelocityBucket[];
}

export interface InsightsSummary {
  statusCounts: Record<string, number>;
  priorityCounts: Record<string, number>;
  assigneeCounts: InsightsAssigneeCount[];
  cycleSnapshot: InsightsCycleSnapshot | null;
  createdVsCompleted: InsightsDayBucket[];
  estimateVelocity?: InsightsEstimateVelocity;
}

export interface InsightsSummaryParams {
  cycleId?: string | null;
  projectId?: string | null;
  labelId?: number | null;
  assigneeLimit?: number;
}

/** 过滤参数归一化：空串 / null / undefined 省略键 */
export function buildInsightsSummaryParams(
  input?: InsightsSummaryParams | null
): Record<string, string | number> {
  const out: Record<string, string | number> = {};
  if (!input) return out;
  if (input.cycleId != null && String(input.cycleId).trim() !== '') {
    out.cycleId = String(input.cycleId);
  }
  if (input.projectId != null && String(input.projectId).trim() !== '') {
    out.projectId = String(input.projectId);
  }
  if (input.labelId != null && Number.isFinite(Number(input.labelId))) {
    out.labelId = Number(input.labelId);
  }
  if (input.assigneeLimit != null && Number.isFinite(Number(input.assigneeLimit))) {
    out.assigneeLimit = Number(input.assigneeLimit);
  }
  return out;
}

export function fetchInsightsSummary(params?: InsightsSummaryParams) {
  return request<InsightsSummary>({
    url: '/api/insights/summary',
    method: 'get',
    params: buildInsightsSummaryParams(params)
  });
}

/** E55：导出 Insights CSV（blob） */
export function downloadInsightsExport(params?: InsightsSummaryParams) {
  return downloadRequest<Blob>({
    url: '/api/insights/export.csv',
    method: 'GET',
    params: buildInsightsSummaryParams(params),
    responseType: 'blob'
  });
}

/** 近 N 日 completed points 合计；空窗 → 0 */
export function sumVelocityPoints(
  buckets: InsightsVelocityBucket[] | undefined | null,
  days?: number
): number {
  if (!buckets?.length) return 0;
  const slice = days == null ? buckets : buckets.slice(-days);
  return slice.reduce((sum, row) => sum + Number(row.completedPoints || 0), 0);
}

/** 拼 export.csv 相对路径（不含 origin） */
export function insightsExportUrl(params?: InsightsSummaryParams): string {
  const q = buildInsightsSummaryParams(params);
  const qs = new URLSearchParams();
  Object.entries(q).forEach(([k, v]) => qs.set(k, String(v)));
  const s = qs.toString();
  return s ? `/api/insights/export.csv?${s}` : '/api/insights/export.csv';
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
