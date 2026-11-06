import { browserServiceUrl } from '@/utils/attachmentUrls';
import { request } from '../request';

export type CustomerRequestStatus = 'open' | 'completed' | 'canceled';
export type CustomerRequestPriority = 'low' | 'medium' | 'high' | 'urgent';

export interface CustomerRequestIssueRef {
  id: string;
  issueCode: string;
  title: string;
  status: string;
}

export interface CustomerRequestStatusLink {
  enabled: boolean;
  url?: string | null;
  publicRepliesEnabled: boolean;
}

export interface CustomerRequestPublicReplyRow {
  id?: string;
  body: string;
  createdAt?: string | null;
}

export interface CustomerRequestRow {
  id: string;
  workspaceId: string;
  customerId: string;
  customerName?: string | null;
  title: string;
  body?: string | null;
  status: CustomerRequestStatus;
  priority?: CustomerRequestPriority | null;
  issueIds: string[];
  issueCount: number;
  issues?: CustomerRequestIssueRef[];
  createdBy?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
  statusLink?: CustomerRequestStatusLink;
  publicReplies?: CustomerRequestPublicReplyRow[];
  token?: string;
}

export interface PublicRequestStatusCard {
  title: string;
  status: string;
  priority?: string | null;
  updatedAt?: string | null;
  customerName?: string | null;
  linkedIssueCount: number;
  linkedIssueCodes: string[];
  publicRepliesEnabled: boolean;
  recentPublicReplies?: CustomerRequestPublicReplyRow[];
}

export interface CustomerRequestListResult {
  rows: CustomerRequestRow[];
  total: number;
}

export function fetchCustomerRequests(params?: {
  customerId?: string;
  status?: CustomerRequestStatus;
  issueId?: string;
}) {
  return request<CustomerRequestListResult>({
    url: '/api/customer-requests',
    method: 'get',
    params
  });
}

export function fetchCustomerRequest(id: string) {
  return request<CustomerRequestRow>({ url: `/api/customer-requests/${id}`, method: 'get' });
}

export function fetchCreateCustomerRequest(body: {
  customerId: string;
  title: string;
  body?: string;
  status?: CustomerRequestStatus;
  priority?: CustomerRequestPriority | null;
  issueIds?: string[];
  createAndLinkIssue?: boolean;
  projectId?: string | null;
}) {
  return request<CustomerRequestRow>({ url: '/api/customer-requests', method: 'post', data: body });
}

export function fetchUpdateCustomerRequest(
  id: string,
  body: {
    title?: string;
    body?: string;
    clearBody?: boolean;
    status?: CustomerRequestStatus;
    priority?: CustomerRequestPriority | null;
    clearPriority?: boolean;
    customerId?: string;
    publicRepliesEnabled?: boolean;
  }
) {
  return request<CustomerRequestRow>({ url: `/api/customer-requests/${id}`, method: 'patch', data: body });
}

export function fetchDeleteCustomerRequest(id: string) {
  return request<{ id: string }>({ url: `/api/customer-requests/${id}`, method: 'delete' });
}

export function fetchLinkRequestIssue(requestId: string, issueId: string) {
  return request<CustomerRequestRow>({
    url: `/api/customer-requests/${requestId}/issues`,
    method: 'post',
    data: { issueId }
  });
}

export function fetchUnlinkRequestIssue(requestId: string, issueId: string) {
  return request<CustomerRequestRow>({
    url: `/api/customer-requests/${requestId}/issues/${issueId}`,
    method: 'delete'
  });
}

export function fetchEnableRequestStatusLink(id: string, body?: { publicRepliesEnabled?: boolean }) {
  return request<CustomerRequestRow>({
    url: `/api/customer-requests/${id}/status-link/enable`,
    method: 'post',
    data: body || {}
  });
}

export function fetchRotateRequestStatusLink(id: string) {
  return request<CustomerRequestRow>({
    url: `/api/customer-requests/${id}/status-link/rotate`,
    method: 'post'
  });
}

export function fetchRevokeRequestStatusLink(id: string) {
  return request<CustomerRequestRow>({
    url: `/api/customer-requests/${id}/status-link/revoke`,
    method: 'post'
  });
}

export function buildPublicStatusPath(tokenOrUrl: string): string {
  const t = String(tokenOrUrl || '').trim();
  if (!t) return '';
  if (t.startsWith('/r/')) return t;
  if (t.startsWith('http')) {
    try {
      const u = new URL(t);
      return u.pathname.startsWith('/r/') ? u.pathname : `/r/${t}`;
    } catch {
      return `/r/${t}`;
    }
  }
  return `/r/${t}`;
}

export function isPublicStatusCardRedacted(card: Record<string, unknown>): boolean {
  const forbidden = ['workspaceId', 'body', 'token', 'id', 'createdBy', 'issues', 'issueIds'];
  return forbidden.every(k => !(k in card));
}

/** Public (no auth). */
export async function fetchPublicRequestStatus(token: string): Promise<PublicRequestStatusCard> {
  const resp = await fetch(
    browserServiceUrl(
      `/api/public/customer-requests/${encodeURIComponent(token)}`,
      import.meta.env.VITE_SERVICE_BASE_URL
    )
  );
  const json = await resp.json();
  if (!resp.ok) {
    throw new Error(json?.detail || json?.message || '状态页不可用');
  }
  return (json.data || json) as PublicRequestStatusCard;
}

export async function submitPublicRequestReply(
  token: string,
  body: string
): Promise<{ ok: boolean; landedAs?: string }> {
  const resp = await fetch(
    browserServiceUrl(
      `/api/public/customer-requests/${encodeURIComponent(token)}/replies`,
      import.meta.env.VITE_SERVICE_BASE_URL
    ),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ body })
    }
  );
  const json = await resp.json();
  if (!resp.ok) {
    throw new Error(json?.detail || json?.message || '提交失败');
  }
  return (json.data || json) as { ok: boolean; landedAs?: string };
}
