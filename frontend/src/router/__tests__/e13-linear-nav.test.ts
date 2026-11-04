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

  it('keeps Projects (workflow) and Workspace reachable in menu', () => {
    const workflow = findRoute(authRoutes as any[], 'workflow');
    expect(workflow.meta?.hideInMenu).toBeFalsy();
    const projects = findRoute(authRoutes as any[], 'workflow_projects');
    expect(projects).toBeTruthy();
    expect(projects.meta?.hideInMenu).toBeFalsy();

    const workspace = findRoute(authRoutes as any[], 'workspace');
    expect(workspace.meta?.hideInMenu).toBeFalsy();
  });

  it('still hides workflow_requirements (E12 de-PGE)', () => {
    const req = findRoute(authRoutes as any[], 'workflow_requirements');
    expect(req?.meta?.hideInMenu).toBe(true);
  });
});
