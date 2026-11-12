import { nextTick } from 'vue';
import { mount } from '@vue/test-utils';
import { afterEach, describe, expect, it } from 'vitest';
import { i18n, setLocale } from '@/locales';
import MarkdownEditor from '../MarkdownEditor.vue';

const pass = (tag: string) => ({ template: `<${tag}><slot name="trigger" /><slot /></${tag}>` });
const Empty = { props: ['description'], template: '<p class="empty">{{ description }}</p>' };
const stubs = {
  NButton: pass('button'),
  Button: pass('button'),
  NButtonGroup: pass('div'),
  ButtonGroup: pass('div'),
  NPopover: pass('div'),
  Popover: pass('div'),
  NSpace: pass('div'),
  Space: pass('div'),
  NText: pass('span'),
  Text: pass('span'),
  NEmpty: Empty,
  Empty
};

describe('markdown editor chrome locale', () => {
  afterEach(() => setLocale('zh-CN'));

  it('switches toolbar and default placeholder without remounting', async () => {
    setLocale('zh-CN');
    const wrapper = mount(MarkdownEditor, {
      props: { modelValue: '' },
      global: { plugins: [i18n], stubs }
    });
    expect(wrapper.get('textarea').attributes('placeholder')).toBe('支持 Markdown 语法...');
    expect(wrapper.text()).toContain('语法帮助');
    expect(wrapper.text()).toContain('预览');
    setLocale('en-US');
    await nextTick();
    expect(wrapper.get('textarea').attributes('placeholder')).toBe('Markdown supported...');
    expect(wrapper.text()).toContain('Syntax help');
    expect(wrapper.text()).toContain('Preview');
    expect(wrapper.text()).not.toContain('page.markdownEditor');
    wrapper.unmount();
  });

  it('keeps a parent placeholder when the locale changes', async () => {
    setLocale('zh-CN');
    const wrapper = mount(MarkdownEditor, {
      props: { modelValue: '', placeholder: '详细描述这个问题...' },
      global: { plugins: [i18n], stubs }
    });
    setLocale('en-US');
    await nextTick();
    expect(wrapper.get('textarea').attributes('placeholder')).toBe('详细描述这个问题...');
    wrapper.unmount();
  });
});
