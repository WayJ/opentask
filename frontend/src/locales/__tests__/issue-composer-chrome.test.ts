import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import en from '../langs/en-us';
import zh from '../langs/zh-cn';

const source = (path: string) => readFileSync(resolve(path), 'utf8');
const create = source('src/views/issue/create/index.vue');
const edit = source('src/views/issue/edit/index.vue');
const editor = source('src/components/MarkdownEditor.vue');
const selector = source('src/components/IssueTemplateSelector.vue');
const form = source('src/components/IssueTemplateForm.vue');
const detail = source('src/views/issue/detail/index.vue');
const typings = source('src/typings/app.d.ts');

const composer = [
  ['backToList', '返回列表 (Esc)', 'Back to list (Esc)'],
  ['backToDetail', '返回详情 (Esc)', 'Back to detail (Esc)'],
  ['unsaved', '未保存', 'Unsaved'],
  ['useTemplate', '使用模板', 'Use template'],
  ['useTemplateHint', '从模板创建问题', 'Create an issue from a template'],
  ['previewMode', '预览模式', 'Preview mode'],
  ['editMode', '编辑模式', 'Edit mode'],
  ['titlePlaceholder', '输入问题标题...', 'Enter an issue title...'],
  ['description', '描述', 'Description'],
  ['markdownHint', '支持 Markdown 语法，+ 引用其他资源', 'Markdown supported. + mentions other resources'],
  ['descriptionPlaceholder', '详细描述这个问题...', 'Describe this issue...'],
  ['attachments', '附件', 'Attachments'],
  ['addAttachment', '添加附件', 'Add attachment'],
  ['preview', '预览', 'Preview'],
  ['noDescription', '暂无描述内容', 'No description yet'],
  ['exitTitle', '确认退出', 'Leave page'],
  ['exitContent', '你有未保存的更改，确定要退出吗？', 'You have unsaved changes. Leave anyway?'],
  ['exitDiscard', '放弃更改', 'Discard changes'],
  ['exitKeep', '继续编辑', 'Keep editing']
] as const;

const templateCopy = [
  [
    'intro',
    '选择一个模板来快速创建规范的问题（工作区模板）',
    'Pick a template to create a well-formed issue (workspace templates)'
  ],
  ['empty', '暂无可用模板', 'No templates available'],
  ['footerHint', '提示：你也可以不使用模板，直接创建空白问题', 'Tip: you can skip templates and start a blank issue'],
  ['cancel', '取消', 'Cancel'],
  ['fieldTitle', '标题', 'Title'],
  ['fieldDescription', '描述', 'Description'],
  ['contentPreview', '内容预览', 'Content preview'],
  ['previewHint', '以下内容将填充到问题描述中：', 'This text will be filled into the issue description:']
] as const;

const editorCopy = [
  ['boldTitle', '粗体 (Ctrl+B)', 'Bold (Ctrl+B)'],
  ['italicTitle', '斜体 (Ctrl+I)', 'Italic (Ctrl+I)'],
  ['inlineCodeTitle', '行内代码 (Ctrl+`)', 'Inline code (Ctrl+`)'],
  ['codeBlockTitle', '代码块', 'Code block'],
  ['linkTitle', '链接', 'Link'],
  ['bulletListTitle', '无序列表', 'Bulleted list'],
  ['quoteTitle', '引用', 'Quote'],
  ['headingTitle', '标题', 'Heading'],
  ['taskListTitle', '任务列表', 'Task list'],
  ['edit', '编辑', 'Edit'],
  ['preview', '预览', 'Preview'],
  ['syntaxHelp', '语法帮助', 'Syntax help'],
  ['syntaxTitle', 'Markdown 语法', 'Markdown syntax'],
  ['glossBold', '粗体', 'Bold'],
  ['glossItalic', '斜体', 'Italic'],
  ['glossInlineCode', '行内代码', 'Inline code'],
  ['glossQuote', '引用块', 'Quote block'],
  ['glossMention', '提及用户', 'Mention a user'],
  ['glossIssueRef', '引用问题', 'Reference an issue'],
  ['defaultPlaceholder', '支持 Markdown 语法...', 'Markdown supported...'],
  ['emptyPreview', '输入内容后预览', 'Nothing to preview yet'],
  ['characters', '{n} 字符', '{n} characters'],
  ['footerHint', '支持 Markdown 语法 • Ctrl+Enter 快速提交', 'Markdown supported • Ctrl+Enter to submit']
] as const;

