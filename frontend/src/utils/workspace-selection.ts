/** Legacy orphan workspace. Same id the backend hides from list_for_user. */
export const LEGACY_DEFAULT_WORKSPACE_ID = '00000000-0000-4000-8000-000000000001';

export interface WorkspaceRef {
  id: string;
}

export type WorkspaceGate = 'ready' | 'onboarding';

export function usableWorkspaces<T extends WorkspaceRef>(list: T[] | null | undefined): T[] {
  return (list ?? []).filter(item => Boolean(item.id) && item.id !== LEGACY_DEFAULT_WORKSPACE_ID);
}

/**
 * Keep a stored id only when it belongs to this user's usable memberships.
 * Otherwise take the earliest usable workspace. An empty list means onboarding.
 */
export function resolveWorkspaceSelection(
  storedId: string | null | undefined,
  list: WorkspaceRef[] | null | undefined
): { gate: WorkspaceGate; workspaceId: string | null } {
  const usable = usableWorkspaces(list);
  if (!usable.length) {
    return { gate: 'onboarding', workspaceId: null };
  }
  if (storedId && usable.some(item => item.id === storedId)) {
    return { gate: 'ready', workspaceId: storedId };
  }
  return { gate: 'ready', workspaceId: usable[0].id };
}

export function workspaceRequestHeader(workspaceId: string | null | undefined): Record<string, string> {
  if (!workspaceId) return {};
  return { 'X-Workspace-Id': workspaceId };
}
