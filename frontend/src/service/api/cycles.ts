import { request } from '../request';

export type CycleStatus = 'upcoming' | 'active' | 'completed';

export interface CycleItem {
  id: string;
  workspaceId: string;
  name: string;
  number?: number | null;
  status: CycleStatus;
  startsAt: string;
  endsAt: string;
  completedAt?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CycleListResult {
  rows: CycleItem[];
  total: number;
}

export function fetchCycles(params?: { status?: CycleStatus }) {
  return request<CycleListResult>({
    url: '/api/cycles',
    method: 'get',
    params
  });
}

export function fetchCycle(id: string) {
  return request<CycleItem>({
    url: `/api/cycles/${id}`,
    method: 'get'
  });
}

export function fetchCreateCycle(body: { name?: string; starts_at: string; ends_at: string }) {
  return request<CycleItem>({
    url: '/api/cycles',
    method: 'post',
    data: body
  });
}

export function fetchUpdateCycle(id: string, body: { name?: string; starts_at?: string; ends_at?: string }) {
  return request<CycleItem>({
    url: `/api/cycles/${id}`,
    method: 'patch',
    data: body
  });
}

export function fetchDeleteCycle(id: string) {
  return request<{ id: string }>({
    url: `/api/cycles/${id}`,
    method: 'delete'
  });
}

export function fetchActivateCycle(id: string) {
  return request<CycleItem>({
    url: `/api/cycles/${id}/activate`,
    method: 'post'
  });
}
