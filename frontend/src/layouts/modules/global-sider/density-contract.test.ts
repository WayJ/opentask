import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';
import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { setLocale } from '@/locales';
import ActivityNav from './ActivityNav.vue';
import CustomersNav from './CustomersNav.vue';
import FavoritesNav from './FavoritesNav.vue';
import InsightsNav from './InsightsNav.vue';
import TriageNav from './TriageNav.vue';

const { app, push, favorites } = vi.hoisted(() => ({
  app: { siderCollapse: false },
  push: vi.fn(),
  favorites: { rows: [] as Record<string, unknown>[] }
}));

vi.mock('vue-router', () => ({
  useRoute: () => ({ name: 'issue_list', path: '/issue/list' }),
  useRouter: () => ({ push })
}));

vi.mock('@/store/modules/app', () => ({
  useAppStore: () => app
}));

vi.mock('@/service/api/issue', () => ({
  issueApi: {
    fetchActivityUnreadCount: vi.fn(async () => ({ data: { count: 3, capped: false }, error: null }))
  }
}));

vi.mock('@/service/api/favorites', () => ({
  fetchFavorites: vi.fn(async () => ({ data: { rows: favorites.rows }, error: null }))
}));

const stubs = {
  SvgIcon: {
    props: ['icon'],
    template: '<svg :data-icon="icon" />'
  },
  NTooltip: { template: '<div><slot name="trigger" /><span class="tip"><slot /></span></div>' },
  NSpin: { template: '<div><slot /></div>' },
  NText: { template: '<span><slot /></span>' }
};

const quicklinks = [
  {
    component: TriageNav,
    icon: 'mdi:inbox-arrow-down',
    emoji: '📥',
    zh: ['分诊', '入站'],
    en: ['Triage', 'Incoming'],
    collapsedZh: '分诊',
    collapsedEn: 'Triage',
    file: 'TriageNav.vue'
  },
  {
    component: CustomersNav,
    icon: 'mdi:account-group-outline',
    emoji: '👥',
    zh: ['客户', '需求'],
    en: ['Customers', 'Requests'],
    collapsedZh: '客户',
    collapsedEn: 'Customers',
    file: 'CustomersNav.vue'
  },
  {
    component: InsightsNav,
    icon: 'mdi:chart-box-outline',
    emoji: '📈',
    zh: ['洞察', '效能'],
    en: ['Insights', 'Performance'],
    collapsedZh: '洞察',
    collapsedEn: 'Insights',
    file: 'InsightsNav.vue'
  },
  {
    component: ActivityNav,
    icon: 'mdi:timeline-text-outline',
    emoji: '🔔',
    zh: ['活动', '3'],
    en: ['Activity', '3'],
    collapsedZh: '活动（3）',
    collapsedEn: 'Activity（3）',
    file: 'ActivityNav.vue'
  }
];

function readSider(name: string) {
  return readFileSync(resolve(process.cwd(), 'src/layouts/modules/global-sider', name), 'utf8');
}

describe('quicklink icons and accessible names', () => {
  afterEach(() => {
    app.siderCollapse = false;
    favorites.rows = [];
    push.mockClear();
    setLocale('zh-CN');
  });

  it.each(quicklinks)('$file renders the route icon and keeps the expanded name', async item => {
    setLocale('zh-CN');
    app.siderCollapse = false;
    const open = mount(item.component, { global: { stubs } });
    await flushPromises();
    expect(open.text()).not.toContain(item.emoji);
    expect(open.get('[aria-hidden="true"] svg').attributes('data-icon')).toBe(item.icon);
    expect(open.get('button').attributes('aria-label')).toBeUndefined();
    for (const word of item.zh) expect(open.get('button').text()).toContain(word);
    open.unmount();

    setLocale('en-US');
    const english = mount(item.component, { global: { stubs } });
    await flushPromises();
    expect(english.text()).not.toContain(item.emoji);
    for (const word of item.en) expect(english.get('button').text()).toContain(word);
    english.unmount();
  });

  it.each(quicklinks)('$file names the collapsed button with the existing label', async item => {
    app.siderCollapse = true;
    setLocale('zh-CN');
    const shut = mount(item.component, { global: { stubs } });
    await flushPromises();
    expect(shut.text()).not.toContain(item.emoji);
    expect(shut.get('button').attributes('aria-label')).toBe(item.collapsedZh);
    expect(shut.get('.tip').text()).toBe(item.collapsedZh);
    expect(shut.get('[aria-hidden="true"] svg').attributes('data-icon')).toBe(item.icon);
    shut.unmount();

    setLocale('en-US');
    const english = mount(item.component, { global: { stubs } });
    await flushPromises();
    expect(english.get('button').attributes('aria-label')).toBe(item.collapsedEn);
    expect(english.get('.tip').text()).toBe(item.collapsedEn);
    english.unmount();
  });
});

