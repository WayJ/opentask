import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { defineComponent, h } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { NInput } from 'naive-ui';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { i18n, setLocale } from '@/locales';
import SlaSettings from '../index.vue';
import { policyNameAfterLocaleChange } from '../policy-name';

vi.mock('@/service/api/sla', async () => {
  const actual = await vi.importActual<typeof import('@/service/api/sla')>('@/service/api/sla');
  return {
    ...actual,
    fetchSlaPolicies: vi.fn(async () => ({ data: { rows: [] }, error: null })),
    fetchHolidayPacks: vi.fn(async () => ({ data: { rows: [] }, error: null }))
  };
});

vi.mock('@/service/api/workspace', async () => {
  const actual = await vi.importActual<typeof import('@/service/api/workspace')>('@/service/api/workspace');
  return {
    ...actual,
    fetchWorkspace: vi.fn(async () => ({
      data: { timezone: 'Asia/Shanghai', businessHours: null },
      error: null
    })),
    fetchWorkspaceList: vi.fn(async () => ({ data: [], error: null })),
    fetchUpdateWorkspace: vi.fn()
  };
});

const passthrough = (name: string) =>
  defineComponent({
    name,
    setup(_, { slots }) {
      return () => h('div', slots.default?.());
    }
  });

describe('policyNameAfterLocaleChange', () => {
  it('keeps a loaded or typed name and only fills a new untouched policy', () => {
    expect(
      policyNameAfterLocaleChange({ dirty: false, loaded: false, current: '进行中停留' }, 'Time in progress')
    ).toBe('Time in progress');
    expect(policyNameAfterLocaleChange({ dirty: true, loaded: false, current: '我的策略' }, 'Time in progress')).toBe(
      '我的策略'
    );
    expect(policyNameAfterLocaleChange({ dirty: false, loaded: true, current: '已保存' }, 'Time in progress')).toBe(
      '已保存'
    );
  });
});

describe('SLA settings labels', () => {
  afterEach(() => {
    setLocale('zh-CN');
  });

  it('switches visible labels and only replaces an untouched new name', async () => {
    setActivePinia(createPinia());
    setLocale('zh-CN');
    const wrapper = mount(SlaSettings, {
      global: {
        plugins: [i18n],
        stubs: {
          NCard: passthrough('NCard'),
          NForm: passthrough('NForm'),
          NFormItem: passthrough('NFormItem'),
          NModal: passthrough('NModal'),
          NDataTable: true,
          NSwitch: true,
          NSelect: true,
          NInputNumber: true,
          NTimePicker: true
        }
      }
    });
    await flushPromises();

    expect(wrapper.text()).toContain('立即执行到期检查');
    expect(wrapper.text()).toContain('支持「状态停留」和「首次响应」两种度量');
    expect(wrapper.text()).toContain('POST /api/sla/run-due');
    expect(wrapper.text()).not.toContain('立即 run-due');
    expect(wrapper.text()).not.toContain('time_in_status');
    expect(wrapper.text()).toContain('关闭日整天不计入营业分钟');
    expect(wrapper.text()).toContain('添加例外');
    expect(wrapper.text()).toContain('周一');
    expect(wrapper.text()).not.toContain('SLA deadline');
    expect(wrapper.text()).not.toContain('running/paused');
    expect(wrapper.text()).not.toContain('forced_open');
    expect(wrapper.get('input[placeholder="名称"]').element).toHaveProperty('value', '进行中停留');

    const source = readFileSync(resolve('src/views/settings/sla/index.vue'), 'utf8');
    expect(source).toContain('lookupLabel(metricLabels.value, row.metric)');
    expect(source).toContain('lookupLabel(exceptionLabels.value, kind)');
    expect(source).toContain('labeledOptions(SLA_METRICS, metricLabels.value)');
    expect(source).not.toContain('请选择 policy');
    expect(source).not.toContain('{{ row._tag }}');
    expect(source).not.toContain('暂无例外日');
    expect(source).not.toContain("'默认窗'");

    setLocale('en-US');
    await flushPromises();
    expect(wrapper.text()).toContain('Run due checks');
    expect(wrapper.text()).toContain('Two metrics: time in status and first response.');
    expect(wrapper.text()).toContain('No exception days');
    expect(wrapper.text()).toContain('Add exception');
    expect(wrapper.text()).toContain('Mon');
    expect(wrapper.text()).not.toContain('添加例外');
    expect(wrapper.text()).not.toContain('周一');
    expect(wrapper.text()).not.toContain('暂无例外日');
    expect(wrapper.text()).toContain('IANA time zone');
    expect(wrapper.text()).toContain('A closed day counts no business minutes');
    expect(wrapper.text()).toContain('09:00-12:00,13:00-18:00');
    expect(wrapper.text()).not.toContain('forced_open');
    expect(wrapper.text()).not.toContain('SLA deadline');
    expect(wrapper.get('input[placeholder="名称"]').element).toHaveProperty('value', 'Time in progress');

    const onName = wrapper.getComponent(NInput).props('onUpdate:value') as (value: string) => void;
    onName('My policy');
    await flushPromises();
    expect(wrapper.get('input[placeholder="名称"]').element).toHaveProperty('value', 'My policy');
    setLocale('zh-CN');
    await flushPromises();
    expect(wrapper.get('input[placeholder="名称"]').element).toHaveProperty('value', 'My policy');
  });
});
