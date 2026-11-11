import { defineComponent, h } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { downloadInsightsExport, updateNotifPrefs } from '@/service/api';
import { i18n, setLocale } from '@/locales';
import InsightsPage from '../index.vue';

vi.mock('@/service/api', async () => {
  const actual = await vi.importActual<typeof import('@/service/api')>('@/service/api');
  return {
    ...actual,
    fetchInsightsSummary: vi.fn(async () => ({
      data: {
        statusCounts: { open: 2, in_progress: 1, mystery: 1 },
        priorityCounts: { high: 2 },
        assigneeCounts: [],
        createdVsCompleted: [{ date: '2026-11-01', created: 1, completed: 1 }],
        estimateVelocity: { buckets: [{ date: '2026-11-01', completedPoints: 3 }] },
        cycleSnapshot: { issueCount: 4, completedCount: 1, estimatePointsSum: 8, cycleName: 'Sprint' }
      },
      error: null
    })),
    fetchCycles: vi.fn(async () => ({
      data: { rows: [{ id: 'c1', name: 'Sprint', status: 'active' }] },
      error: null
    })),
    fetchInsightsReports: vi.fn(async () => ({ data: { rows: [] }, error: null })),
    fetchProjectList: vi.fn(async () => ({ data: [], error: null })),
    fetchNotifPrefs: vi.fn(async () => ({ data: { insights_digest: false }, error: null })),
    updateNotifPrefs: vi.fn(async () => ({ data: { insights_digest: true }, error: null })),
    downloadInsightsExport: vi.fn(async () => new Blob(['a,b'])),
    tagApi: { ...(actual.tagApi || {}), list: vi.fn(async () => ({ data: { rows: [] }, error: null })) }
  };
});

vi.mock('@/store/modules/auth', () => ({
  useAuthStore: () => ({ userInfo: { userId: 'u1' } })
}));

const passthrough = (name: string) =>
  defineComponent({
    name,
    setup(_, { slots }) {
      return () => h('div', slots.default?.());
    }
  });

const NCard = defineComponent({
  name: 'NCard',
  props: { title: { type: String, default: '' } },
  setup(props, { slots }) {
    return () => h('section', [h('h3', props.title), slots.default?.()]);
  }
});

const NSelect = defineComponent({
  name: 'NSelect',
  props: {
    options: { type: Array, default: () => [] },
    value: { type: [String, Number, Array], default: null }
  },
  setup(props) {
    return () =>
      h(
        'div',
        { class: 'select-stub' },
        (props.options as { label: string; value: string }[]).map(option =>
          h('span', { 'data-value': String(option.value) }, option.label)
        )
      );
  }
});

describe('insights labels', () => {
  afterEach(() => setLocale('zh-CN'));

  it('switches distribution labels and keeps counts, keys, and the CSV payload field', async () => {
    setLocale('zh-CN');
    const wrapper = mount(InsightsPage, {
      global: {
        plugins: [i18n],
        stubs: {
          NCard,
          NSelect,
          NSpin: passthrough('NSpin'),
          NGrid: passthrough('NGrid'),
          NGi: passthrough('NGi'),
          NEmpty: passthrough('NEmpty'),
          NProgress: true,
          NInput: true,
          NButton: passthrough('NButton'),
          NSwitch: defineComponent({
            name: 'NSwitch',
            emits: ['update:value'],
            setup(_, { emit }) {
              return () => h('button', { class: 'digest-switch', onClick: () => emit('update:value', true) }, 'switch');
            }
          })
        }
      }
    });
    await flushPromises();

    expect(wrapper.text()).toContain('工作区效能摘要。多个标签取并集');
    expect(wrapper.text()).toContain('待办');
    expect(wrapper.text()).toContain('进行中');
    expect(wrapper.text()).toContain('高');
    expect(wrapper.text()).toContain('mystery');
    expect(wrapper.text()).toContain('2');
    expect(wrapper.text()).not.toContain('in_progress');
    expect(wrapper.text()).not.toContain('多标签 OR');
    expect(wrapper.text()).toContain('Sprint · 进行中');
    expect(wrapper.get('[data-value="c1"]').attributes('data-value')).toBe('c1');
    expect(wrapper.text()).toContain('估点合计');
    expect(wrapper.text()).toContain('8');
    expect(wrapper.text()).toContain('近 14 日 · 创建与完成');
    expect(wrapper.text()).toContain('点数');

    setLocale('en-US');
    await flushPromises();
    expect(wrapper.text()).toContain('Workspace performance summary');
    expect(wrapper.text()).toContain('Open');
    expect(wrapper.text()).toContain('In progress');
    expect(wrapper.text()).toContain('High');
    expect(wrapper.text()).toContain('mystery');
    expect(wrapper.text()).toContain('Sprint · Active');
    expect(wrapper.get('[data-value="c1"]').attributes('data-value')).toBe('c1');
    expect(wrapper.text()).toContain('Export CSV');
    expect(wrapper.text()).toContain('Performance digest');
    expect(wrapper.text()).not.toContain('in_progress');

    const downloads: string[] = [];
    const orig = document.createElement.bind(document);
    const spy = vi.spyOn(document, 'createElement').mockImplementation(((tag: string) => {
      const el = orig(tag);
      if (tag === 'a') {
        const anchor = el as HTMLAnchorElement;
        anchor.click = () => downloads.push(anchor.download);
      }
      return el;
    }) as typeof document.createElement);
    await wrapper.get('button, .digest-switch').trigger('click');
    expect(updateNotifPrefs).toHaveBeenCalledWith({ insights_digest: true });
    const exportButton = wrapper.findAll('div, button, span').find(node => node.text() === 'Export CSV');
    await exportButton?.trigger('click');
    expect(downloadInsightsExport).toHaveBeenCalled();
    expect(downloads).toContain('insights-export.csv');
    spy.mockRestore();
  });
});
