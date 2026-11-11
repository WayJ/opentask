import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';
import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import ActivityNav from './ActivityNav.vue';
import CustomersNav from './CustomersNav.vue';
import InsightsNav from './InsightsNav.vue';
import TriageNav from './TriageNav.vue';

const { app, push, route } = vi.hoisted(() => ({
  app: { siderCollapse: false },
  push: vi.fn(),
  route: { name: 'issue_list', path: '/issue/list' }
}));

vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => ({ push })
}));

vi.mock('@/store/modules/app', () => ({
  useAppStore: () => app
}));

vi.mock('@/service/api/issue', () => ({
  issueApi: {
    fetchActivityUnreadCount: vi.fn(async () => ({ data: { count: 0, capped: false }, error: null }))
  }
}));

describe('sider menu density invariants', () => {
  it('keeps the Naive item height override exactly as baseline', () => {
    const css = readFileSync(resolve(process.cwd(), 'src/styles/css/linear-shell.css'), 'utf8');
    expect(css).toContain('.n-menu {\n  --n-item-height: 34px !important;\n}');
  });

  it('does not move item height into the menu component', () => {
    const vue = readFileSync(
      resolve(process.cwd(), 'src/layouts/modules/global-menu/modules/vertical-menu.vue'),
      'utf8'
    );
    expect(vue).not.toContain('--n-item-height');
  });

  it('keeps logo, quick links, favorites, then the menu slot in that order', () => {
    const vue = readFileSync(resolve(process.cwd(), 'src/layouts/modules/global-sider/index.vue'), 'utf8');
    const template = vue.slice(vue.indexOf('<template>'), vue.indexOf('</template>'));
    const order = [
      'GlobalLogo',
      'TriageNav',
      'CustomersNav',
      'InsightsNav',
      'ActivityNav',
      'FavoritesNav',
      'GLOBAL_SIDER_MENU_ID'
    ];
    const positions = order.map(name => template.indexOf(name));
    expect(positions.every(position => position >= 0)).toBe(true);
    expect([...positions]).toEqual([...positions].sort((a, b) => a - b));
  });
});

describe('quicklink navigation still reaches the existing routes', () => {
  it.each([
    { component: TriageNav, name: 'triage', path: '/triage', args: { name: 'triage' } },
    { component: CustomersNav, name: 'customers', path: '/customers', args: { name: 'customers' } },
    { component: InsightsNav, name: 'insights', path: '/insights', args: { name: 'insights' } },
    {
      component: ActivityNav,
      name: 'activity',
      path: '/activity',
      args: { name: 'activity', query: { watching: '1' } }
    }
  ])('pushes $name and marks that route active', async item => {
    app.siderCollapse = false;
    route.name = 'issue_list';
    route.path = '/issue/list';
    push.mockClear();
    const idle = mount(item.component);
    await idle.get('button').trigger('click');
    expect(push).toHaveBeenCalledWith(item.args);
    expect(idle.classes()).not.toContain('active');
    idle.unmount();

    route.name = item.name;
    route.path = item.path;
    const current = mount(item.component);
    expect(current.classes()).toContain('active');
    current.unmount();

    app.siderCollapse = true;
    route.name = 'issue_list';
    route.path = '/issue/list';
    push.mockClear();
    const collapsed = mount(item.component, {
      global: {
        stubs: { NTooltip: { template: '<div><slot name="trigger" /><span class="tip"><slot /></span></div>' } }
      }
    });
    await collapsed.get('button').trigger('click');
    expect(push).toHaveBeenCalledWith(item.args);
    collapsed.unmount();
  });

  it('keeps the customers active routes that are not the list name', () => {
    app.siderCollapse = false;
    for (const routeName of ['customers_detail', 'requests', 'requests_detail']) {
      route.name = routeName;
      route.path = '/requests';
      const wrapper = mount(CustomersNav);
      expect(wrapper.classes()).toContain('active');
      wrapper.unmount();
    }
  });
});
