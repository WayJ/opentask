/** E17/E60: workspace-scoped global search */
import { request } from '@/service/request';

export interface SearchIssueHit {
  id: string;
  issueCode: string;
  title: string;
  status?: string;
  priority?: string;
  rank?: number;
  snippet?: string;
}

export interface SearchProjectHit {
  id: string;
  name: string;
  description?: string;
  isActive?: boolean;
  rank?: number;
  snippet?: string;
}

export interface SearchDocHit {
  id: string;
  title: string;
  parentType: string;
  parentId: string;
  snippet?: string;
  rank?: number;
}

export interface SearchMemberHit {
  membershipId: string;
  userId: string;
  role: string;
  username?: string | null;
  name?: string | null;
}

export interface GlobalSearchResult {
  issues: SearchIssueHit[];
  projects: SearchProjectHit[];
  docs: SearchDocHit[];
  members: SearchMemberHit[];
}

export function fetchGlobalSearch(q: string, limit = 10) {
  return request<GlobalSearchResult>({
    url: '/api/search',
    method: 'GET',
    params: { q, limit }
  });
}
