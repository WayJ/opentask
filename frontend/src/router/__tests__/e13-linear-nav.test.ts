import { describe, expect, it } from 'vitest';
import { createStaticRoutes } from '../routes';

function findRoute(routes: any[], name: string): any | undefined {
  for (const r of routes) {
    if (r.name === name) return r;
    if (r.children) {
      const hit = findRoute(r.children, name);
      if (hit) return hit;
    }
  }
  return undefined;
}

describe('E13 Linear sidebar IA', () => {
  const { authRoutes } = createStaticRoutes();

  it('dedupes custom vs generated top-level names', () => {
    const names = authRoutes.map((r: any) => r.name);
    expect(names.filter((n: string) => n === 'workflow')).toHaveLength(1);
    expect(names.filter((n: string) => n === 'work-management')).toHaveLength(1);
    expect(names.filter((n: string) => n === 'issue')).toHaveLength(1);
  });

  it('shows Inbox early and hides Soybean clutter groupings', () => {
    const inbox = findRoute(authRoutes as any[], 'inbox');
    expect(inbox).toBeTruthy();
    expect(inbox.meta?.hideInMenu).toBeFalsy();
    expect(Number(inbox.meta?.order)).toBeLessThan(3);

    for (const name of ['work-management', 'manage', 'dashboard', 'home']) {
      const r = findRoute(authRoutes as any[], name);
      expect(r, name).toBeTruthy();
      expect(r.meta?.hideInMenu, name).toBe(true);
    }
  });

  it('puts Projects under Workspace and hides top-level workflow', () => {
    const workflow = findRoute(authRoutes as any[], 'workflow');
    expect(workflow).toBeTruthy();
    expect(workflow.meta?.hideInMenu).toBe(true);

    const workspace = findRoute(authRoutes as any[], 'workspace');
    expect(workspace).toBeTruthy();
    expect(workspace.meta?.hideInMenu).toBeFalsy();

    const projectsUnderWs = (workspace.children || []).find((c: any) => c.name === 'workflow_projects');
    expect(projectsUnderWs, 'workflow_projects should be a workspace child').toBeTruthy();
    expect(projectsUnderWs.meta?.hideInMenu).toBeFalsy();

    // top-level menu must not expose Projects via workflow group
    expect(workflow.meta?.hideInMenu).toBe(true);
  });

  it('still hides workflow_requirements (E12 de-PGE)', () => {
    const req = findRoute(authRoutes as any[], 'workflow_requirements');
    expect(req?.meta?.hideInMenu).toBe(true);
  });
});
