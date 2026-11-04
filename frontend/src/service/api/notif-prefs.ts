import { request } from '../request';

export const NOTIF_PREF_KEYS = [
  'issue_assigned',
  'issue_comment',
  'issue_mention',
  'issue_status',
  'due_date_changed',
  'issue_watch_event',
  'automation_comment'
] as const;

export type NotifPrefKey = (typeof NOTIF_PREF_KEYS)[number];

export interface NotifPrefs {
  userId: string;
  workspaceId: string;
  issue_assigned: boolean;
  issue_comment: boolean;
  issue_mention: boolean;
  issue_status: boolean;
  due_date_changed: boolean;
  issue_watch_event: boolean;
  automation_comment: boolean;
}

export const NOTIF_PREF_LABELS: Record<NotifPrefKey, string> = {
  issue_assigned: '被指派 Issue',
  issue_comment: 'Issue 新评论',
  issue_mention: '@提及',
  issue_status: '状态变更（关注）',
  due_date_changed: '截止日期变更',
  issue_watch_event: '关注更新',
  automation_comment: '自动化评论'
};

export function fetchNotifPrefs() {
  return request<NotifPrefs>({ url: '/api/inbox/preferences', method: 'get' });
}

export function updateNotifPrefs(body: Partial<Record<NotifPrefKey, boolean>>) {
  return request<NotifPrefs>({ url: '/api/inbox/preferences', method: 'put', data: body });
}

/** Helper for vitest / UI: merge partial into defaults (all true). */
export function mergeNotifPrefs(
  partial?: Partial<Record<NotifPrefKey, boolean>> | null
): Record<NotifPrefKey, boolean> {
  const base = Object.fromEntries(NOTIF_PREF_KEYS.map(k => [k, true])) as Record<NotifPrefKey, boolean>;
  if (!partial) return base;
  for (const k of NOTIF_PREF_KEYS) {
    if (typeof partial[k] === 'boolean') base[k] = partial[k] as boolean;
  }
  return base;
}
