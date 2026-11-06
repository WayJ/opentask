import type { RouteLocationNormalized, RouteLocationRaw } from 'vue-router';

const DEPRECATED_REQUIREMENT_ROUTES = new Set(['workflow_requirements', 'workflow_requirement-detail']);

/** Requirement pages stay in the tree for shared imports, but navigation leaves them. */
export function requirementSurfaceRedirect(name: RouteLocationNormalized['name']): RouteLocationRaw | null {
  if (name && DEPRECATED_REQUIREMENT_ROUTES.has(String(name))) {
    return { name: 'issue_list' };
  }
  return null;
}

export type WorkspaceGateState = 'pending' | 'ready' | 'onboarding' | 'error';

/**
 * Onboarding is not a constant route, so logout still goes to login.
 * Constant routes (login, /f, /r, /invite) are never forced onto onboarding.
 */
export function workspaceGateRedirect(
  to: { name?: RouteLocationNormalized['name']; meta?: { constant?: boolean } },
  state: { isLogin: boolean; gate: WorkspaceGateState }
): RouteLocationRaw | null {
  const name = String(to.name ?? '');
  if (!state.isLogin) {
    if (name === 'workspace-onboarding') return { name: 'login' };
    return null;
  }
  if (to.meta?.constant) return null;
  if (state.gate === 'onboarding' || state.gate === 'error') {
    if (name !== 'workspace-onboarding') return { name: 'workspace-onboarding' };
    return null;
  }
  if (state.gate === 'ready' && name === 'workspace-onboarding') return { name: 'root' };
  return null;
}
