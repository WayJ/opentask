import { request } from '../request';

export type CycleRolloverPolicy = 'into_next' | 'leave_unassigned';

export interface WorkspaceItem {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  role?: string | null;
  cyclesEnabled?: boolean;
  cycleDurationDays?: number;
  cycleRolloverPolicy?: CycleRolloverPolicy | string;
  cycleCapacityLookback?: number;
  issueKey?: string;
  createdAt: string;
  updatedAt: string;
}

export function fetchWorkspaceList() {
  return request<WorkspaceItem[]>({ url: '/api/workspaces', method: 'get' });
}

export function fetchWorkspace(id: string) {
  return request<WorkspaceItem>({ url: `/api/workspaces/${id}`, method: 'get' });
}

export function fetchCreateWorkspace(data: { name: string; slug?: string; description?: string }) {
  return request<WorkspaceItem>({ url: '/api/workspaces', method: 'post', data });
}

export function fetchUpdateWorkspace(
  id: string,
  data: {
    name?: string;
    description?: string | null;
    cyclesEnabled?: boolean;
    cycleDurationDays?: number;
    cycleRolloverPolicy?: CycleRolloverPolicy;
    cycleCapacityLookback?: number;
    issueKey?: string;
  }
) {
  return request<WorkspaceItem>({ url: `/api/workspaces/${id}`, method: 'patch', data });
}
