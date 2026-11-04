import { request } from '../request';

export const RECURRENCE_INTERVALS = ['daily', 'weekly', 'monthly'] as const;
export type RecurrenceInterval = (typeof RECURRENCE_INTERVALS)[number];

export interface RecurrenceRow {
  id: string;
  workspaceId: string;
  titleTemplate: string;
  description?: string | null;
  priority?: string | null;
  labels: string[];
  projectId?: string | null;
  assigneeId?: string | null;
  customFields: Record<string, unknown>;
  interval: RecurrenceInterval | string;
  weekday?: number | null;
  monthday?: number | null;
  nextRunAt?: string | null;
  enabled: boolean;
  lastIssueId?: string | null;
  createdBy?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface RecurrenceListResult {
  rows: RecurrenceRow[];
  total: number;
}

export interface RunDueResult {
  created: number;
  errors: Array<{ recurrenceId: string; message: string }>;
  issues: Array<{ id: string; issueCode: string; recurrenceId: string; title?: string }>;
}

export function formatNextRun(iso?: string | null): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : `${iso}Z`);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
  } catch {
    return iso;
  }
}

export function fetchRecurrences() {
  return request<RecurrenceListResult>({ url: '/api/recurrences', method: 'get' });
}

export function fetchCreateRecurrence(body: {
  titleTemplate: string;
  interval: string;
  nextRunAt: string;
  description?: string;
  priority?: string;
  labels?: string[];
  projectId?: string;
  assigneeId?: string;
  customFields?: Record<string, unknown>;
  weekday?: number;
  monthday?: number;
  enabled?: boolean;
}) {
  return request<RecurrenceRow>({ url: '/api/recurrences', method: 'post', data: body });
}

export function fetchUpdateRecurrence(
  id: string,
  body: Partial<{
    titleTemplate: string;
    description: string | null;
    clearDescription: boolean;
    priority: string | null;
    setPriority: boolean;
    labels: string[];
    projectId: string | null;
    setProjectId: boolean;
    assigneeId: string | null;
    setAssigneeId: boolean;
    customFields: Record<string, unknown>;
    interval: string;
    weekday: number | null;
    setWeekday: boolean;
    monthday: number | null;
    setMonthday: boolean;
    nextRunAt: string;
    enabled: boolean;
  }>
) {
  return request<RecurrenceRow>({ url: `/api/recurrences/${id}`, method: 'patch', data: body });
}

export function fetchDeleteRecurrence(id: string) {
  return request<{ id: string }>({ url: `/api/recurrences/${id}`, method: 'delete' });
}

export function fetchRunDueRecurrences() {
  return request<RunDueResult>({ url: '/api/recurrences/run-due', method: 'post' });
}
