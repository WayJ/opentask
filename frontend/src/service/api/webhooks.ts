import { request } from '../request';

export const WEBHOOK_EVENTS = [
  'issue.created',
  'issue.updated',
  'issue.status_changed',
  'comment.created',
  'issue.custom_field_changed',
  'issue.sla_breached',
  'issue.assignee_changed',
  'issue.label_added',
  'issue.label_removed',
  'issue.cycle_changed',
  'issue.estimate_changed',
  'issue.project_changed',
  'issue.sla_paused',
  'issue.sla_resumed'
] as const;

export const WEBHOOK_EVENT_LABELS: Record<(typeof WEBHOOK_EVENTS)[number], string> = {
  'issue.created': 'Issue 创建',
  'issue.updated': 'Issue 更新',
  'issue.status_changed': 'Issue 状态变更',
  'comment.created': '评论创建',
  'issue.custom_field_changed': '自定义字段变更',
  'issue.sla_breached': 'SLA 违约',
  'issue.assignee_changed': '经办人变更',
  'issue.label_added': '添加标签',
  'issue.label_removed': '移除标签',
  'issue.cycle_changed': 'Cycle 变更',
  'issue.estimate_changed': '估点变更',
  'issue.project_changed': '项目变更',
  'issue.sla_paused': 'SLA 暂停',
  'issue.sla_resumed': 'SLA 恢复'
};

export type WebhookEvent = (typeof WEBHOOK_EVENTS)[number];

/** E51 Q3a：集成常用预设（cycle/estimate/project/sla_*） */
export const INTEGRATION_PRESET_EVENTS: WebhookEvent[] = [
  'issue.cycle_changed',
  'issue.estimate_changed',
  'issue.project_changed',
  'issue.sla_paused',
  'issue.sla_resumed'
];

export function applyIntegrationPreset(current: string[]): string[] {
  const out = [...current];
  for (const ev of INTEGRATION_PRESET_EVENTS) {
    if (!out.includes(ev)) out.push(ev);
  }
  return out;
}

export function clearIntegrationPreset(current: string[]): string[] {
  const drop = new Set<string>(INTEGRATION_PRESET_EVENTS);
  return current.filter(e => !drop.has(e));
}

export function filterDeliveriesByEvent<T extends { eventType: string }>(
  list: T[],
  eventType: string | 'all'
): T[] {
  if (!eventType || eventType === 'all') return list;
  return list.filter(d => d.eventType === eventType);
}

export interface WebhookDelivery {
  id: string;
  webhookId: string;
  eventType: string;
  success: boolean;
  statusCode?: number | null;
  attempt: number;
  latencyMs?: number | null;
  error?: string | null;
  createdAt?: string | null;
  status?: string | null;
  nextAttemptAt?: string | null;
  deliveryId?: string | null;
  replayable?: boolean;
  maxAttempts?: number;
}

