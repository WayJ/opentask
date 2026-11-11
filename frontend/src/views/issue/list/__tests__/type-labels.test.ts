import { computed, defineComponent } from 'vue';
import { mount } from '@vue/test-utils';
import { afterEach, describe, expect, it } from 'vitest';
import { i18n, setLocale } from '@/locales';
import { labeledOptions } from '@/locales/display-label';
import { useLabelTable } from '@/locales/use-label-table';
import { issueTypeOptions } from '@/constants/issue';
import { groupIssuesBy } from '@/utils/groupIssuesBy';
import IssueListGrouped from '../modules/IssueListGrouped.vue';
import type { Api } from '@/typings/api';

const sampleIssues = [
  {
    id: '1',
    title: 't',
    type: 'bug',
    status: 'open',
    priority: 'medium',
    issue_code: 'T-1'
  }
] as Api.Issue.Issue[];

const TypeHost = defineComponent({
  components: { IssueListGrouped },
  setup() {
    const typeLabels = useLabelTable('page.issueType');
    const options = computed(() => labeledOptions(issueTypeOptions.map(option => option.value), typeLabels.value));
    return { options, typeLabels, issues: sampleIssues, columns: [] };
  },
  template: `
    <div>
      <p class="opt" v-for="opt in options" :key="opt.value">{{ opt.value }}:{{ opt.label }}</p>
      <IssueListGrouped :issues="issues" group-by="type" :columns="columns" />
    </div>
  `
});

describe('issue type labels follow the locale', () => {
  afterEach(() => setLocale('zh-CN'));

  it('updates option labels and group headings without changing values or keys', async () => {
    setLocale('zh-CN');
    const wrapper = mount(TypeHost, {
      global: {
        plugins: [i18n],
        stubs: {
          NCollapse: { template: '<div><slot /></div>' },
          NCollapseItem: { template: '<div class="lane"><slot name="header" /><slot /></div>' },
          NDataTable: { template: '<div />' },
          NEmpty: { template: '<div />' },
          NTag: { template: '<span><slot /></span>' }
        }
      }
    });
    expect(wrapper.text()).toContain('bug:缺陷');
    expect(wrapper.get('.lane-header').text()).toContain('缺陷');
    setLocale('en-US');
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('bug:Bug');
    expect(wrapper.get('.lane-header').text()).toContain('Bug');
    expect(wrapper.get('.lane-header').text()).not.toContain('缺陷');
    const buckets = groupIssuesBy(sampleIssues, 'type', { type: wrapper.vm.typeLabels });
    expect(buckets.find(bucket => bucket.key === 'bug')?.key).toBe('bug');
    expect(buckets.find(bucket => bucket.key === 'bug')?.label).toBe('Bug');
    expect(buckets[0]?.issues[0]?.type).toBe('bug');
  });
});
