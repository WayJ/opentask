import { request } from '../request';

export interface WorkspaceItem {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  role?: string | null;
  createdAt: string;
  updatedAt: string;
}

export function fetchWorkspaceList() {
  return request<WorkspaceItem[]>({ url: '/api/workspaces', method: 'get' });
}

export function fetchCreateWorkspace(data: { name: string; slug?: string; description?: string }) {
  return request<WorkspaceItem>({ url: '/api/workspaces', method: 'post', data });
}