const createCalls: Record<string, number> = {
  backToList: 1,
  unsaved: 1,
  useTemplate: 1,
  useTemplateHint: 1,
  previewMode: 1,
  editMode: 1,
  titlePlaceholder: 1,
  description: 1,
  markdownHint: 1,
  descriptionPlaceholder: 1,
  attachments: 1,
  addAttachment: 1,
  preview: 1,
  noDescription: 1,
  exitTitle: 1,
  exitContent: 1,
  exitDiscard: 1,
  exitKeep: 1
};
const editCalls: Record<string, number> = {
  backToDetail: 1,
  unsaved: 1,
  previewMode: 1,
  editMode: 1,
  titlePlaceholder: 1,
  description: 1,
  markdownHint: 1,
  descriptionPlaceholder: 1,
  preview: 1,
  noDescription: 1,
  exitTitle: 1,
  exitContent: 1,
  exitDiscard: 1,
  exitKeep: 1
};
const editorCalls: Record<string, number> = {
  boldTitle: 1,
  italicTitle: 1,
  inlineCodeTitle: 1,
  codeBlockTitle: 2,
  linkTitle: 2,
  bulletListTitle: 2,
  quoteTitle: 1,
  headingTitle: 2,
  taskListTitle: 2,
  edit: 1,
  preview: 1,
  syntaxHelp: 1,
  syntaxTitle: 1,
  glossBold: 1,
  glossItalic: 1,
  glossInlineCode: 1,
  glossQuote: 1,
  glossMention: 1,
  glossIssueRef: 1,
  defaultPlaceholder: 1,
  emptyPreview: 1,
  characters: 1,
  footerHint: 1
};

function leafKeys(value: unknown, prefix = ''): string[] {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return prefix ? [prefix] : [];
  return Object.entries(value as Record<string, unknown>).flatMap(([key, child]) =>
    leafKeys(child, prefix ? `${prefix}.${key}` : key)
  );
}

function schemaBlock(name: string): string {
  const match = typings.match(new RegExp(`${name}\\s*:\\s*\\{`));
  expect(match?.index).toBeGreaterThan(-1);
  const start = match?.index ?? 0;
  let depth = 0;
  let seen = false;
  for (let i = start; i < typings.length; i += 1) {
    if (typings[i] === '{') {
      depth += 1;
      seen = true;
    } else if (typings[i] === '}') {
      depth -= 1;
      if (seen && depth === 0) return typings.slice(start, i + 1);
    }
  }
  throw new Error(`unclosed ${name}`);
}

function schemaLeaves(name: string): string[] {
  const block = schemaBlock(name);
  return [...block.matchAll(/^\s+([A-Za-z0-9]+)\??:\s*string;/gm)].map(item => item[1]).sort();
}

function countCalls(text: string, namespace: string, key: string): number {
  const plain = `$t('${namespace}.${key}')`;
  const named = `$t('${namespace}.${key}',`;
  return text.split(plain).length - 1 + text.split(named).length - 1;
}

