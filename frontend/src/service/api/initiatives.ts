import { request } from '../request';

export type InitiativeStatus = 'planned' | 'active' | 'completed' | 'canceled';

export type InitiativeRelationType = 'blocks' | 'is_blocked_by' | 'relates_to';
export type InitiativeRelationDirection = 'outgoing' | 'incoming';

export interface InitiativeHealthSummary {
  overall: 'on_track' | 'at_risk' | 'off_track' | null;
  counts: { onTrack: number; atRisk: number; offTrack: number; unknown: number };
  projectCount: number;
}

export interface InitiativeProjectRef {
  id: string;
  name: string | null;
  healthStatus: 'on_track' | 'at_risk' | 'off_track' | null;
}

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
  healthSummary?: InitiativeHealthSummary;
  projects?: InitiativeProjectRef[];
  blocksCount?: number;
  blockedByCount?: number;
  relatesToCount?: number;
  createdBy?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface InitiativeListResult {
  rows: InitiativeRow[];
  total: number;
}

export interface InitiativeRelationItem {
  id: string;
  type: InitiativeRelationType;
  direction: InitiativeRelationDirection;
  initiative: { id: string; name: string; status: string };
}

export interface InitiativeRelationsResult {
  items: InitiativeRelationItem[];
}

export function fetchInitiatives(params?: { include?: string }) {
  return request<InitiativeListResult>({
    url: '/api/initiatives',
    method: 'get',
    params
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

export function fetchInitiativeRelations(id: string) {
  return request<InitiativeRelationsResult>({
    url: `/api/initiatives/${id}/relations`,
    method: 'get'
  });
}

export function fetchAddInitiativeRelation(
  id: string,
  body: { targetInitiativeId: string; type: InitiativeRelationType }
) {
  return request<InitiativeRelationItem>({
    url: `/api/initiatives/${id}/relations`,
    method: 'post',
    data: body
  });
}

export function fetchRemoveInitiativeRelation(id: string, relationId: string) {
  return request<{ id: string }>({
    url: `/api/initiatives/${id}/relations/${relationId}`,
    method: 'delete'
  });
}
