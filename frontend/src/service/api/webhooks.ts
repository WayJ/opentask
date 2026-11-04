import { request } from '../request';

export const WEBHOOK_EVENTS = [
  'issue.created',
  'issue.updated',
  'issue.status_changed',
  'comment.created',
  'issue.custom_field_changed',
  'issue.sla_breached'
] as const;

export const WEBHOOK_EVENT_LABELS: Record<(typeof WEBHOOK_EVENTS)[number], string> = {
  'issue.created': 'Issue 创建',
  'issue.updated': 'Issue 更新',
  'issue.status_changed': 'Issue 状态变更',
  'comment.created': '评论创建',
  'issue.custom_field_changed': '自定义字段变更',
  'issue.sla_breached': 'SLA 违约'
};

export type WebhookEvent = (typeof WEBHOOK_EVENTS)[number];

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
