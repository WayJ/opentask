import { request } from '../request';

export type CustomerRequestStatus = 'open' | 'completed' | 'canceled';
export type CustomerRequestPriority = 'low' | 'medium' | 'high' | 'urgent';

export interface CustomerRequestIssueRef {
  id: string;
  issueCode: string;
  title: string;
  status: string;
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
