import { request } from '../request';

export interface IssueBranchName {
  branchName: string;
  issueCode: string;
  slug: string;
  issueId: string;
}

export interface IssueVcsLink {
  id: string;
  workspaceId: string;
  issueId: string;
  kind: 'branch' | 'pull_request';
  branchName?: string | null;
  prUrl?: string | null;
  provider: string;
  externalId?: string | null;
  status: string;
  title?: string | null;
}

export function fetchIssueBranchName(issueId: string) {
  return request<IssueBranchName>({
    url: `/api/issues/${issueId}/vcs/branch-name`,
    method: 'get'
  });
}

export function fetchIssueVcsLinks(issueId: string) {
  return request<{ rows: IssueVcsLink[]; total: number }>({
    url: `/api/issues/${issueId}/vcs/links`,
    method: 'get'
  });
}

export function createIssueVcsLink(
  issueId: string,
  data: {
    kind: 'branch' | 'pull_request';
    branchName?: string;
    prUrl?: string;
    provider?: string;
    externalId?: string;
    status?: string;
    title?: string;
  }
) {
  return request<IssueVcsLink>({
    url: `/api/issues/${issueId}/vcs/links`,
    method: 'post',
    data
  });
}

export function deleteIssueVcsLink(issueId: string, linkId: string) {
  return request<{ id: string }>({
    url: `/api/issues/${issueId}/vcs/links/${linkId}`,
    method: 'delete'
  });
}
