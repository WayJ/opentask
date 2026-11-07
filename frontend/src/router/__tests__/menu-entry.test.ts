import { createMemoryHistory, createRouter } from 'vue-router';
import { describe, expect, it } from 'vitest';
import { getGlobalMenusByAuthRoutes, resolveMenuSelectedKey } from '@/store/modules/route/shared';
import { listRedirectForMissingId } from '../list-entry';
import { createStaticRoutes, getAuthVueRoutes } from '../routes';

function findRoute(routes: any[], name: string): any | undefined {
  for (const route of routes) {
    if (route.name === name) return route;
    if (route.children) {
      const hit = findRoute(route.children, name);
      if (hit) return hit;
    }
  }
  return undefined;
}

const groups = [
  {
    parent: 'customers',
    list: 'customers_list',
    detail: 'customers_detail',
    detailPath: '/customers/detail',
    id: 'c-1'
  },
  { parent: 'requests', list: 'requests_list', detail: 'requests_detail', detailPath: '/requests/detail', id: 'r-1' },
  {
    parent: 'initiatives',
    list: 'initiatives_list',
    detail: 'initiatives_detail',
    detailPath: '/initiatives/detail',
    id: 'i-1'
  }
];

describe('menu entries open existing lists', () => {
  const { authRoutes } = createStaticRoutes();

  it.each(groups)('$parent lands on its list once and keeps a deep link', async group => {
    const { parent, list, detail, detailPath, id } = group;
    const found = findRoute(authRoutes as any[], parent);
    expect(found.children[0].name).toBe(list);
    expect(found.children[0].path).toBe('');
    expect(found.children[0].component).toBe(`view.${parent}`);
    const detailRoute = findRoute(found.children, detail);
    expect(detailRoute.path).toBe(detailPath);
    expect(detailRoute.meta.hideInMenu).toBe(true);
    expect(detailRoute.meta.activeMenu).toBe(parent);

    const router = createRouter({
      history: createMemoryHistory(),
      routes: getAuthVueRoutes(authRoutes)
    });
    const names: string[] = [];
    const stop = router.afterEach(to => {
      names.push(String(to.name));
    });
    await router.push({ name: parent });
    expect(router.currentRoute.value.name).toBe(list);
    expect(router.currentRoute.value.path).toBe(`/${parent}`);
    expect(names).toEqual([list]);

    await router.push({ path: detailPath, query: { id } });
    expect(router.currentRoute.value.name).toBe(detail);
    expect(router.currentRoute.value.query.id).toBe(id);

    await router.push({ name: detail });
    expect(router.currentRoute.value.name).toBe(detail);
    expect(router.currentRoute.value.query.id).toBeUndefined();
    await router.replace({ name: list });
    expect(router.currentRoute.value.name).toBe(list);
    expect(router.currentRoute.value.path).toBe(`/${parent}`);

    const before = names.length;
    await router.push({ name: parent });
    expect(router.currentRoute.value.name).toBe(list);
    expect(names.length).toBe(before + 1);
    stop();
  });

  it.each(groups)('$parent detail without an id is replaced before it is confirmed', async group => {
    const { list, detail, id } = group;
    expect(listRedirectForMissingId({ name: detail })).toEqual({ name: list, replace: true });
    expect(listRedirectForMissingId({ name: detail, query: { id } })).toBeNull();
    expect(listRedirectForMissingId({ name: list })).toBeNull();

    const router = createRouter({
      history: createMemoryHistory(),
      routes: getAuthVueRoutes(authRoutes)
    });
    router.beforeEach((to, _from, next) => {
      const redirect = listRedirectForMissingId(to);
      if (redirect) {
        next(redirect);
        return;
      }
      next();
    });
    const names: string[] = [];
    const stop = router.afterEach(to => {
      names.push(String(to.name));
    });
    await router.push({ name: detail });
    expect(router.currentRoute.value.name).toBe(list);
    expect(names).toEqual([list]);

    await router.push({ name: detail, query: { id } });
    expect(router.currentRoute.value.name).toBe(detail);
    expect(router.currentRoute.value.query.id).toBe(id);
    expect(names.at(-1)).toBe(detail);
    stop();
  });

  it('shows initiatives as one highlighted leaf', () => {
    const menus = getGlobalMenusByAuthRoutes(authRoutes);
    const initiatives = menus.find(menu => menu.key === 'initiatives');
    expect(initiatives).toBeTruthy();
    expect(initiatives?.children?.length ?? 0).toBe(0);
    expect(
      resolveMenuSelectedKey({
        name: 'initiatives_list',
        meta: { hideInMenu: true, activeMenu: 'initiatives' }
      })
    ).toBe('initiatives');
    expect(
      resolveMenuSelectedKey({
        name: 'initiatives_detail',
        meta: { hideInMenu: true, activeMenu: 'initiatives' }
      })
    ).toBe('initiatives');
  });
});
