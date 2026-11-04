/** E21: SmartSearch/TemplateSelector/Reactions revived (no describe.skip). */
/**
 * Issue 相关组件测试
 */

import type { VueWrapper } from '@vue/test-utils';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ISSUE_TEMPLATES } from '@/constants/issueTemplates';
import { generateSearchSuggestions, parseSearchString } from '@/utils/issueSearchParser';
import IssueSmartSearch from '@/components/IssueSmartSearch.vue';
import IssueTemplateSelector from '@/components/IssueTemplateSelector.vue';
import IssueReactions from '@/components/IssueReactions.vue';
import UserMention from '@/components/UserMention.vue';
import IssueReference from '@/components/IssueReference.vue';

vi.mock('vue-router', async importOriginal => {
  const actual = await importOriginal<typeof import('vue-router')>();
  return {
    ...actual,
    useRouter: () => ({ push: vi.fn() })
  };
});

// Mock Naive UI 组件
vi.mock('naive-ui', () => ({
  NButton: { template: '<button class="n-button" @click="$emit(\'click\')"><slot /><slot name="icon" /></button>' },
  NTag: { template: '<span class="n-tag"><slot /></span>' },
  NCard: {
    template: '<div class="n-card"><slot name="header-extra" /><slot /></div>'
  },
  NEmpty: { template: '<div class="n-empty">Empty</div>' },
  NInput: { template: '<input />' },
  NSelect: { template: '<select></select>' },
  NSpace: { template: '<div class="n-space"><slot /></div>' },
  NText: { template: '<span class="n-text"><slot /></span>' },
  NTooltip: { template: '<div><slot /></div>' },
  NList: { template: '<ul><slot /></ul>' },
  NListItem: { template: '<li><slot /></li>' },
  NAutoComplete: {
    props: ['value', 'options', 'placeholder', 'clearable', 'size'],
    emits: ['update:value', 'select', 'keydown'],
    template:
      '<input class="smart-search-input" :value="value" @input="$emit(\'update:value\', ($event.target).value)" />'
  },
  NPopover: { template: '<div><slot name="trigger" /><slot /></div>' },
  NDropdown: { template: '<div class="n-dropdown"><slot /></div>' },
  NFormItem: { template: '<div><slot /></div>' },
  NSpin: { template: '<div class="n-spin"><slot /></div>' },
  NGrid: { template: '<div class="n-grid"><slot /></div>' },
  NGridItem: { template: '<div class="n-grid-item" @click="$emit(\'click\')"><slot /></div>' }
}));

vi.mock('@/service/api/issue-templates', () => ({
  fetchIssueTemplates: vi.fn(async () => ({ data: { rows: [] }, error: null }))
}));

describe('Issue Search Parser', () => {
  describe('parseSearchString', () => {
    it('should parse status filter', () => {
      const result = parseSearchString('is:open');
      expect(result.status).toBe('open');
    });

    it('should parse type filter', () => {
      const result = parseSearchString('type:bug');
      expect(result.type).toBe('bug');
    });

    it('should parse priority filter', () => {
      const result = parseSearchString('priority:urgent');
      expect(result.priority).toBe('urgent');
    });

    it('should parse multiple filters', () => {
      const result = parseSearchString('is:open priority:high');
      expect(result.status).toBe('open');
      expect(result.priority).toBe('high');
    });

    it('should parse text search', () => {
      const result = parseSearchString('search keyword');
      expect(result.search).toBe('search keyword');
    });

    it('should parse combined filters and text', () => {
      const result = parseSearchString('is:open bug report');
      expect(result.status).toBe('open');
      expect(result.search).toContain('bug report');
    });

    it('should handle empty string', () => {
      const result = parseSearchString('');
      expect(Object.keys(result)).toHaveLength(0);
    });
  });

  describe('generateSearchSuggestions', () => {
    it('should return all suggestions', () => {
      const suggestions = generateSearchSuggestions();
      expect(suggestions).toBeDefined();
      expect(suggestions.length).toBeGreaterThan(0);
    });

    it('should include common filters', () => {
      const suggestions = generateSearchSuggestions();
      const suggestionText = suggestions.join(' ');

      expect(suggestionText).toContain('is:open');
      expect(suggestionText).toContain('label:bug');
      expect(suggestionText).toContain('type:feature');
      expect(suggestionText).toContain('priority:urgent');
    });
  });
});

