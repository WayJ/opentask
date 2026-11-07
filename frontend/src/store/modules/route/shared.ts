import type { RouteLocationNormalizedLoaded, RouteRecordRaw, _RouteRecordBase } from 'vue-router';
import type { ElegantConstRoute, LastLevelRouteKey, RouteKey, RouteMap, RoutePath } from '@elegant-router/types';
import { useSvgIcon } from '@/hooks/common/icon';
import { $t } from '@/locales';

/**
 * 受菜单权限控制的静态路由名集合
 *
 * 与后端 permission_defs.py 中 type=menu 权限的 route_key 一一对应；
 * 新增带 route_key 的菜单页时需同步登记（后端字典 + 此清单）。
 * 未登记的业务路由（home/issue 等）默认放行，不受 menus 过滤影响。
 */
const MENU_PERMISSION_ROUTE_KEYS: readonly string[] = [
  'manage_user',
  'manage_dept',
  'manage_role',
  'manage_perm',
  'manage_oauth2'
];

/**
 * 是否为受菜单权限控制的路由
 *
 * @param routeName 路由名（route_key）
 */
export function isMenuPermissionRoute(routeName: string) {
  return MENU_PERMISSION_ROUTE_KEYS.includes(routeName);
}

/**
 * Filter auth routes by menus (permission route_keys)
 *
 * @param routes Auth routes
 * @param menus menu 类权限 route_key 列表（getUserInfo 下发）
 * @param isSuper 超管（admin 全量放行）
 */
export function filterAuthRoutesByMenus(routes: ElegantConstRoute[], menus: string[] | undefined, isSuper: boolean) {
  // menus 缺失（旧版后端未下发 menus）时回退全放行，防止开发环境锁死
  if (isSuper || !menus) {
    return routes;
  }

  return routes.flatMap(route => filterAuthRouteByMenus(route, menus, true));
}

/**
 * Filter auth route by menus
 *
 * @param route Auth route
 * @param menus menu 类权限 route_key 列表
 * @param parentKept 父级路由是否保留（hideInMenu 功能页跟随）
 */
function filterAuthRouteByMenus(route: ElegantConstRoute, menus: string[], parentKept: boolean): ElegantConstRoute[] {
  const isHidden = Boolean(route.meta?.hideInMenu);

  // 自身放行判定：
  // - hideInMenu 功能页（详情页等）跟随所属菜单（activeMenu 优先）或父级的可见性
  // - 受控菜单路由按 menus 命中 route_key 判定
  // - 其余业务路由默认放行
  let selfAllowed: boolean;
  if (isHidden) {
    selfAllowed = isFunctionalPageAllowedByMenus(route, menus, parentKept);
  } else if (isMenuPermissionRoute(route.name)) {
    selfAllowed = menus.includes(route.name);
  } else {
    selfAllowed = true;
  }

  const filterRoute = { ...route };

  if (filterRoute.children?.length) {
    filterRoute.children = filterRoute.children.flatMap(item => filterAuthRouteByMenus(item, menus, selfAllowed));
  }

  // 容器路由的全部子级被过滤后剪枝（避免菜单出现空分组）
  if (route.children?.length && filterRoute.children?.length === 0) {
    return [];
  }

  return selfAllowed ? [filterRoute] : [];
}

/**
 * hideInMenu 功能页的菜单归属判定
 *
 * @param route 功能页路由
 * @param menus menu 类权限 route_key 列表
 * @param parentKept 父级路由是否保留
 */
function isFunctionalPageAllowedByMenus(route: ElegantConstRoute, menus: string[], parentKept: boolean) {
  const activeMenu = route.meta?.activeMenu as string | undefined;

  // 声明了 activeMenu 的功能页跟随所属菜单的权限（如 manage_user-detail → manage_user）
  if (activeMenu) {
    return isMenuPermissionRoute(activeMenu) ? menus.includes(activeMenu) : true;
  }

  return parentKept;
}

/**
 * sort route by order
 *
 * @param route route
 */
function sortRouteByOrder(route: ElegantConstRoute) {
  if (route.children?.length) {
    route.children.sort((next, prev) => (Number(next.meta?.order) || 0) - (Number(prev.meta?.order) || 0));
    route.children.forEach(sortRouteByOrder);
  }

  return route;
}

/**
 * sort routes by order
 *
 * @param routes routes
 */
