import type { ElegantConstRoute, RouteKey } from '@elegant-router/types';

const DETAIL_NAME: Record<string, string> = {
  customers: 'customers_detail',
  requests: 'requests_detail',
  initiatives: 'initiatives_detail'
};

const LIST_FOR_DETAIL: Record<string, string> = {
  customers_detail: 'customers_list',
  requests_detail: 'requests_list',
  initiatives_detail: 'initiatives_list'
};

export function listRedirectForMissingId(to: { name?: unknown; query?: { id?: unknown } }) {
  const list = LIST_FOR_DETAIL[String(to.name ?? '')];
  if (!list) return null;
  const raw = to.query?.id;
  const values = Array.isArray(raw) ? raw : [raw];
  const present = values.some(item => String(item ?? '').length > 0);
  if (present) return null;
  return { name: list, replace: true as const };
}

/**
 * Mount the existing list view as the default child.
 *
 * elegant-router drops index.vue when a folder also has children, and a production
 * build regenerates that shape. Injecting here keeps the list after codegen without
 * adding *_list to the generated RouteKey union. An empty child path terminates:
 * the parent redirects to the list name, and both records share /customers.
 */
export function attachDefaultListChildren(routes: ElegantConstRoute[]): ElegantConstRoute[] {
  return routes.map(route => {
    const detailName = DETAIL_NAME[route.name];
    if (!detailName || !route.children?.length) return route;
    const listName = `${route.name}_list`;
    if (route.children.some(child => child.name === listName)) return route;

    const list: ElegantConstRoute = {
      name: listName,
      path: '',
      component: `view.${route.name}`,
      meta: {
        title: route.name,
        i18nKey: `route.${route.name}` as App.I18n.I18nKey,
        hideInMenu: true,
        activeMenu: route.name as RouteKey
      }
    };

    const children = route.children.map(child => {
      if (child.name !== detailName) return child;
      return {
        ...child,
        meta: {
          ...child.meta,
          hideInMenu: true,
          activeMenu: route.name as RouteKey
        }
      };
    });

    return { ...route, children: [list, ...children] } as ElegantConstRoute;
  });
}

export function replaceWithListWhenIdMissing(
  id: string,
  router: { replace: (to: { name: string }) => unknown },
  listName: string
) {
  if (id) return false;
  router.replace({ name: listName });
  return true;
}