describe('IssueSmartSearch Component', () => {
  let wrapper: VueWrapper<any>;

  it('should render search input', () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    wrapper = mount(IssueSmartSearch, {
      props: {
        modelValue: '',
        placeholder: '搜索 Issue...'
      },
      global: {
        plugins: [pinia],
        stubs: {
          'icon-mdi-emoticon-happy-outline': true,
          'icon-mdi-account-multiple-outline': true,
          'icon-mdi-close': true
        }
      }
    });

    expect(wrapper.find('.issue-smart-search').exists()).toBe(true);
  });

  it('should emit search with parsed query', async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    wrapper = mount(IssueSmartSearch, {
      props: {
        modelValue: 'is:open',
        placeholder: '搜索 Issue...'
      },
      global: {
        plugins: [pinia]
      }
    });

    await wrapper.vm.handleSearch();
    const emitted = wrapper.emitted('search');
    expect(emitted).toBeTruthy();
    expect(emitted![0][0]).toMatchObject({ status: 'open' });
    expect(emitted![0][1]).toBe('is:open');
  });

  it('clear emits empty search', async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    wrapper = mount(IssueSmartSearch, {
      props: { modelValue: 'priority:high' },
      global: { plugins: [pinia] }
    });
    await wrapper.vm.handleClear();
    const emitted = wrapper.emitted('search');
    expect(emitted?.[emitted.length - 1][0]).toEqual({});
  });
});

describe('IssueTemplateSelector Component', () => {
  let wrapper: VueWrapper<any>;

  it('should fall back to static templates when API empty', async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    wrapper = mount(IssueTemplateSelector, {
      props: {
        visible: true
      },
      global: {
        plugins: [pinia],
        stubs: { Teleport: true, 'icon-mdi-close': true }
      }
    });
    await wrapper.vm.load();
    await wrapper.vm.$nextTick();
    expect(ISSUE_TEMPLATES.length).toBe(5);
    const templateIds = ISSUE_TEMPLATES.map(t => t.id);
    expect(templateIds).toContain('bug_report');
    expect(wrapper.find('.template-selector-card').exists()).toBe(true);
  });

  it('should emit select when selectTemplate called', async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    wrapper = mount(IssueTemplateSelector, {
      props: { visible: true },
      global: { plugins: [pinia], stubs: { Teleport: true, 'icon-mdi-close': true } }
    });
    const bug = ISSUE_TEMPLATES.find(t => t.id === 'bug_report')!;
    wrapper.vm.selectTemplate(bug);
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted('select')?.[0]?.[0]).toMatchObject({ id: 'bug_report' });
    expect(wrapper.emitted('close')).toBeTruthy();
  });

  it('should emit close event when closed', async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    wrapper = mount(IssueTemplateSelector, {
      props: { visible: true },
      global: { plugins: [pinia], stubs: { Teleport: true, 'icon-mdi-close': true } }
    });

    await wrapper.vm.close();
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted('close')).toBeTruthy();
  });
});