export function sortRoutesByOrder(routes: ElegantConstRoute[]) {
  routes.sort((next, prev) => (Number(next.meta?.order) || 0) - (Number(prev.meta?.order) || 0));
  routes.forEach(sortRouteByOrder);

  return routes;
}

/**
 * Get global menus by auth routes
 *
 * @param routes Auth routes
 */
export function getGlobalMenusByAuthRoutes(routes: ElegantConstRoute[]) {
  const menus: App.Global.Menu[] = [];

  routes.forEach(route => {
    if (!route.meta?.hideInMenu) {
      const menu = getGlobalMenuByBaseRoute(route);

      if (route.children?.some(child => !child.meta?.hideInMenu)) {
        menu.children = getGlobalMenusByAuthRoutes(route.children);
      }

      menus.push(menu);
    }
  });

  return menus;
}

/**
 * Update locale of global menus
 *
 * @param menus
 */
export function updateLocaleOfGlobalMenus(menus: App.Global.Menu[]) {
  const result: App.Global.Menu[] = [];

  menus.forEach(menu => {
    const { i18nKey, label, children } = menu;

    const newLabel = i18nKey ? $t(i18nKey) : label;

    const newMenu: App.Global.Menu = {
      ...menu,
      label: newLabel
    };

    if (children?.length) {
      newMenu.children = updateLocaleOfGlobalMenus(children);
    }

    result.push(newMenu);
  });

  return result;
}

/**
 * Get global menu by route
 *
 * @param route
 */
function getGlobalMenuByBaseRoute(route: RouteLocationNormalizedLoaded | ElegantConstRoute) {
  const { SvgIconVNode } = useSvgIcon();

  const { name, path } = route;
  const { title, i18nKey, icon = import.meta.env.VITE_MENU_ICON, localIcon, iconFontSize } = route.meta ?? {};

  const label = i18nKey ? $t(i18nKey) : title!;

  const menu: App.Global.Menu = {
    key: name as string,
    label,
    i18nKey,
    routeKey: name as RouteKey,
    routePath: path as RouteMap[RouteKey],
    icon: SvgIconVNode({ icon, localIcon, fontSize: iconFontSize || 20 })
  };

  return menu;
}

/**
 * Get cache route names
 *
 * @param routes Vue routes (two levels)
 */
export function getCacheRouteNames(routes: RouteRecordRaw[]) {
  const cacheNames: LastLevelRouteKey[] = [];

  routes.forEach(route => {
    // only get last two level route, which has component
    route.children?.forEach(child => {
      if (child.component && child.meta?.keepAlive) {
        cacheNames.push(child.name as LastLevelRouteKey);
      }
    });
  });

  return cacheNames;
}

/**
 * Is route exist by route name
 *
 * @param routeName
 * @param routes
 */
export function isRouteExistByRouteName(routeName: RouteKey, routes: ElegantConstRoute[]) {
  return routes.some(route => recursiveGetIsRouteExistByRouteName(route, routeName));
}

/**
 * Recursive get is route exist by route name
 *
 * @param route
 * @param routeName
 */
function recursiveGetIsRouteExistByRouteName(route: ElegantConstRoute, routeName: RouteKey) {
  let isExist = route.name === routeName;

  if (isExist) {
    return true;
  }

  if (route.children && route.children.length) {
    isExist = route.children.some(item => recursiveGetIsRouteExistByRouteName(item, routeName));
  }

  return isExist;
}

/**
 * Get selected menu key path
 *
 * @param selectedKey
 * @param menus
 */
export function getSelectedMenuKeyPathByKey(selectedKey: string, menus: App.Global.Menu[]) {
  const keyPath: string[] = [];

  menus.some(menu => {
    const path = findMenuPath(selectedKey, menu);

    const find = Boolean(path?.length);

    if (find) {
      keyPath.push(...path!);
    }

    return find;
  });

  return keyPath;
}

/**
 * Find menu path
 *
 * @param targetKey Target menu key
 * @param menu Menu
 */
function findMenuPath(targetKey: string, menu: App.Global.Menu): string[] | null {
  const path: string[] = [];

  function dfs(item: App.Global.Menu): boolean {
    path.push(item.key);

    if (item.key === targetKey) {
      return true;
    }

    if (item.children) {
      for (const child of item.children) {
        if (dfs(child)) {
          return true;
        }
      }
    }

    path.pop();

    return false;
  }

  if (dfs(menu)) {
    return path;
  }

  return null;
}

/**
 * Transform menu to breadcrumb
 *
 * @param menu
 */
