import { request } from '../request';

export const ISSUE_STATUSES = [
  'open',
  'in_progress',
  'feedback',
  'resolved',
  'closed',
  'rejected'
] as const;

export type SlaClockStatus = 'running' | 'paused' | 'met' | 'breached' | 'cancelled';

export interface SlaPolicyRow {
  id: string;
  workspaceId: string;
  name: string;
  enabled: boolean;
  metric: string;
  startStatuses: string[];
  stopStatuses: string[];
  pauseStatuses: string[];
  targetMinutes: number;
  notifyAssignee: boolean;
  notifyWatchers: boolean;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface SlaClockRow {
  id: string;
  workspaceId: string;
  issueId: string;
  policyId: string;
  policyName?: string | null;
  status: SlaClockStatus | string;
  startedAt?: string | null;
  deadlineAt?: string | null;
  stoppedAt?: string | null;
  breachedAt?: string | null;
  startStatus: string;
  elapsedBeforePauseMinutes?: number;
  pausedAt?: string | null;
  segmentStartedAt?: string | null;
}

/** Format remaining/overdue wall-clock minutes for SLA badges. */
export function formatSlaRemaining(deadlineAt?: string | null, nowMs: number = Date.now()): string {
  if (!deadlineAt) return '—';
  const raw = deadlineAt.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(deadlineAt) ? deadlineAt : `${deadlineAt}Z`;
  const t = new Date(raw).getTime();
  if (Number.isNaN(t)) return '—';
  const diffMin = Math.round((t - nowMs) / 60000);
  if (diffMin >= 0) {
    if (diffMin < 60) return `剩余 ${diffMin} 分钟`;
    const h = Math.floor(diffMin / 60);
    const m = diffMin % 60;
    return m ? `剩余 ${h}h ${m}m` : `剩余 ${h}h`;
  }
  const overdue = Math.abs(diffMin);
  if (overdue < 60) return `逾期 ${overdue} 分钟`;
  const h = Math.floor(overdue / 60);
  const m = overdue % 60;
  return m ? `逾期 ${h}h ${m}m` : `逾期 ${h}h`;
}

export function slaBadgeType(status: string): 'default' | 'info' | 'success' | 'error' | 'warning' {
  if (status === 'breached') return 'error';
  if (status === 'met') return 'success';
  if (status === 'running') return 'warning';
  if (status === 'paused') return 'warning';
  return 'default';
}

/** Paused badge copy: 已暂停 · 已用 X / 目标 Y */
export function formatSlaPaused(
  elapsedBeforePauseMinutes?: number | null,
  targetMinutes?: number | null
): string {
  const used = Math.max(0, Math.floor(Number(elapsedBeforePauseMinutes) || 0));
  const target = targetMinutes == null ? null : Math.max(0, Math.floor(Number(targetMinutes) || 0));
  if (target == null) return `已暂停 · 已用 ${used}`;
  return `已暂停 · 已用 ${used} / 目标 ${target}`;
}

export function fetchSlaPolicies() {
  return request<{ rows: SlaPolicyRow[]; total: number }>({ url: '/api/sla/policies', method: 'get' });
}

export function fetchCreateSlaPolicy(body: {
  name: string;
  startStatuses: string[];
  stopStatuses?: string[];
  pauseStatuses?: string[];
  targetMinutes?: number;
  notifyAssignee?: boolean;
  notifyWatchers?: boolean;
  enabled?: boolean;
}) {
  return request<SlaPolicyRow>({ url: '/api/sla/policies', method: 'post', data: body });
}

export function fetchUpdateSlaPolicy(
  id: string,
  body: Partial<{
    name: string;
    startStatuses: string[];
    stopStatuses: string[];
    pauseStatuses: string[];
    targetMinutes: number;
    notifyAssignee: boolean;
    notifyWatchers: boolean;
    enabled: boolean;
  }>
) {
  return request<SlaPolicyRow>({ url: `/api/sla/policies/${id}`, method: 'patch', data: body });
}

export function fetchDeleteSlaPolicy(id: string) {
  return request({ url: `/api/sla/policies/${id}`, method: 'delete' });
}

export function fetchIssueSla(issueId: string) {
  return request<{ rows: SlaClockRow[]; total: number }>({
    url: `/api/issues/${issueId}/sla`,
    method: 'get'
  });
}

export function fetchSlaRunDue() {
  return request<{
    scanned: number;
    breached: number;
    notificationsCreated: number;
    skipped: number;
    errors: Array<{ clockId: string; message: string }>;
  }>({ url: '/api/sla/run-due', method: 'post' });
}
