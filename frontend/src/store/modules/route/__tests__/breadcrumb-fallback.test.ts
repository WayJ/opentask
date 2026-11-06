import type { RouteLocationNormalizedLoaded } from 'vue-router';
import { describe, expect, it } from 'vitest';
import { setLocale } from '@/locales';
import { breadcrumbLabel } from '../index';
import { breadcrumbsFromMatched, getBreadcrumbsByRoute } from '../shared';

const labels: Record<string, string> = {
  'route.customers': '客户',
  'route.customers_detail': '客户详情',
  'route.settings_sla': 'SLA 策略',
  'route.manage': 'route.manage'
};

const labelOf = (key: string) => labels[key] ?? null;

function routeOf(partial: Record<string, unknown>) {
  return partial as unknown as RouteLocationNormalizedLoaded;
}

describe('breadcrumb fallback', () => {
  it('builds linked crumbs from the matched route when the page is not in the menu', () => {
    const items = breadcrumbsFromMatched(
      routeOf({
        path: '/customers/detail',
        matched: [
          { name: 'customers', path: '/customers', meta: { i18nKey: 'route.customers' } },
          { name: 'customers_detail', path: '/customers/detail', meta: { i18nKey: 'route.customers_detail' } }
        ]
      }),
      labelOf
    );
    expect(items.map(item => item.label)).toEqual(['客户', '客户详情']);
    expect(items[0].key).toBe('customers');
    expect(items[0].routePath).toBe('/customers');
    expect(items[1].key).toBe('customers_detail');
  });

  it('drops unregistered labels and hidden management routes', () => {
    const items = getBreadcrumbsByRoute(
      routeOf({
        name: 'manage_user',
        path: '/manage/user',
        meta: {},
        matched: [
          { name: 'manage', path: '/manage', meta: { i18nKey: 'route.manage' } },
          { name: 'manage_user', path: '/manage/user', meta: { i18nKey: 'route.not_registered' } }
        ]
      }),
      [],
      labelOf
    );
    expect(items).toEqual([]);
  });

  it('follows the active locale', () => {
    setLocale('zh-CN');
    expect(breadcrumbLabel('route.activity')).toBe('活动');
    setLocale('en-US');
    expect(breadcrumbLabel('route.activity')).toBe('Activity');
    expect(breadcrumbLabel('route.not_registered')).toBeNull();
    setLocale('zh-CN');
  });
});