describe('issue composer chrome copy', () => {
  it('locks composer, template, and editor leaves', () => {
    for (const [key, zhText, enText] of composer) {
      expect(zh.page.issueComposer[key as keyof typeof zh.page.issueComposer]).toBe(zhText);
      expect(en.page.issueComposer[key as keyof typeof en.page.issueComposer]).toBe(enText);
    }
    for (const [key, zhText, enText] of templateCopy) {
      expect(zh.page.issueTemplate[key as keyof typeof zh.page.issueTemplate]).toBe(zhText);
      expect(en.page.issueTemplate[key as keyof typeof en.page.issueTemplate]).toBe(enText);
    }
    for (const [key, zhText, enText] of editorCopy) {
      expect(zh.page.markdownEditor[key as keyof typeof zh.page.markdownEditor]).toBe(zhText);
      expect(en.page.markdownEditor[key as keyof typeof en.page.markdownEditor]).toBe(enText);
    }
    expect(leafKeys(zh.page.issueComposer).sort()).toEqual(composer.map(([key]) => key).sort());
    expect(leafKeys(en.page.issueComposer).sort()).toEqual(composer.map(([key]) => key).sort());
    expect(leafKeys(zh.page.issueTemplate).sort()).toEqual(templateCopy.map(([key]) => key).sort());
    expect(leafKeys(en.page.issueTemplate).sort()).toEqual(templateCopy.map(([key]) => key).sort());
    expect(leafKeys(zh.page.markdownEditor).sort()).toEqual(editorCopy.map(([key]) => key).sort());
    expect(leafKeys(en.page.markdownEditor).sort()).toEqual(editorCopy.map(([key]) => key).sort());
    expect(schemaLeaves('issueComposer')).toEqual(composer.map(([key]) => key).sort());
    expect(schemaLeaves('issueTemplate')).toEqual(templateCopy.map(([key]) => key).sort());
    expect(schemaLeaves('markdownEditor')).toEqual(editorCopy.map(([key]) => key).sort());
    expect(zh.page.issueForm.createTitle).toBe('创建问题');
    expect(en.page.issueForm.createTitle).toBe('Create issue');
    expect(en.page.shell.selectIssueTemplate).toBe('Choose an issue template');
    expect(en.page.shell.issueUploadHint).toBe('Uploads after the issue is created');
  });

  it('counts $t calls and drops the visible Chinese bindings', () => {
    for (const [key, times] of Object.entries(createCalls)) {
      expect(countCalls(create, 'page.issueComposer', key)).toBe(times);
    }
    for (const [key, times] of Object.entries(editCalls)) {
      expect(countCalls(edit, 'page.issueComposer', key)).toBe(times);
    }
    expect(countCalls(create, 'page.issueComposer', 'backToDetail')).toBe(0);
    expect(countCalls(create, 'page.issueComposer', 'attachments')).toBe(1);
    expect(countCalls(edit, 'page.issueComposer', 'attachments')).toBe(0);
    expect(countCalls(edit, 'page.issueComposer', 'useTemplate')).toBe(0);
    for (const [key, times] of Object.entries(editorCalls)) {
      expect(countCalls(editor, 'page.markdownEditor', key)).toBe(times);
    }
    expect(editor).toContain("$t('page.markdownEditor.characters', { n: content.length })");
    expect(editor).not.toContain(".replace('{n}'");
    expect(countCalls(selector, 'page.issueTemplate', 'intro')).toBe(1);
    expect(countCalls(selector, 'page.issueTemplate', 'empty')).toBe(1);
    expect(countCalls(selector, 'page.issueTemplate', 'footerHint')).toBe(1);
    expect(countCalls(selector, 'page.issueTemplate', 'cancel')).toBe(1);
    expect(countCalls(selector, 'page.issueTemplate', 'fieldTitle')).toBe(2);
    expect(countCalls(selector, 'page.issueTemplate', 'fieldDescription')).toBe(1);
    expect(countCalls(form, 'page.issueTemplate', 'contentPreview')).toBe(1);
    expect(countCalls(form, 'page.issueTemplate', 'previewHint')).toBe(1);
    expect(countCalls(form, 'page.issueTemplate', 'cancel')).toBe(1);
    expect(countCalls(form, 'page.issueForm', 'createTitle')).toBe(1);
    expect(countCalls(create, 'page.issueForm', 'createTitle')).toBe(2);
    expect(countCalls(create, 'page.shell', 'issueUploadHint')).toBe(1);
    expect(countCalls(selector, 'page.shell', 'selectIssueTemplate')).toBe(1);

    const gone = [
      /^\s+使用模板\s*$/m,
      /从模板创建问题/,
      /<NText strong>描述<\/NText>/,
      /placeholder="输入问题标题\.\.\."/,
      /placeholder="详细描述这个问题\.\.\."/,
      /<NText strong>预览<\/NText>/,
      /description="暂无描述内容"/,
      /title="确认退出"/,
      /content="你有未保存的更改，确定要退出吗？"/,
      /positive-text="放弃更改"/,
      /negative-text="继续编辑"/,
      /showPreview \? '编辑模式' : '预览模式'/,
      />未保存</
    ];
    for (const pattern of gone) {
      expect(create).not.toMatch(pattern);
      expect(edit).not.toMatch(pattern);
    }
    expect(create).not.toMatch(/^\s+返回列表 \(Esc\)\s*$/m);
    expect(edit).not.toMatch(/^\s+返回详情 \(Esc\)\s*$/m);
    expect(create).not.toMatch(/<NText strong>附件<\/NText>/);
    expect(create).not.toMatch(/^\s+添加附件\s*$/m);
    expect(editor).toContain('void locale.value;');
    expect(editor).toMatch(
      /const resolvedPlaceholder = computed\(\(\) => \{\n(?:[ \t]*\/\/ eslint-disable-next-line no-void[^\n]*\n)?[ \t]+void locale\.value;\n[ \t]+if \(props\.placeholder !== undefined\) return props\.placeholder;/
    );
    const nextLine = (editor.match(/eslint-disable-next-line no-void/g) ?? []).length;
    const blockOff = (editor.match(/\/\* eslint-disable no-void/g) ?? []).length;
    const blockOn = (editor.match(/eslint-enable no-void/g) ?? []).length;
    expect(nextLine + blockOff).toBe(1);
    expect(blockOff).toBe(blockOn);
  });

  it('keeps out-of-scope Chinese where this slice promised', () => {
    expect(create).toContain('请输入问题标题');
    expect(create).toContain('问题创建成功');
    expect(create).toContain('问题创建失败');
    expect(create).toContain('自定义字段（可选）');
    expect(edit).toContain('加载中...');
    expect(editor).toContain("insertText('**', '**', '粗体文本')");
    expect(editor).toContain("insertText('*', '*', '斜体文本')");
    expect(editor).toContain("insertText('`', '`', '代码')");
    expect(editor).toContain("insertText('\\n```\\n', '\\n```\\n', '代码块')");
    expect(editor).toContain("insertText('[', '](url)', '链接文本')");
    expect(editor).toContain("insertText('\\n- ', '', '列表项')");
    expect(editor).toContain("insertText('\\n> ', '', '引用文本')");
    expect(editor).toContain("insertText('\\n## ', '', '标题')");
    expect(editor).toContain("insertText('\\n- [ ] ', '', '待办事项')");
    const statusBtnStart = detail.indexOf("startEdit('status'");
    expect(detail.slice(statusBtnStart, detail.indexOf('</NButton>', statusBtnStart))).toContain('状态');
    const deleteIcon = detail.indexOf('icon-mdi-delete');
    expect(deleteIcon).toBeGreaterThan(-1);
    expect(detail.slice(deleteIcon, detail.indexOf('</NButton>', deleteIcon))).toContain('删除');
    expect(detail).toContain('取消\n                  </NButton>');
  });
});
