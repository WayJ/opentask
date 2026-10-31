import type { RouteMeta } from 'vue-router';
import ElegantVueRouter from '@elegant-router/vue/vite';
import type { RouteKey } from '@elegant-router/types';

export function setupElegantRouter() {
  return ElegantVueRouter({
    layouts: {
      base: 'src/layouts/base-layout/index.vue',
      blank: 'src/layouts/blank-layout/index.vue'
    },
    routePathTransformer(routeName, routePath) {
      const key = routeName as RouteKey;

      if (key === 'login') {
        const modules: UnionKey.LoginModule[] = [
          'pwd-login',
          'code-login',
          'register',
          'reset-pwd',
          'bind-wechat',
          'change-password',
          'dingtalk-callback'
        ];

        const moduleReg = modules.join('|');

        return `/login/:module(${moduleReg})?`;
      }

      return routePath;
    },
    onRouteMetaGen(routeName) {
      const key = routeName as RouteKey;

      const constantRoutes: RouteKey[] = ['login', '403', '404', '500', 'workflow-guide'];

      // 详情页路由应该隐藏在菜单中
      const hideInMenuRoutes: RouteKey[] = [
        'knowledge-base',
        'knowledge-base_knowledge_detail',
        'knowledge-base_knowledge_edit',
        'knowledge-base_knowledge_edit_git'
      ];

      const meta: Partial<RouteMeta> = {
        title: key,
        i18nKey: `route.${key}` as App.I18n.I18nKey
      };

      if (constantRoutes.includes(key)) {
        meta.constant = true;
      }

      if (hideInMenuRoutes.includes(key)) {
        meta.hideInMenu = true;
      }

      return meta;
    }
  });
}
