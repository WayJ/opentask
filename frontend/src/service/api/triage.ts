import { request } from '../request';

export interface TriageIssue {
  id: string;
  issueCode: string;
  title: string;
  description?: string | null;
  status: string;
  type: string;
  priority: string;
  triageStatus: string | null;
  workspaceId: string;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface TriageListResult {
  rows: TriageIssue[];
  total: number;
}

export function fetchTriageList(params?: { page?: number; pageSize?: number }) {
  return request<TriageListResult>({
    url: '/api/triage',
    method: 'get',
    params: {
      page: params?.page ?? 1,
      page_size: params?.pageSize ?? 50
    }
  });
}

export function fetchTriageEnqueue(body: {
  issueId?: string;
  title?: string;
  type?: string;
  priority?: string;
  description?: string;
}) {
  return request<TriageIssue>({
    url: '/api/triage',
    method: 'post',
    data: body
  });
}

export function fetchTriageAccept(issueId: string) {
  return request<TriageIssue>({
    url: `/api/triage/${issueId}/accept`,
    method: 'post'
  });
}

export function fetchTriageDecline(issueId: string) {
  return request<TriageIssue>({
    url: `/api/triage/${issueId}/decline`,
    method: 'post'
  });
}

export function fetchTriageDuplicate(issueId: string, duplicateOfIssueId: string) {
  return request<TriageIssue>({
    url: `/api/triage/${issueId}/duplicate`,
    method: 'post',
    data: { duplicateOfIssueId }
  });
}
