import { describe, expect, it } from 'vitest';
import { generatedRoutes } from '../elegant/routes';

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

describe('E17 search route', () => {
  it('registers /search hideInMenu', () => {
    const search = findRoute(generatedRoutes as any[], 'search');
    expect(search).toBeTruthy();
    expect(search.path).toBe('/search');
    expect(search.meta?.hideInMenu).toBe(true);
  });
});
