import { request } from '../request';

export type InitiativeStatus = 'planned' | 'active' | 'completed' | 'canceled';

export interface InitiativeRow {
  id: string;
  workspaceId: string;
  name: string;
  description?: string | null;
  status: InitiativeStatus;
  targetDate?: string | null;
  ownerUserId?: string | null;
  sortOrder: number;
  projectIds: string[];
  createdBy?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface InitiativeListResult {
  rows: InitiativeRow[];
  total: number;
}

export function fetchInitiatives() {
  return request<InitiativeListResult>({
    url: '/api/initiatives',
    method: 'get'
  });
}

export function fetchInitiative(id: string) {
  return request<InitiativeRow>({
    url: `/api/initiatives/${id}`,
    method: 'get'
  });
}

export function fetchCreateInitiative(body: {
  name: string;
  description?: string;
  status?: InitiativeStatus;
  targetDate?: string | null;
  ownerUserId?: string | null;
  sortOrder?: number;
  projectIds?: string[];
}) {
  return request<InitiativeRow>({
    url: '/api/initiatives',
    method: 'post',
    data: body
  });
}

export function fetchUpdateInitiative(
  id: string,
  body: {
    name?: string;
    description?: string;
    status?: InitiativeStatus;
    targetDate?: string | null;
    clearTargetDate?: boolean;
    ownerUserId?: string | null;
    clearOwner?: boolean;
    sortOrder?: number;
    projectIds?: string[];
  }
) {
  return request<InitiativeRow>({
    url: `/api/initiatives/${id}`,
    method: 'patch',
    data: body
  });
}

export function fetchDeleteInitiative(id: string) {
  return request<{ id: string }>({
    url: `/api/initiatives/${id}`,
    method: 'delete'
  });
}

export function fetchSetInitiativeProjects(id: string, projectIds: string[]) {
  return request<InitiativeRow>({
    url: `/api/initiatives/${id}/projects`,
    method: 'put',
    data: { projectIds }
  });
}