describe('sider density contract', () => {
  it('gives the four quicklinks one 6px rhythm', () => {
    const index = readSider('index.vue');
    expect(index).toContain(
      '.global-sider__quick {\n  display: flex;\n  flex-direction: column;\n  gap: 6px;\n  padding: 6px 8px 0;\n  margin: 0;\n}'
    );
    expect(index).toContain('padding: 6px 0 0;');
  });

  it('uses a 34px expanded row, a 36px collapsed target, and a local focus ring', () => {
    for (const item of quicklinks) {
      const source = readSider(item.file);
      expect(source).toContain('height: 34px;');
      expect(source).toContain('padding: 0 8px;');
      expect(source).toContain('width: 36px;\n  height: 36px;\n  padding: 0;\n  margin: 0;\n  border-radius: 6px;');
      expect(source).toContain('outline: 2px solid var(--vk-accent);');
      expect(source).toContain('outline-offset: 2px;');
      expect(source).toContain('font-size: 20px;');
      expect(source).toContain('color: currentColor;');
    }
  });

  it('styles the favorites title and the static empty note, and drops the empty illustration', () => {
    const source = readSider('FavoritesNav.vue');
    expect(source).toContain('v-if="showFavorites"');
    expect(source).toContain('favorites-nav__empty-note');
    expect(source).toContain('font-size: 12px;');
    expect(source).toContain('line-height: 18px;');
    expect(source).toContain('margin: 0 0 6px;');
    expect(source).toContain('padding: 0 8px;');
    expect(source).toContain('margin: 0;');
    expect(source).toContain('max-height: 40%;');
    expect(source).not.toContain('NEmpty');
  });

  it('hides a collapsed empty list and shows a static expanded note', async () => {
    app.siderCollapse = false;
    const open = mount(FavoritesNav, { global: { stubs } });
    await flushPromises();
    const note = open.get('p.favorites-nav__empty-note');
    expect(note.text()).toBe('暂无侧栏收藏');
    expect(note.attributes('role')).toBeUndefined();
    expect(note.attributes('tabindex')).toBeUndefined();
    expect(open.find('button').exists()).toBe(false);
    expect(open.html()).not.toContain('n-empty');
    open.unmount();

    app.siderCollapse = true;
    const shut = mount(FavoritesNav, { global: { stubs } });
    await flushPromises();
    expect(shut.find('.favorites-nav').exists()).toBe(false);
    expect(shut.text()).not.toContain('无数据');
    shut.unmount();
  });

  it('renders a populated favorite and keeps its click target when collapsed', async () => {
    favorites.rows = [
      {
        id: 'fav-1',
        workspaceId: 'ws',
        userId: 'u',
        targetType: 'issue',
        targetId: 'issue-long',
        position: 0,
        createdAt: '2026-11-11T08:00:00Z',
        target: { id: 'issue-long', type: 'issue', name: '合成收藏的很长问题标题用来观察省略', code: 'SYN-1' }
      }
    ];
    app.siderCollapse = false;
    const open = mount(FavoritesNav, { global: { stubs } });
    await flushPromises();
    expect(open.find('p.favorites-nav__empty-note').exists()).toBe(false);
    expect(open.get('button').text()).toContain('合成收藏的很长问题标题用来观察省略');
    await open.get('button').trigger('click');
    expect(push).toHaveBeenCalledWith({ path: '/issue/detail', query: { id: 'issue-long' } });
    open.unmount();

    app.siderCollapse = true;
    push.mockClear();
    const shut = mount(FavoritesNav, { global: { stubs } });
    await flushPromises();
    expect(shut.find('.favorites-nav').exists()).toBe(true);
    expect(shut.get('button').text()).not.toContain('合成收藏的很长问题标题用来观察省略');
    expect(shut.get('.favorites-nav__icon').text()).toBe('🎫');
    await shut.get('button').trigger('click');
    expect(push).toHaveBeenCalledWith({ path: '/issue/detail', query: { id: 'issue-long' } });
    shut.unmount();
  });
});
