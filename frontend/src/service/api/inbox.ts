import { request } from '../request';

export interface InboxNotification {
  id: string;
  workspaceId: string;
  recipientUserId: string;
  actorUserId?: string | null;
  type: 'assigned' | 'commented' | 'mentioned' | string;
  resourceType: string;
  resourceId: string;
  title: string;
  body?: string | null;
  readAt?: string | null;
  snoozedUntil?: string | null;
  createdAt: string;
}

export interface InboxListResult {
  rows: InboxNotification[];
  total: number;
  page: number;
  pageSize: number;
  unreadCount: number;
}

export function fetchInboxList(params?: {
  unreadOnly?: boolean;
  includeSnoozed?: boolean;
  page?: number;
  pageSize?: number;
}) {
  return request<InboxListResult>({
    url: '/api/inbox',
    method: 'get',
    params: {
      unread_only: params?.unreadOnly ?? false,
      include_snoozed: params?.includeSnoozed ?? false,
      page: params?.page ?? 1,
      page_size: params?.pageSize ?? 20
    }
  });
}

export function fetchMarkInboxRead(id: string) {
  return request<InboxNotification>({
    url: `/api/inbox/${id}/read`,
    method: 'post'
  });
}

export function fetchMarkAllInboxRead() {
  return request<{ updated: number }>({
    url: '/api/inbox/read-all',
    method: 'post'
  });
}

export function fetchSnoozeInbox(id: string, until: string) {
  return request<InboxNotification>({
    url: `/api/inbox/${id}/snooze`,
    method: 'post',
    data: { until }
  });
}

export function fetchUnsnoozeInbox(id: string) {
  return request<InboxNotification>({
    url: `/api/inbox/${id}/unsnooze`,
    method: 'post'
  });
}
