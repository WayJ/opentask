import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import GlobalBreadcrumb from '../index.vue';

const push = vi.fn();

vi.mock('vue-router', () => ({
  useRouter: () => ({ push })
}));

vi.mock('@/store/modules/theme', () => ({
  useThemeStore: () => ({ header: { breadcrumb: { visible: true, showIcon: false } } })
}));

vi.mock('@/store/modules/route', () => ({
  useRouteStore: () => ({
    breadcrumbs: [
      { key: 'customers', label: '客户', routeKey: 'customers', routePath: '/customers' },
      { key: 'customers_detail', label: '客户详情', routeKey: 'customers_detail', routePath: '/customers/detail' }
    ]
  })
}));

vi.mock('@/hooks/common/router', () => ({
  useRouterPush: () => ({ routerPushByKey: vi.fn() })
}));

describe('GlobalBreadcrumb', () => {
  it('navigates when an earlier crumb is clicked', async () => {
    const wrapper = mount(GlobalBreadcrumb, {
      global: {
        stubs: {
          NBreadcrumb: { template: '<nav><slot /></nav>' },
          NBreadcrumbItem: { template: '<div><slot /></div>' },
          NDropdown: { template: '<div><slot /></div>' }
        }
      }
    });
    await wrapper.get('button.ot-crumb').trigger('click');
    expect(push).toHaveBeenCalledWith({ name: 'customers' });
    expect(wrapper.text()).toContain('客户详情');
  });
});
