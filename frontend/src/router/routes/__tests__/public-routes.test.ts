import { describe, expect, it } from 'vitest';
import { createStaticRoutes, getAuthVueRoutes } from '../index';

function hasPath(routes: { path: string; children?: { path: string }[] }[], path: string): boolean {
  return routes.some(route => route.path === path || (route.children ? hasPath(route.children, path) : false));
}

describe('public form routes survive route generation', () => {
  it('keeps /f/:token and /r/:token as constant routes with a view', () => {
    const { constantRoutes } = createStaticRoutes();
    const vueRoutes = getAuthVueRoutes(constantRoutes);

    expect(hasPath(vueRoutes, '/f/:token')).toBe(true);
    expect(hasPath(vueRoutes, '/r/:token')).toBe(true);
    expect(hasPath(vueRoutes, '/invite/:token')).toBe(true);
  });
});
