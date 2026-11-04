import { request } from '../request';

export const NOTIF_PREF_KEYS = [
  'issue_assigned',
  'issue_comment',
  'issue_mention',
  'issue_status',
  'due_date_changed',
  'issue_watch_event',
  'automation_comment',
  'due_reminder',
  'sla_breached'
] as const;

export type NotifPrefKey = (typeof NOTIF_PREF_KEYS)[number];

/** Keys rendered in the generic type list (due_reminder has its own card). */
export const NOTIF_PREF_LIST_KEYS = NOTIF_PREF_KEYS.filter(k => k !== 'due_reminder');

/** E30 channel toggle / E39 digest mode (not TYPE gates). */
export type NotifChannelKey = 'email_enabled' | 'due_reminder_digest' | 'insights_digest';

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
  due_reminder: boolean;
  sla_breached: boolean;
  webhook_delivery_alert: boolean;
  due_reminder_digest: boolean;
  insights_digest: boolean;
  email_enabled: boolean;
  email_configured: boolean;
}

export const NOTIF_PREF_LABELS: Record<NotifPrefKey, string> = {
  issue_assigned: '被指派 Issue',
  issue_comment: 'Issue 新评论',
  issue_mention: '@提及',
  issue_status: '状态变更（关注）',
  due_date_changed: '截止日期变更',
  issue_watch_event: '关注更新',
  automation_comment: '自动化评论',
  due_reminder: '到期提醒',
  sla_breached: 'SLA 违约',
  webhook_delivery_alert: 'Webhook 死信告警'
};

export function fetchNotifPrefs() {
  return request<NotifPrefs>({ url: '/api/inbox/preferences', method: 'get' });
}

export function updateNotifPrefs(
  body: Partial<Record<NotifPrefKey | NotifChannelKey, boolean>>
) {
  return request<NotifPrefs>({ url: '/api/inbox/preferences', method: 'put', data: body });
}

export function sendNotifEmailTest() {
  return request<{ sent: boolean; to: string }>({
    url: '/api/inbox/email-test',
    method: 'post'
  });
}

/** Helper for vitest / UI: merge partial into defaults. */
export function mergeNotifPrefs(
  partial?: Partial<Record<NotifPrefKey | NotifChannelKey, boolean>> | null
): Record<NotifPrefKey, boolean> & {
  email_enabled: boolean;
  due_reminder_digest: boolean;
  insights_digest: boolean;
} {
  const base = Object.fromEntries(NOTIF_PREF_KEYS.map(k => [k, true])) as Record<
    NotifPrefKey,
    boolean
  > & { email_enabled: boolean; due_reminder_digest: boolean; insights_digest: boolean };
  base.email_enabled = false;
  base.due_reminder_digest = false;
  base.insights_digest = false;
  if (!partial) return base;
  for (const k of NOTIF_PREF_KEYS) {
    if (typeof partial[k] === 'boolean') base[k] = partial[k] as boolean;
  }
  if (typeof partial.email_enabled === 'boolean') {
    base.email_enabled = partial.email_enabled;
  }
  if (typeof partial.due_reminder_digest === 'boolean') {
    base.due_reminder_digest = partial.due_reminder_digest;
  }
  if (typeof partial.insights_digest === 'boolean') {
    base.insights_digest = partial.insights_digest;
  }
  return base;
}

export function isEmailToggleDisabled(prefs: Pick<NotifPrefs, 'email_configured'> | null | undefined) {
  return !prefs?.email_configured;
}

/** Digest mode requires due_reminder on. */
export function isDigestToggleDisabled(
  prefs: Pick<NotifPrefs, 'due_reminder'> | null | undefined
) {
  return !prefs?.due_reminder;
}
