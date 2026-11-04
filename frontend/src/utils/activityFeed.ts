/** E47：WS Activity Feed helpers（纯函数，便于 vitest） */
import { formatTimelineAction } from './formatTimelineAction';

export type ActivityItem = {
  id: string;
  issueId: string;
  issueCode?: string | null;
  issueTitle?: string | null;
  actionType: string;
  actor?: { id: string; username?: string | null; displayName?: string | null } | null;
  createdAt?: string | null;
  payload?: Record<string, unknown> | null;
};

export const ACTIVITY_ACTION_OPTIONS: { value: string; label: string }[] = [
  { value: 'status_changed', label: '状态变更' },
  { value: 'assigned', label: '分配' },
  { value: 'priority_changed', label: '优先级' },
  { value: 'commented', label: '评论' },
  { value: 'label_added', label: '加标签' },
  { value: 'label_removed', label: '去标签' },
  { value: 'custom_field_changed', label: '自定义字段' },
  { value: 'cycle_changed', label: 'Cycle' },
  { value: 'estimate_changed', label: '估分' },
  { value: 'project_changed', label: '项目' },
  { value: 'created', label: '创建' }
];

export type ActivityQueryInput = {
  sincePreset?: '24h' | '7d' | null;
  since?: string | null;
  until?: string | null;
  actionTypes?: string[];
  actorId?: string | null;
  issueId?: string | null;
  cursor?: string | null;
  limit?: number;
  now?: Date;
};

/** Build query params for GET /api/issues/activity */
export function buildActivityQuery(input: ActivityQueryInput = {}): Record<string, string | string[]> {
  const out: Record<string, string | string[]> = {};
  const now = input.now ?? new Date();
  let since = input.since || null;
  if (!since && input.sincePreset === '24h') {
    since = new Date(now.getTime() - 24 * 3600 * 1000).toISOString();
  } else if (!since && input.sincePreset === '7d') {
    since = new Date(now.getTime() - 7 * 24 * 3600 * 1000).toISOString();
  }
  if (since) out.since = since;
  if (input.until) out.until = input.until;
  if (input.actionTypes && input.actionTypes.length) out.actionType = input.actionTypes;
  if (input.actorId) out.actorId = input.actorId;
  if (input.issueId) out.issueId = input.issueId;
  if (input.cursor) out.cursor = input.cursor;
  if (input.limit != null) out.limit = String(input.limit);
  return out;
}

export function formatActivityRow(item: ActivityItem): string {
  return formatTimelineAction({
    action_type: item.actionType,
    action_data: item.payload || {}
  });
}

export function formatActivityActor(item: ActivityItem): string {
  const a = item.actor;
  if (!a) return '系统';
  return a.displayName || a.username || a.id || '未知';
}
