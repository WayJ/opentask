/** E47/E52：WS Activity Feed helpers（纯函数，便于 vitest） */
import { formatTimelineAction } from './formatTimelineAction';

export type ActivityReactionChip = {
  emoji: string;
  count: number;
  myReacted: boolean;
};

export type ActivityReactions = {
  scope: 'issue' | 'comment';
  commentId?: string | null;
  summary: ActivityReactionChip[];
};

export type ActivityItem = {
  id: string;
  issueId: string;
  issueCode?: string | null;
  issueTitle?: string | null;
  actionType: string;
  actor?: { id: string; username?: string | null; displayName?: string | null } | null;
  createdAt?: string | null;
  payload?: Record<string, unknown> | null;
  reactions?: ActivityReactions | null;
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
  { value: 'created', label: '创建' },
  { value: 'sla_paused', label: 'SLA 暂停' },
  { value: 'sla_resumed', label: 'SLA 恢复' }
];

export const ACTIVITY_QUICK_EMOJIS = ['👍', '🎉', '❤️', '👀'] as const;

export type ActivityQueryInput = {
  sincePreset?: '24h' | '7d' | null;
  since?: string | null;
  until?: string | null;
  actionTypes?: string[];
  actorId?: string | null;
  issueId?: string | null;
  watching?: boolean | null;
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
  if (input.watching === true) out.watching = 'true';
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

/** Q4a empty copy: distinguish no activity vs no watches */
export function emptyActivityDescription(watching: boolean): string {
  return watching ? '你还没有关注任何 Issue，或关注的 Issue 暂无动态' : '暂无活动';
}

/** Bell badge: '' | '1'..'99' | '99+' */
export function formatUnreadBadge(count: number, capped = false): string {
  const n = Math.max(0, Math.floor(Number(count) || 0));
  if (n <= 0) return '';
  if (capped || n > 99) return '99+';
  return String(n);
}

/** Optimistic toggle of a chip in reactions summary */
export function toggleReactionSummary(
  reactions: ActivityReactions | null | undefined,
  emoji: string,
  myReactedNext: boolean
): ActivityReactions {
  const base: ActivityReactions = reactions
    ? { scope: reactions.scope, commentId: reactions.commentId, summary: [...(reactions.summary || [])] }
    : { scope: 'issue', summary: [] };
  const idx = base.summary.findIndex(s => s.emoji === emoji);
  if (idx >= 0) {
    const cur = base.summary[idx];
    const count = Math.max(0, cur.count + (myReactedNext ? 1 : -1));
    if (count === 0) {
      base.summary = base.summary.filter((_, i) => i !== idx);
    } else {
      base.summary[idx] = { ...cur, count, myReacted: myReactedNext };
    }
  } else if (myReactedNext) {
    base.summary = [...base.summary, { emoji, count: 1, myReacted: true }];
  }
  return base;
}
