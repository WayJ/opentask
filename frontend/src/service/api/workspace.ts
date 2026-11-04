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

export interface WorkspaceMemberItem {
  id: string;
  userId: string;
  role: string;
  createdAt: string;
}

export interface WorkspaceInviteItem {
  id: string;
  workspaceId: string;
  email?: string | null;
  role: string;
  status: string;
  expiresAt: string;
  invitedBy: string;
  acceptedBy?: string | null;
  acceptedAt?: string | null;
  createdAt: string;
  token?: string;
  workspaceName?: string;
}

export function fetchWorkspaceMembers(workspaceId: string) {
  return request<WorkspaceMemberItem[]>({
    url: `/api/workspaces/${workspaceId}/members`,
    method: 'get'
  });
}

export function fetchAddWorkspaceMember(
  workspaceId: string,
  data: { userId: string; role?: string }
) {
  return request<WorkspaceMemberItem>({
    url: `/api/workspaces/${workspaceId}/members`,
    method: 'post',
    data
  });
}

export function fetchUpdateWorkspaceMemberRole(
  workspaceId: string,
  userId: string,
  role: string
) {
  return request<WorkspaceMemberItem>({
    url: `/api/workspaces/${workspaceId}/members/${userId}`,
    method: 'patch',
    data: { role }
  });
}

export function fetchRemoveWorkspaceMember(workspaceId: string, userId: string) {
  return request({
    url: `/api/workspaces/${workspaceId}/members/${userId}`,
    method: 'delete'
  });
}

export function fetchLeaveWorkspace(workspaceId: string) {
  return request({
    url: `/api/workspaces/${workspaceId}/leave`,
    method: 'post'
  });
}

export function fetchCreateWorkspaceInvite(
  workspaceId: string,
  data: { email?: string; role?: string; expiresInDays?: number }
) {
  return request<WorkspaceInviteItem>({
    url: `/api/workspaces/${workspaceId}/invites`,
    method: 'post',
    data
  });
}

export function fetchWorkspaceInvites(workspaceId: string) {
  return request<WorkspaceInviteItem[]>({
    url: `/api/workspaces/${workspaceId}/invites`,
    method: 'get'
  });
}

export function fetchRevokeWorkspaceInvite(workspaceId: string, inviteId: string) {
  return request({
    url: `/api/workspaces/${workspaceId}/invites/${inviteId}`,
    method: 'delete'
  });
}

export function fetchPreviewInvite(token: string) {
  return request<WorkspaceInviteItem>({
    url: `/api/invites/${encodeURIComponent(token)}`,
    method: 'get'
  });
}

export function fetchAcceptInvite(token: string) {
  return request<{ workspaceId: string; userId: string; role: string; alreadyMember?: boolean }>({
    url: `/api/invites/${encodeURIComponent(token)}/accept`,
    method: 'post'
  });
}
