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

      // OAuth2 授权入口：客户端登记的 authorization_endpoint 即此路径
      // （OpenTask 侧是标准 OAuth2 授权服务器的浏览器入口，见
      // docs/superpowers/specs/2026-11-02-oauth2-provider-design.md）
      if (key === 'oauth2') {
        return '/oauth2/authorize';
      }
      if (key === 'oauth2-install') {
        return '/oauth2/install/:installId';
      }

      return routePath;
    },
    onRouteMetaGen(routeName) {
      const key = routeName as RouteKey;

      const constantRoutes: RouteKey[] = ['login', '403', '404', '500'];

      // 详情页路由应该隐藏在菜单中
      const hideInMenuRoutes: RouteKey[] = [
        'workspace-onboarding',
        'knowledge-base',
        'knowledge-base_knowledge_detail',
        'knowledge-base_knowledge_edit',
        'knowledge-base_knowledge_edit_git',
        // OAuth2 授权同意页：仅经授权入口跳转进入，不出现在菜单
        'oauth2',
        'oauth2-install'
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
