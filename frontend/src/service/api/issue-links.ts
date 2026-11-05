import { request } from '../request';

export interface IssueLink {
  id: string;
  workspaceId: string;
  issueId: string;
  url: string;
  title?: string | null;
  position: number;
  createdBy?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export function fetchIssueLinks(issueId: string) {
  return request<{ rows: IssueLink[]; total: number }>({
    url: `/api/issues/${issueId}/links`,
    method: 'get'
  });
}

export function createIssueLink(issueId: string, data: { url: string; title?: string }) {
  return request<IssueLink>({
    url: `/api/issues/${issueId}/links`,
    method: 'post',
    data
  });
}

export function patchIssueLink(
  issueId: string,
  linkId: string,
  data: { url?: string; title?: string; position?: number }
) {
  return request<IssueLink>({
    url: `/api/issues/${issueId}/links/${linkId}`,
    method: 'patch',
    data
  });
}

export function deleteIssueLink(issueId: string, linkId: string) {
  return request<{ id: string }>({
    url: `/api/issues/${issueId}/links/${linkId}`,
    method: 'delete'
  });
}
