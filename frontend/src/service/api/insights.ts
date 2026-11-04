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
  /** 单 label 兼容别名；与 labelIds 勿同用 */
  labelId?: number | null;
  /** 多 label OR；空数组 = 不过滤 */
  labelIds?: number[] | null;
  assigneeLimit?: number;
}

export interface InsightsReportFilters {
  projectId?: string;
  labelIds?: number[];
  cycleId?: string;
  assigneeLimit?: number;
}

export interface InsightsSavedReport {
  id: string;
  workspaceId: string;
  ownerUserId: string;
  name: string;
  filters: InsightsReportFilters;
  isDefault: boolean;
  createdAt?: string | null;
  updatedAt?: string | null;
}

/** 归一化 labelIds：去重保序；非法/空 → [] */
export function normalizeLabelIds(input?: Array<number | string | null | undefined> | null): number[] {
  if (!input?.length) return [];
  const seen = new Set<number>();
  const out: number[] = [];
  for (const raw of input) {
    if (raw == null || raw === '') continue;
    const n = Number(raw);
    if (!Number.isFinite(n)) continue;
    if (seen.has(n)) continue;
    seen.add(n);
    out.push(n);
  }
  return out;
}

/** 过滤参数归一化：空串 / null / undefined / 空 labelIds 省略键 */
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
  const ids = normalizeLabelIds(input.labelIds);
  if (ids.length) {
    // 逗号串：后端 parse_label_ids_query 支持；避免与 labelId 冲突
    out.labelIds = ids.join(',');
  } else if (input.labelId != null && Number.isFinite(Number(input.labelId))) {
    out.labelId = Number(input.labelId);
  }
  if (input.assigneeLimit != null && Number.isFinite(Number(input.assigneeLimit))) {
    out.assigneeLimit = Number(input.assigneeLimit);
  }
  return out;
}

/** 报表 filters → summary params（Q4a round-trip） */
export function filtersToSummaryParams(filters?: InsightsReportFilters | null): InsightsSummaryParams {
  if (!filters) return {};
  const out: InsightsSummaryParams = {};
  if (filters.projectId) out.projectId = filters.projectId;
  if (filters.cycleId) out.cycleId = filters.cycleId;
  const ids = normalizeLabelIds(filters.labelIds);
  if (ids.length) out.labelIds = ids;
  if (filters.assigneeLimit != null) out.assigneeLimit = filters.assigneeLimit;
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

export function fetchInsightsReports() {
  return request<{ rows: InsightsSavedReport[] }>({
    url: '/api/insights/reports',
    method: 'get'
  });
}

export function createInsightsReport(body: {
  name: string;
  filters?: InsightsReportFilters;
  isDefault?: boolean;
}) {
  return request<InsightsSavedReport>({
    url: '/api/insights/reports',
    method: 'post',
    data: {
      name: body.name,
      filters: body.filters || {},
      isDefault: Boolean(body.isDefault)
    }
  });
}

export function patchInsightsReport(
  id: string,
  body: { name?: string; filters?: InsightsReportFilters; isDefault?: boolean }
) {
  return request<InsightsSavedReport>({
    url: `/api/insights/reports/${id}`,
    method: 'patch',
    data: body
  });
}

export function deleteInsightsReport(id: string) {
  return request<{ id: string }>({
    url: `/api/insights/reports/${id}`,
    method: 'delete'
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
