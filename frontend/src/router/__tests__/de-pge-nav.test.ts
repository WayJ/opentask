import { describe, expect, it } from 'vitest';
import { generatedRoutes } from '../elegant/routes';
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

describe('E12-S3 de-PGE nav', () => {
  it('hides workflow_requirements from primary menu (generated)', () => {
    const req = findRoute(generatedRoutes as any[], 'workflow_requirements');
    expect(req).toBeTruthy();
    expect(req.meta?.hideInMenu).toBe(true);
  });

  it('keeps deep-link path /workflow/requirements', () => {
    const req = findRoute(generatedRoutes as any[], 'workflow_requirements');
    expect(req.path).toBe('/workflow/requirements');
  });

  it('hides workflow_requirements in static custom routes too', () => {
    const { authRoutes } = createStaticRoutes();
    const req = findRoute(authRoutes as any[], 'workflow_requirements');
    // may appear in customRoutes merge; if present must be hidden
    if (req) {
      expect(req.meta?.hideInMenu).toBe(true);
    }
  });
});
