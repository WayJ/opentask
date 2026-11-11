import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { i18n, setLocale } from '@/locales';
import InitiativesPage from '../index.vue';

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() })
}));

vi.mock('@/service/api', () => ({
  fetchInitiatives: vi.fn(async () => ({ data: { rows: [], total: 0 }, error: null })),
  fetchCreateInitiative: vi.fn(),
  fetchDeleteInitiative: vi.fn()
}));

function createLabels(wrapper: ReturnType<typeof mount>) {
  return wrapper.findAll('button').map(button => button.text().trim());
}

describe('initiative create label', () => {
  afterEach(() => setLocale('zh-CN'));

  it('uses the same verb on the header and the empty state, and switches language', async () => {
    setLocale('zh-CN');
    const wrapper = mount(InitiativesPage, {
      global: {
        plugins: [i18n],
        stubs: {
          NEmpty: {
            props: ['description'],
            template: '<div class="empty"><p>{{ description }}</p><slot name="extra" /></div>'
          },
          NCard: { template: '<div><slot /></div>' },
          NModal: { template: '<div />' },
          NDataTable: { template: '<div />' }
        }
      }
    });
    await flushPromises();
    expect(wrapper.text()).toContain('暂无举措');
    expect(createLabels(wrapper).filter(label => label === '新建举措')).toHaveLength(2);
    expect(wrapper.text()).not.toContain('新建议措');
    setLocale('en-US');
    await wrapper.vm.$nextTick();
    expect(createLabels(wrapper).filter(label => label === 'New initiative')).toHaveLength(2);
    expect(createLabels(wrapper).some(label => label === '新建')).toBe(false);
  });
});
