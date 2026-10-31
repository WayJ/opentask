import type { ElegantConstRoute } from '@elegant-router/types';
import { filterAuthRoutesByMenus } from '../shared';

/** 模拟静态鉴权路由（结构与 elegant/routes.ts 生成结果一致的最小子集） */
function createMockAuthRoutes(): ElegantConstRoute[] {
  return [
    {
      name: 'home',
      path: '/home',
      component: 'layout.base$view.home',
      meta: { title: 'home', i18nKey: 'route.home' }
    },
    {
      name: 'issue',
      path: '/issue',
      component: 'layout.base$view.issue',
      meta: { title: 'issue', i18nKey: 'route.issue' }
    },
    {
      name: 'manage',
      path: '/manage',
      component: 'layout.base',
      meta: { title: 'manage', i18nKey: 'route.manage' },
      children: [
        {
          name: 'manage_dept',
          path: '/manage/dept',
          component: 'view.manage_dept',
          meta: { title: 'manage_dept', i18nKey: 'route.manage_dept' }
        },
        {
          name: 'manage_perm',
          path: '/manage/perm',
          component: 'view.manage_perm',
          meta: { title: 'manage_perm', i18nKey: 'route.manage_perm' }
        },
        {
          name: 'manage_role',
          path: '/manage/role',
          component: 'view.manage_role',
          meta: { title: 'manage_role', i18nKey: 'route.manage_role' }
        },
        {
          name: 'manage_user',
          path: '/manage/user',
          component: 'view.manage_user',
          meta: { title: 'manage_user', i18nKey: 'route.manage_user' }
        },
        {
          name: 'manage_user-detail',
          path: '/manage/user-detail/:id',
          component: 'view.manage_user-detail',
          props: true,
          meta: {
            title: 'manage_user-detail',
            i18nKey: 'route.manage_user-detail',
            hideInMenu: true,
            activeMenu: 'manage_user'
          }
        }
      ]
    }
  ];
}

/** 收集过滤后全部路由名 */
function collectRouteNames(routes: ElegantConstRoute[], acc: string[] = []): string[] {
  routes.forEach(route => {
    acc.push(route.name);
    if (route.children?.length) {
      collectRouteNames(route.children, acc);
    }
  });
  return acc;
}

describe('filterAuthRoutesByMenus', () => {
  it('超管全量放行', () => {
    const routes = createMockAuthRoutes();
    const result = filterAuthRoutesByMenus(routes, [], true);
    expect(collectRouteNames(result)).toEqual(collectRouteNames(routes));
  });

  it('menus 缺失（旧版后端响应）回退全放行', () => {
    const routes = createMockAuthRoutes();
    const result = filterAuthRoutesByMenus(routes, undefined, false);
    expect(collectRouteNames(result)).toEqual(collectRouteNames(routes));
  });

  it('admin 全量 menus：四个管理页 + 用户详情页全保留', () => {
    const result = filterAuthRoutesByMenus(
      createMockAuthRoutes(),
      ['manage_user', 'manage_dept', 'manage_role', 'manage_perm'],
      false
    );
    const names = collectRouteNames(result);
    expect(names).toContain('manage');
    expect(names).toContain('manage_user');
    expect(names).toContain('manage_dept');
    expect(names).toContain('manage_role');
    expect(names).toContain('manage_perm');
    expect(names).toContain('manage_user-detail');
  });

  it('viewer（menus 为空）：管理组整体剪枝，业务路由不受影响', () => {
    const result = filterAuthRoutesByMenus(createMockAuthRoutes(), [], false);
    const names = collectRouteNames(result);
    expect(names).not.toContain('manage');
    expect(names).not.toContain('manage_user');
    expect(names).not.toContain('manage_user-detail');
    expect(names).toContain('home');
    expect(names).toContain('issue');
  });

  it('部分权限：仅保留命中的管理页，未授权管理页与关联详情页被过滤', () => {
    const result = filterAuthRoutesByMenus(createMockAuthRoutes(), ['manage_dept'], false);
    const manage = result.find(route => route.name === 'manage');
    expect(manage).toBeDefined();
    const childNames = (manage?.children ?? []).map(child => child.name);
    expect(childNames).toEqual(['manage_dept']);
  });
});