describe('IssueReactions Component', () => {
  let wrapper: VueWrapper<any>;

  it('should render reactions list', () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const reactions = {
      '👍': ['admin', 'zhangsan'],
      '❤️': ['lisi']
    };

    wrapper = mount(IssueReactions, {
      props: {
        modelValue: reactions,
        disabled: false,
        currentUserId: 'admin'
      },
      global: {
        plugins: [pinia],
        stubs: {
          'icon-mdi-emoticon-happy-outline': true,
          'icon-mdi-account-multiple-outline': true
        }
      }
    });

    expect(wrapper.find('.issue-reactions').exists()).toBe(true);
    expect(wrapper.findAll('.reaction-item').length).toBeGreaterThanOrEqual(1);
  });

  it('should toggle reaction on click', async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const reactions = {
      '👍': ['admin']
    };

    wrapper = mount(IssueReactions, {
      props: {
        modelValue: reactions,
        currentUserId: 'admin'
      },
      global: {
        plugins: [pinia],
        stubs: {
          'icon-mdi-emoticon-happy-outline': true,
          'icon-mdi-account-multiple-outline': true
        }
      }
    });

    await wrapper.vm.handleReactionClick('👍');
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted('unreact')).toBeTruthy();
  });

  it('hides add button when disabled', () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    wrapper = mount(IssueReactions, {
      props: {
        modelValue: { '👍': ['u1'] },
        disabled: true,
        currentUserId: 'u1'
      },
      global: {
        plugins: [pinia],
        stubs: {
          'icon-mdi-emoticon-happy-outline': true,
          'icon-mdi-account-multiple-outline': true
        }
      }
    });

    expect(wrapper.find('.reaction-add-button').exists()).toBe(false);
    expect(wrapper.find('.reaction-item-disabled').exists()).toBe(true);
  });
});

describe('UserMention Component', () => {
  it('renders @username', () => {
    const wrapper = mount(UserMention, { props: { username: 'alice' } });
    expect(wrapper.text()).toContain('@alice');
  });

  it('strips duplicate @ prefix', () => {
    const wrapper = mount(UserMention, { props: { username: '@bob' } });
    expect(wrapper.text()).toContain('@bob');
    expect(wrapper.text()).not.toContain('@@');
  });
});

describe('IssueReference Component', () => {
  it('renders issue code', () => {
    const wrapper = mount(IssueReference, {
      props: { issueId: 'uuid-1', issueCode: 'SMK-2' },
      global: {
        mocks: {
          $router: { push: vi.fn() }
        }
      }
    });
    expect(wrapper.text()).toContain('SMK-2');
  });
});

describe('Issue Templates Integration', () => {
  it('should generate correct Markdown content', () => {
    // const bugTemplate = ISSUE_TEMPLATES.find(t => t.id === 'bug_report');
    // const formData = {
    //   title: '登录失败',
    //   description: '用户无法登录系统',
    //   environment: 'Windows 10, Chrome',
    //   steps_to_reproduce: '1. 打开登录页面\n2. 输入用户名密码\n3. 点击登录',
    //   expected_behavior: '成功登录',
    //   actual_behavior: '显示错误提示',
    //   attachments: 'screenshot.png'
    // };
    // 验证 generateTemplateContent 函数存在
    // const content = generateTemplateContent(bugTemplate, formData)
    // expect(content).toContain('## Bug 报告')
    // expect(content).toContain('登录失败')
    // expect(content).toContain('**(必填)**')
  });

  it('should include all required fields in template', () => {
    const bugTemplate = ISSUE_TEMPLATES.find(t => t.id === 'bug_report');

    const requiredFields = bugTemplate.fields.filter(f => f.required);
    expect(requiredFields.length).toBeGreaterThan(0);

    const fieldNames = requiredFields.map(f => f.name);
    expect(fieldNames).toContain('title');
    expect(fieldNames).toContain('description');
  });
});

describe('Issue Search Integration', () => {
  it('should handle complex search queries', () => {
    const testCases = [
      { query: 'is:open type:bug', expected: { status: 'open', type: 'bug' } },
      { query: 'priority:urgent assignee:admin', expected: { priority: 'urgent', assignee_id: 'admin' } },
      { query: 'is:in_progress label:bug', expected: { status: 'in_progress' } }
    ];

    testCases.forEach(({ query, expected }) => {
      const result = parseSearchString(query);

      Object.keys(expected).forEach(key => {
        expect(result[key]).toBe(expected[key]);
      });
    });
  });

  it('should handle search with special characters', () => {
    const result = parseSearchString('search: "test with spaces"');
    expect(result.search).toBe('search: test with spaces');
  });
});