function transformMenuToBreadcrumb(menu: App.Global.Menu) {
  const { children, ...rest } = menu;

  const breadcrumb: App.Global.Breadcrumb = {
    ...rest
  };

  if (children?.length) {
    breadcrumb.options = children.map(transformMenuToBreadcrumb);
  }

  return breadcrumb;
}

/**
 * Get breadcrumbs by route
 *
 * @param route
 * @param menus
 */
const HIDDEN_MANAGEMENT = /^(manage|work-management)(_|$)|^workflow_requirements$|^workflow_requirement-detail$/;

export function resolveMenuSelectedKey(route: {
  name?: string | symbol | null;
  meta?: { hideInMenu?: unknown; activeMenu?: unknown };
}) {
  const name = String(route.name ?? '');
  const hideInMenu = Boolean(route.meta?.hideInMenu);
  const activeMenu = route.meta?.activeMenu;
  const active = typeof activeMenu === 'string' ? activeMenu : '';
  return (hideInMenu ? active : name) || name;
}

function presentBreadcrumbs(items: App.Global.Breadcrumb[]) {
  return items
    .filter(item => {
      if (!item.label) return false;
      if (item.i18nKey && item.label === item.i18nKey) return false;
      return !item.label.startsWith('route.');
    })
    .filter((item, index, list) => index === 0 || list[index - 1].label !== item.label);
}

export function breadcrumbsFromMatched(
  route: Pick<RouteLocationNormalizedLoaded, 'path' | 'matched'>,
  labelOf: (i18nKey: string) => string | null
): App.Global.Breadcrumb[] {
  return (route.matched ?? []).flatMap(record => {
    const name = String(record.name ?? '');
    const i18nKey = record.meta?.i18nKey as string | undefined;
    const label = i18nKey ? labelOf(i18nKey) : null;
    if (!name || name === 'root' || HIDDEN_MANAGEMENT.test(name) || !i18nKey || !label) return [];
    const recordPath = typeof record.path === 'string' && record.path.startsWith('/') ? record.path : route.path;
    const item: App.Global.Breadcrumb = {
      key: name,
      label,
      i18nKey: i18nKey as App.I18n.I18nKey,
      routeKey: name as RouteKey,
      routePath: recordPath as RoutePath
    };
    return [item];
  });
}

function findBreadcrumbs(route: RouteLocationNormalizedLoaded, menus: App.Global.Menu[]): App.Global.Breadcrumb[] {
  const key = route.name as string;
  const activeKey = route.meta?.activeMenu;

  for (const menu of menus) {
    if (menu.key === key) {
      return [transformMenuToBreadcrumb(menu)];
    }

    if (menu.key === activeKey) {
      const ROUTE_DEGREE_SPLITTER = '_';
      const parentKey = key.split(ROUTE_DEGREE_SPLITTER).slice(0, -1).join(ROUTE_DEGREE_SPLITTER);
      const breadcrumbMenu = getGlobalMenuByBaseRoute(route);
      if (parentKey !== activeKey) {
        return [transformMenuToBreadcrumb(breadcrumbMenu)];
      }
      return [transformMenuToBreadcrumb(menu), transformMenuToBreadcrumb(breadcrumbMenu)];
    }

    if (menu.children?.length) {
      const result = findBreadcrumbs(route, menu.children);
      if (result.length > 0) {
        return [transformMenuToBreadcrumb(menu), ...result];
      }
    }
  }

  return [];
}

export function getBreadcrumbsByRoute(
  route: RouteLocationNormalizedLoaded,
  menus: App.Global.Menu[],
  labelOf?: (i18nKey: string) => string | null
): App.Global.Breadcrumb[] {
  const fromMenu = presentBreadcrumbs(findBreadcrumbs(route, menus));
  if (fromMenu.length > 0 || !labelOf) return fromMenu;
  return presentBreadcrumbs(breadcrumbsFromMatched(route, labelOf));
}

/**
 * Transform menu to searchMenus
 *
 * @param menus - menus
 * @param treeMap
 */
export function transformMenuToSearchMenus(menus: App.Global.Menu[], treeMap: App.Global.Menu[] = []) {
  if (menus && menus.length === 0) return [];
  return menus.reduce((acc, cur) => {
    if (!cur.children) {
      acc.push(cur);
    }
    if (cur.children && cur.children.length > 0) {
      transformMenuToSearchMenus(cur.children, treeMap);
    }
    return acc;
  }, treeMap);
}
