import { type PropType, type VNodeChild, defineComponent, h } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { i18n, setLocale } from '@/locales';
import TrashPage from '../index.vue';

const api = vi.hoisted(() => ({ listTrash: vi.fn(), restoreIssue: vi.fn() }));
vi.mock('@/service/api/issue', () => ({ issueApi: api }));
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }));

type Row = Record<string, unknown>;
type Column = { key: string; title: string; render?: (row: Row) => VNodeChild };
const Table = defineComponent({
  props: {
    columns: { type: Array as PropType<Column[]>, default: () => [] },
    data: { type: Array as PropType<Row[]>, default: () => [] }
  },
  setup(props) {
    return () =>
      h('table', [
        h('thead', [
          h(
            'tr',
            props.columns.map(c => h('th', { key: c.key }, c.title))
          )
        ]),
        h(
          'tbody',
          props.data.map((row, index) =>
            h(
              'tr',
              { key: index },
              props.columns.map(c => h('td', { key: c.key }, [c.render ? c.render(row) : String(row[c.key] ?? '')]))
            )
          )
        )
      ]);
  }
});
const Card = defineComponent({
  props: { title: String },
  setup(props, { slots }) {
    return () => h('section', [h('h1', props.title), slots['header-extra']?.(), slots.default?.()]);
  }
});
const pass = (tag: string) =>
  defineComponent({
    setup(_, { slots }) {
      return () => h(tag, slots.default?.());
    }
  });
const Empty = defineComponent({
  props: { description: String },
  setup(props) {
    return () => h('p', { class: 'empty' }, props.description);
  }
});
const buttonStub = pass('button');
const tagStub = pass('span');
const spaceStub = pass('div');
const stubs = {
  NCard: Card,
  Card,
  NDataTable: Table,
  DataTable: Table,
  NButton: buttonStub,
  Button: buttonStub,
  NTag: tagStub,
  Tag: tagStub,
  NSpace: spaceStub,
  Space: spaceStub,
  NEmpty: Empty,
  Empty,
  NPagination: true,
  Pagination: true
};
const renderTrash = () => mount(TrashPage, { global: { plugins: [i18n], stubs } });
let wrapper: ReturnType<typeof renderTrash> | undefined;

beforeEach(() => {
  vi.clearAllMocks();
  setActivePinia(createPinia());
  setLocale('zh-CN');
});
afterEach(() => {
  wrapper?.unmount();
  wrapper = undefined;
  setLocale('zh-CN');
});

describe('trash fixture rows and locale reactivity', () => {
  it('renders stored enum values with current labels, without remounting', async () => {
    api.listTrash.mockResolvedValue({
      data: {
        rows: [
          { id: 'fixture-1', issue_code: 'WAY-1', title: 'Fixture issue', status: 'open', priority: 'critical' },
          {
            id: 'fixture-2',
            issue_code: 'WAY-2',
            title: 'Unknown enums',
            status: 'future_status',
            priority: 'future_priority'
          }
        ],
        total: 2
      }
    });
    wrapper = renderTrash();
    await flushPromises();
    expect(api.listTrash).toHaveBeenCalledWith({ page: 1, page_size: 20 });
    expect(wrapper.findAll('th').map(node => node.text())).toEqual([
      '编号',
      '标题',
      '状态',
      '优先级',
      '更新时间',
      '操作'
    ]);
    expect(wrapper.get('h1').text()).toBe('回收站');
    const firstZh = wrapper
      .findAll('tbody tr')[0]
      .findAll('td')
      .map(node => node.text());
    expect(firstZh).toEqual(['WAY-1', 'Fixture issue', '待办', '紧急', '—', '恢复']);
    expect(wrapper.findAll('tbody tr')[1].text()).toContain('future_status');
    expect(wrapper.findAll('tbody tr')[1].text()).toContain('future_priority');
    setLocale('en-US');
    await flushPromises();
    expect(wrapper.findAll('th').map(node => node.text())).toEqual([
      'Key',
      'Title',
      'Status',
      'Priority',
      'Updated',
      'Actions'
    ]);
    expect(wrapper.get('h1').text()).toBe('Trash');
    expect(wrapper.findAll('button').map(node => node.text())).toContain('Back to list');
    expect(wrapper.findAll('button').map(node => node.text())).toContain('Refresh');
    const firstEn = wrapper
      .findAll('tbody tr')[0]
      .findAll('td')
      .map(node => node.text());
    expect(firstEn).toEqual(['WAY-1', 'Fixture issue', 'Open', 'Urgent', '—', 'Restore']);
    const unknown = wrapper
      .findAll('tbody tr')[1]
      .findAll('td')
      .map(node => node.text());
    expect(unknown[2]).toBe('future_status');
    expect(unknown[3]).toBe('future_priority');
    expect(api.listTrash).toHaveBeenCalledTimes(1);
    setLocale('zh-CN');
    await flushPromises();
    expect(wrapper.findAll('tbody tr')[0].findAll('td')[2].text()).toBe('待办');
    expect(wrapper.findAll('tbody tr')[0].findAll('td')[3].text()).toBe('紧急');
  });

  it('updates the empty hint without remounting', async () => {
    api.listTrash.mockResolvedValue({ data: { rows: [], total: 0 } });
    wrapper = renderTrash();
    await flushPromises();
    expect(wrapper.find('table').exists()).toBe(false);
    expect(wrapper.get('.empty').text()).toBe('回收站为空');
    setLocale('en-US');
    await flushPromises();
    expect(wrapper.get('.empty').text()).toBe('Trash is empty');
    expect(api.listTrash).toHaveBeenCalledTimes(1);
  });
});