export interface WebhookRow {
  id: string;
  workspaceId: string;
  name?: string | null;
  url: string;
  events: string[];
  enabled: boolean;
  createdBy?: string | null;
  secretHint?: string;
  secret?: string;
  deliveries?: WebhookDelivery[];
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface WebhookListResult {
  rows: WebhookRow[];
  total: number;
}

export function isDeliveryReplayable(d: WebhookDelivery): boolean {
  if (typeof d.replayable === 'boolean') return d.replayable;
  const st = d.status || (d.success ? 'success' : 'pending_retry');
  return st === 'pending_retry' || st === 'dead';
}

export function fetchWebhooks() {
  return request<WebhookListResult>({ url: '/api/webhooks', method: 'get' });
}

export function fetchCreateWebhook(body: {
  url: string;
  events: string[];
  name?: string;
  enabled?: boolean;
}) {
  return request<WebhookRow>({ url: '/api/webhooks', method: 'post', data: body });
}

export function fetchWebhook(id: string) {
  return request<WebhookRow>({ url: `/api/webhooks/${id}`, method: 'get' });
}

export function fetchUpdateWebhook(
  id: string,
  body: Partial<{
    url: string;
    events: string[];
    name: string | null;
    setName: boolean;
    enabled: boolean;
  }>
) {
  return request<WebhookRow>({ url: `/api/webhooks/${id}`, method: 'patch', data: body });
}

export function fetchDeleteWebhook(id: string) {
  return request<{ id: string }>({ url: `/api/webhooks/${id}`, method: 'delete' });
}

export function fetchTestWebhook(id: string) {
  return request<{
    success: boolean;
    statusCode?: number | null;
    attempt?: number;
    error?: string | null;
  }>({ url: `/api/webhooks/${id}/test`, method: 'post' });
}

export function fetchRetryWebhookDelivery(webhookId: string, deliveryLogId: string) {
  return request<{
    success: boolean;
    statusCode?: number | null;
    attempt?: number;
    error?: string | null;
    status?: string;
  }>({
    url: `/api/webhooks/${webhookId}/deliveries/${deliveryLogId}/retry`,
    method: 'post'
  });
}

/** Parse comma / whitespace separated events; dedupe; validate against known set. */
export function parseWebhookEvents(input: string, allowed: readonly string[] = WEBHOOK_EVENTS): string[] {
  const parts = (input || '')
    .split(/[,\s]+/)
    .map(s => s.trim())
    .filter(Boolean);
  const out: string[] = [];
  const allow = new Set(allowed);
  for (const p of parts) {
    if (!allow.has(p)) {
      throw new Error(`未知事件: ${p}`);
    }
    if (!out.includes(p)) out.push(p);
  }
  return out;
}


/** E54 stats windows */
export const STAT_WINDOWS = ['24h', '7d', '30d'] as const;
export const DEFAULT_STAT_WINDOW = '7d' as const;
export type StatWindow = (typeof STAT_WINDOWS)[number];

export interface DeliveryTotals {
  success: number;
  pending_retry: number;
  dead: number;
  attempts: number;
  successRate: number | null;
  latencyMs?: { p50: number; p95: number };
}

export interface WebhookStatsBreakdown {
  webhookId: string;
  name?: string | null;
  url?: string | null;
  totals: DeliveryTotals;
}

export interface WebhookStatsPayload {
  window: StatWindow;
  totals: DeliveryTotals;
  byWebhook?: WebhookStatsBreakdown[];
  webhookId?: string;
  name?: string | null;
  url?: string | null;
}

export interface DeadLetterRow extends WebhookDelivery {
  webhookName?: string | null;
  webhookUrl?: string | null;
}

export interface DeadLetterListResult {
  rows: DeadLetterRow[];
  nextCursor?: string | null;
  total?: number;
}

export interface BulkRetryResult {
  results: Array<{
    deliveryLogId: string;
    ok: boolean;
    error?: string;
    result?: Record<string, unknown>;
  }>;
  succeeded: number;
  failed: number;
}

function _num(v: unknown, fallback = 0): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

export function normalizeStatsPayload(raw: unknown): WebhookStatsPayload {
  const r = (raw || {}) as Record<string, unknown>;
  const windowRaw = String(r.window || DEFAULT_STAT_WINDOW);
  const window = (STAT_WINDOWS as readonly string[]).includes(windowRaw)
    ? (windowRaw as StatWindow)
    : DEFAULT_STAT_WINDOW;
  const t = (r.totals || {}) as Record<string, unknown>;
  const totals: DeliveryTotals = {
    success: _num(t.success),
    pending_retry: _num(t.pending_retry ?? t.pendingRetry),
    dead: _num(t.dead),
    attempts: _num(t.attempts),
    successRate:
      t.successRate === null || t.successRate === undefined
        ? null
        : _num(t.successRate, 0)
  };
  const lat = t.latencyMs as { p50?: unknown; p95?: unknown } | undefined;
  if (lat && lat.p50 != null && lat.p95 != null) {
    totals.latencyMs = { p50: _num(lat.p50), p95: _num(lat.p95) };
  }
  const out: WebhookStatsPayload = { window, totals };
  if (Array.isArray(r.byWebhook)) {
    out.byWebhook = (r.byWebhook as Record<string, unknown>[]).map(b => {
      const bt = (b.totals || {}) as Record<string, unknown>;
      const btTotals: DeliveryTotals = {
        success: _num(bt.success),
        pending_retry: _num(bt.pending_retry ?? bt.pendingRetry),
        dead: _num(bt.dead),
        attempts: _num(bt.attempts),
        successRate:
          bt.successRate === null || bt.successRate === undefined
            ? null
            : _num(bt.successRate, 0)
      };
      return {
        webhookId: String(b.webhookId || ''),
        name: (b.name as string | null | undefined) ?? null,
        url: (b.url as string | null | undefined) ?? null,
        totals: btTotals
      };
    });
  }
  if (r.webhookId) out.webhookId = String(r.webhookId);
  if ('name' in r) out.name = (r.name as string | null | undefined) ?? null;
  if ('url' in r) out.url = (r.url as string | null | undefined) ?? null;
  return out;
}

export function filterDeadLetterRows<T extends { webhookId: string; eventType: string }>(
  rows: T[],
  webhookId: string | 'all',
  eventType: string | 'all'
): T[] {
  let list = rows;
  if (webhookId && webhookId !== 'all') {
    list = list.filter(r => r.webhookId === webhookId);
  }
  if (eventType && eventType !== 'all') {
    list = list.filter(r => r.eventType === eventType);
  }
  return list;
}

export function formatSuccessRate(rate: number | null | undefined): string {
  if (rate === null || rate === undefined || Number.isNaN(rate)) return '—';
  return `${(rate * 100).toFixed(1)}%`;
}

export function fetchWebhookStats(window: string = DEFAULT_STAT_WINDOW) {
  return request<WebhookStatsPayload>({
    url: '/api/webhooks/stats',
    method: 'get',
    params: { window }
  });
}

export function fetchWebhookStatsById(id: string, window: string = DEFAULT_STAT_WINDOW) {
  return request<WebhookStatsPayload>({
    url: `/api/webhooks/${id}/stats`,
    method: 'get',
    params: { window }
  });
}

export function fetchDeadLetter(params?: {
  limit?: number;
  cursor?: string;
  webhook_id?: string;
  event?: string;
}) {
  return request<DeadLetterListResult>({
    url: '/api/webhooks/dead-letter',
    method: 'get',
    params: params || {}
  });
}

export function fetchBulkRetryDeadLetter(deliveryLogIds: string[]) {
  return request<BulkRetryResult>({
    url: '/api/webhooks/dead-letter/retry',
    method: 'post',
    data: { deliveryLogIds }
  });
}
