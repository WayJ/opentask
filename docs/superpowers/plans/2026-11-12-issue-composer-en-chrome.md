# 新建与编辑描述列英文铬 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把新建/编辑描述列、模板入口和 MarkdownEditor 工具栏接到 zh/en，不改提交、上传和模板套用行为。

**Architecture:** 新增 `page.issueComposer`、`page.issueTemplate`、`page.markdownEditor`，并同步 `App.I18n.Schema`。页面继续用 `@/locales` 的 `$t`。编辑器默认占位是先读 `locale.value` 的 computed。表单主按钮复用 `page.issueForm.createTitle`。

**Tech Stack:** Vue 3、vue-i18n、Naive UI、Vitest、Vue Test Utils、已有 `$t` 与 `App.I18n.Schema`，无新依赖。

## Global Constraints

- 本轮只交本地草稿。获批口令为「design ok，开写」。决策 A/B/C 未确认前不得实施。本计划按推荐案写；否决任一条，先改 design 与本 plan，再执行。
- 精确 base：`a1debf14bd754fcf34a788535c2a4d3a5684ed16`（PR15 tip）。不改写 PR6–15 已存提交或头。
- 后续仅普通隔离 clone（`.git` 为目录），不用 worktree。不写/reset MAIN `244c93e296a047cf138a880fa24d683b4be8203d` 或 PIN `250fc34af9c64e828aab706567b0430d3d74e452`。不碰已有 pid 服务。
- 不买额度，不 merge，不部署。未经再授权不 push、不开 PR。本轮不建产品分支、不改产品、不 TDD、不 commit。
- 英文页内铬 sentence case。新键进入 `App.I18n.Schema`。页面用 `$t`。不要把已有 `$t` 改成局部 `t()`。
- 脚本里调用 `$t` 的 computed，第一句必须是 `void locale.value;`，位于任何短路之前。`no-void` 只用 `eslint-disable-next-line` 盖住这一句，或紧贴该 computed 的 disable/enable 块。禁止文件级 `eslint-disable no-void`。
- 测试统计 `$t('…')` 调用点。字面缺失用正则。禁止 `not.toContain('描述')`、`('预览')`、`('附件')`、`('编辑')`、`('取消')`、`('标题')`。
- Vue Test Utils stub 同时覆盖 naive-ui 真实 name 与 `N*` 别名。不为测试修改产品组件的 `name` 或 `defineOptions`。
- 四门从 `frontend/` 跑：`pnpm exec vitest run`、`pnpm exec vite build --mode prod`（仓库外 config）、`pnpm exec vue-tsc --noEmit --skipLibCheck`、`pnpm exec eslint .`。对照当次干净 baseline。tsc/eslint 基线非 0 则保持，不得写成全绿，不得借用 PR15 的失败行号。
- 两笔提交：第一笔仅两份 docs；第二笔是 RED 测试与最小 GREEN 产品一起提交。不预安排第三笔。
- hook 只在新 clone：删除 pre-commit，保留 commit-msg，`core.hooksPath` 为空。不用 SKIP / `--no-verify`。EXIT 0 不是 hook 路径证明。若 `frontend/.git/COMMIT_EDITMSG` 或类似 ENOENT，原件落盘后 STOP，不重试。
- 不运行 `eslint --fix`。不改 `.env.prod` 正文；实施若要 prod build，只从已核来源拷贝，不把正文或键值写进证据。缺文件则 STOP，不用 `.env.example` 顶替。
- 决策 A：翻译 `MarkdownEditor` 本体。决策 B：包含选择器与模板表单。决策 C：退出四句用 design 第 3 节英文；`insertText` 种子保持中文。

### 白名单（14 路径）

- `docs/superpowers/specs/2026-11-12-issue-composer-en-chrome-design.md`
- `docs/superpowers/plans/2026-11-12-issue-composer-en-chrome.md`
- `frontend/src/locales/langs/zh-cn.ts`
- `frontend/src/locales/langs/en-us.ts`
- `frontend/src/typings/app.d.ts`
- `frontend/src/views/issue/create/index.vue`
- `frontend/src/views/issue/edit/index.vue`
- `frontend/src/views/issue/create/surface.test.ts`
- `frontend/src/locales/__tests__/issue-form-property-chrome.test.ts`
- `frontend/src/components/MarkdownEditor.vue`
- `frontend/src/components/IssueTemplateSelector.vue`
- `frontend/src/components/IssueTemplateForm.vue`
- `frontend/src/locales/__tests__/issue-composer-chrome.test.ts`
- `frontend/src/components/__tests__/markdown-editor-chrome.test.ts`

`issue-form-property-chrome.test.ts` 只改 110–111 行。`edit/surface.test.ts` 不在白名单。

---

### Task 0: 获批后隔离、当次基线、docs-only commit

**Files:** 仅上述两份 docs。**Consumes:** 精确 `a1debf14bd754fcf34a788535c2a4d3a5684ed16` 与已批的两份本地文件。**Produces:** 普通 clone 上的文档提交，以及仓库外 baseline 原件。

- [ ] **Step 1: 在实施环境建全新普通 clone**

下面的命令等获批后再执行。先确认目标不存在。不写/reset main `244c93e2` 或 pin `250fc34a`。

```bash
export TZ=Asia/Shanghai
export REPO=/tmp/cursor/opentask-issue-composer-en-chrome-clone
export EVIDENCE=/tmp/cursor/opentask-readonly/issue-composer-en-chrome-logs
test ! -e "$REPO" || exit 1
mkdir -p "$EVIDENCE"
git clone https://github.com/WayJ/opentask.git "$REPO"
cd "$REPO"
git switch --detach a1debf14bd754fcf34a788535c2a4d3a5684ed16
test -d .git || exit 1
test "$(git rev-parse HEAD)" = a1debf14bd754fcf34a788535c2a4d3a5684ed16 || exit 1
test -z "$(git status --porcelain)" || exit 1
test -z "$(git config --get core.hooksPath)" || exit 1
git switch -c cursor/issue-composer-en-chrome-<实施会话后缀>
cd "$REPO/frontend"
pnpm install --frozen-lockfile
cd "$REPO"
test -f .git/hooks/commit-msg || exit 1
rm -f .git/hooks/pre-commit
sha256sum .git/hooks/commit-msg > "$EVIDENCE/commit-msg.sha256"
git status --porcelain > "$EVIDENCE/checkout-porcelain.txt"
test ! -s "$EVIDENCE/checkout-porcelain.txt" || exit 1
```

hooks 缺失或位置不对就 STOP，不另装 verifier。`.env.prod` 只从已核来源拷贝；缺原件 STOP。不记录正文。依赖和 env 准备好之后再确认 tracked diff 为空。已有服务端口不动。Vite 只读 config 的 server port 用 `9571`，`strictPort: true`，`open: false`。

- [ ] **Step 2: 仓库外 config，先在干净 base 跑四门**

```bash
cd "$REPO/frontend"
node --input-type=module <<'JS'
import { writeFileSync } from 'node:fs';
const root = process.cwd();
const evidence = process.env.EVIDENCE;
writeFileSync(`${evidence}/vite.readonly.config.mjs`, `
import original from ${JSON.stringify(root + '/vite.config.ts')};
export default async env => {
  const resolved = typeof original === 'function' ? await original(env) : await original;
  return {
    ...resolved,
    root: ${JSON.stringify(root)},
    cacheDir: ${JSON.stringify(evidence + '/vite-cache')},
    build: { ...(resolved.build || {}), outDir: ${JSON.stringify(evidence + '/dist')} },
    server: { ...(resolved.server || {}), open: false, host: '127.0.0.1', port: 9571, strictPort: true }
  };
};
`);
JS
cat > "$EVIDENCE/run-gates.sh" <<'SH'
#!/usr/bin/env bash
set -u
phase="$1"
cd "$REPO/frontend" || exit 1
run() {
  name="$1"; shift
  dir="$EVIDENCE/$phase/$name"; mkdir -p "$dir"
  { printf 'CWD=%s\nTZ=%s\n' "$PWD" "$TZ"; printf 'COMMAND='; printf '%q ' "$@"; printf '\n'; git rev-parse HEAD; git status --porcelain; } > "$dir/meta.txt"
  "$@" > "$dir/stdout.txt" 2> "$dir/stderr.txt"
  rc=$?; printf 'EXIT=%s\n' "$rc" >> "$dir/meta.txt"
}
run vitest pnpm exec vitest run
run build pnpm exec vite build --mode prod --config "$EVIDENCE/vite.readonly.config.mjs"
run tsc pnpm exec vue-tsc --noEmit --skipLibCheck
run eslint pnpm exec eslint .
SH
bash "$EVIDENCE/run-gates.sh" baseline
```

baseline HEAD 必须仍是精确 base，tracked diff 空。vitest 与 build 必须 EXIT 0 才继续。tsc / eslint 非 0 则把诊断原样留下，不修范围外问题。build 前后比较 tracked diff 和生成文件 hash。意外改动就 STOP。

- [ ] **Step 3: 文档先行，恰好两文件提交**

把已批文件逐字节放入 docs，`cmp` 前后 sha256。拿不到已批原件就 STOP，不从未批草稿复刻。

```bash
cd "$REPO"
mkdir -p docs/superpowers/specs docs/superpowers/plans
cp /workspace/designs/issue-composer-en-chrome-spec/2026-11-12-issue-composer-en-chrome-design.md docs/superpowers/specs/
cp /workspace/designs/issue-composer-en-chrome-spec/2026-11-12-issue-composer-en-chrome.md docs/superpowers/plans/
cmp /workspace/designs/issue-composer-en-chrome-spec/2026-11-12-issue-composer-en-chrome-design.md docs/superpowers/specs/2026-11-12-issue-composer-en-chrome-design.md
cmp /workspace/designs/issue-composer-en-chrome-spec/2026-11-12-issue-composer-en-chrome.md docs/superpowers/plans/2026-11-12-issue-composer-en-chrome.md
git add docs/superpowers/specs/2026-11-12-issue-composer-en-chrome-design.md docs/superpowers/plans/2026-11-12-issue-composer-en-chrome.md
git diff --cached --name-only
git commit -m "docs: specify issue composer English chrome"
test "$(git rev-parse HEAD^)" = a1debf14bd754fcf34a788535c2a4d3a5684ed16 || exit 1
test -z "$(git status --porcelain)" || exit 1
```

`git diff --cached --name-only` 必须恰好是这两个路径。commit-msg hook 要留下。EXIT 0 之后把 `git rev-parse HEAD`、`git status --porcelain` 和 hook 文件是否仍在 `.git/hooks/commit-msg` 写入证据。遇到 `COMMIT_EDITMSG` ENOENT 立即 STOP。

### Task 1: tests-only RED（不改产品，不另强制 RED commit）

**Files:**

- Create: `frontend/src/locales/__tests__/issue-composer-chrome.test.ts`
- Create: `frontend/src/components/__tests__/markdown-editor-chrome.test.ts`
- Modify: `frontend/src/views/issue/create/surface.test.ts`（只换 18–19 行）
- Modify: `frontend/src/locales/__tests__/issue-form-property-chrome.test.ts`（只换 110–111 行）

**Interfaces:**

- Consumes: base 上没有这三个 namespace；create/edit/MarkdownEditor/选择器/表单仍是第 1 节那些中文绑定。
- Produces: 缺键、缺调用、中文绑定仍在时失败的测试。GREEN 之后这些断言转为锁定。

- [ ] **Step 1: 把 PR14 的两处冻结改成新键**

`create/surface.test.ts` 18–19 行换成：

```ts
    expect(source).toContain("$t('page.issueComposer.useTemplate')");
    expect(source).toContain("$t('page.issueComposer.useTemplateHint')");
    expect(source).not.toMatch(/^\s+使用模板\s*$/m);
    expect(source).not.toMatch(/从模板创建问题/);
```

18–19 行原来的 `toContain('使用模板')` 与 `toContain('从模板创建问题')` 删除。同文件 16–17、20–28 行不动，三条 toast 继续冻结。

`issue-form-property-chrome.test.ts` 110–111 行换成同一组四条断言（变量名是 `create`）。该文件其余行不动，包括 `createTitle` 次数为 2、详情顶栏按钮仍含「状态」。

- [ ] **Step 2: 写入源码合同**

`frontend/src/locales/__tests__/issue-composer-chrome.test.ts` 全文：

```ts
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
  ['intro', '选择一个模板来快速创建规范的问题（工作区模板）', 'Pick a template to create a well-formed issue (workspace templates)'],
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
  backToList: 1, unsaved: 1, useTemplate: 1, useTemplateHint: 1, previewMode: 1, editMode: 1,
  titlePlaceholder: 1, description: 1, markdownHint: 1, descriptionPlaceholder: 1, attachments: 1,
  addAttachment: 1, preview: 1, noDescription: 1, exitTitle: 1, exitContent: 1, exitDiscard: 1, exitKeep: 1
};
const editCalls: Record<string, number> = {
  backToDetail: 1, unsaved: 1, previewMode: 1, editMode: 1, titlePlaceholder: 1, description: 1,
  markdownHint: 1, descriptionPlaceholder: 1, preview: 1, noDescription: 1, exitTitle: 1,
  exitContent: 1, exitDiscard: 1, exitKeep: 1
};
const editorCalls: Record<string, number> = {
  boldTitle: 1, italicTitle: 1, inlineCodeTitle: 1, codeBlockTitle: 2, linkTitle: 2, bulletListTitle: 2,
  quoteTitle: 1, headingTitle: 2, taskListTitle: 2, edit: 1, preview: 1, syntaxHelp: 1, syntaxTitle: 1,
  glossBold: 1, glossItalic: 1, glossInlineCode: 1, glossQuote: 1, glossMention: 1, glossIssueRef: 1,
  defaultPlaceholder: 1, emptyPreview: 1, characters: 1, footerHint: 1
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
  const needle = `$t('${namespace}.${key}')`;
  return text.split(needle).length - 1;
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
    expect(editor).toContain("void locale.value;");
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
```

`no-void` 只允许一处：要么一行 `eslint-disable-next-line`，要么一对紧贴 computed 的 disable/enable。两处叠加，或只有 disable 没有 enable，测试失败。`insertText` 代码块那一行在源码里是反斜杠加 n 再加三个反引号；测试字符串里每个反斜杠要再写一遍。RED 若只因这条转义不一致失败，只改测试字符串，不改产品种子。

详情「取消」那条正则对着关注者按钮的换行（2026–2027 行）。不要写成 `not.toContain('取消')`。

- [ ] **Step 3: 写入编辑器挂载合同**

`frontend/src/components/__tests__/markdown-editor-chrome.test.ts`：

```ts
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
```

产品文件不要为了这个测试增加 `defineOptions`。GREEN 时把 `NEmpty` 与 `NPopover` 补进现有 naive-ui import，否则 Vitest 解析不到自动引入。

- [ ] **Step 4: 跑合同，确认 RED**

```bash
cd "$REPO/frontend"
pnpm exec vitest run src/locales/__tests__/issue-composer-chrome.test.ts src/components/__tests__/markdown-editor-chrome.test.ts src/views/issue/create/surface.test.ts src/locales/__tests__/issue-form-property-chrome.test.ts
```

期望：新合同因缺键或中文绑定仍在而 FAIL。`surface.test.ts` 与 PR14 测试在尚未接线时，对 `$t('page.issueComposer.useTemplate')` 的 `toContain` 也 FAIL。不要在这一步改产品。把 stdout/stderr/EXIT 存到证据目录。这一步不单独 commit。

### Task 2: locale、Schema、最小接线

**Files:**

- Modify: `frontend/src/locales/langs/zh-cn.ts`
- Modify: `frontend/src/locales/langs/en-us.ts`
- Modify: `frontend/src/typings/app.d.ts`
- Modify: `frontend/src/views/issue/create/index.vue`
- Modify: `frontend/src/views/issue/edit/index.vue`
- Modify: `frontend/src/components/MarkdownEditor.vue`
- Modify: `frontend/src/components/IssueTemplateSelector.vue`
- Modify: `frontend/src/components/IssueTemplateForm.vue`

**Interfaces:**

- Consumes: Task 1 的键名、次数和正则。
- Produces: 三棵对象与 design 第 3 节逐字相同；上述 Vue 的可见绑定改为 `$t`。

- [ ] **Step 1: 两份 locale 与 Schema**

在 `page.issueForm` 对象之后、同级加入三棵对象。zh 与 en 的键集合相同，值用 Task 1 数组，不要改写。`app.d.ts` 的 `page` 里加：

```ts
issueComposer: {
  backToList: string;
  backToDetail: string;
  unsaved: string;
  useTemplate: string;
  useTemplateHint: string;
  previewMode: string;
  editMode: string;
  titlePlaceholder: string;
  description: string;
  markdownHint: string;
  descriptionPlaceholder: string;
  attachments: string;
  addAttachment: string;
  preview: string;
  noDescription: string;
  exitTitle: string;
  exitContent: string;
  exitDiscard: string;
  exitKeep: string;
};
issueTemplate: {
  intro: string;
  empty: string;
  footerHint: string;
  cancel: string;
  fieldTitle: string;
  fieldDescription: string;
  contentPreview: string;
  previewHint: string;
};
markdownEditor: {
  boldTitle: string;
  italicTitle: string;
  inlineCodeTitle: string;
  codeBlockTitle: string;
  linkTitle: string;
  bulletListTitle: string;
  quoteTitle: string;
  headingTitle: string;
  taskListTitle: string;
  edit: string;
  preview: string;
  syntaxHelp: string;
  syntaxTitle: string;
  glossBold: string;
  glossItalic: string;
  glossInlineCode: string;
  glossQuote: string;
  glossMention: string;
  glossIssueRef: string;
  defaultPlaceholder: string;
  emptyPreview: string;
  characters: string;
  footerHint: string;
};
```

不要改 `page.shell.issueForm: string` 那一行。

- [ ] **Step 2: 新建页与编辑页绑定**

新建页头：

```vue
返回列表 (Esc)
```

换成 `{{ $t('page.issueComposer.backToList') }}`。未保存标签换成 `{{ $t('page.issueComposer.unsaved') }}`。使用模板按钮与 tooltip 换成 `useTemplate` / `useTemplateHint`。预览切换换成：

```vue
{{ showPreview ? $t('page.issueComposer.editMode') : $t('page.issueComposer.previewMode') }}
```

标题 input 使用 `:placeholder="$t('page.issueComposer.titlePlaceholder')"`。描述标题、提示、MarkdownEditor 的 placeholder、预览标题、空态、附件标题、添加附件，分别换成 `description`、`markdownHint`、`descriptionPlaceholder`、`preview`、`noDescription`、`attachments`、`addAttachment`。`page.shell.issueUploadHint` 那一行保持。退出对话框：

```vue
:title="$t('page.issueComposer.exitTitle')"
:content="$t('page.issueComposer.exitContent')"
:positive-text="$t('page.issueComposer.exitDiscard')"
:negative-text="$t('page.issueComposer.exitKeep')"
```

编辑页同样处理，返回 tooltip 用 `backToDetail`。不要给编辑页添附件区或模板按钮。不要改「加载中...」和「自定义字段（可选）」。toast 保持中文。

- [ ] **Step 3: MarkdownEditor**

import 改为：

```ts
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { NButton, NButtonGroup, NEmpty, NPopover, NSpace, NText } from 'naive-ui';
import { $t } from '@/locales';
```

`withDefaults` 去掉中文 placeholder 默认值，让缺省为 `undefined`。setup 里：

```ts
const { locale } = useI18n();
const resolvedPlaceholder = computed(() => {
  // eslint-disable-next-line no-void -- derived chrome must read locale.value before $t
  void locale.value;
  if (props.placeholder !== undefined) return props.placeholder;
  return $t('page.markdownEditor.defaultPlaceholder');
});
```

textarea 绑定 `:placeholder="resolvedPlaceholder"`。每个按钮 `:title` 用对应键。编辑/预览按钮文本：

```vue
{{ showPreview ? $t('page.markdownEditor.edit') : $t('page.markdownEditor.preview') }}
```

语法帮助按钮、弹出层 `h4`、11 条说明的破折号后半句，用第 3 节的键。代码样例节点保持原样。空预览 `:description="$t('page.markdownEditor.emptyPreview')"`。页脚：

```vue
<NText depth="3" style="font-size: 12px">{{ $t('page.markdownEditor.characters', { n: content.length }) }}</NText>
<NText depth="3" style="font-size: 12px">{{ $t('page.markdownEditor.footerHint') }}</NText>
```

`insertText(...)` 的第三个参数全部保持现在的中文。不要加 `defineOptions`。若 next-line 盖不住 `no-void`，改成紧贴这个 computed 的 disable/enable 块，块外立刻 enable。不要在文件顶部 disable。

- [ ] **Step 4: 选择器与表单**

选择器已有 `$t`。介绍、空态、页脚、取消换成 `page.issueTemplate` 对应键。`mapRow` 的回退字段：

```ts
label: $t('page.issueTemplate.fieldTitle'),
placeholder: $t('page.issueTemplate.fieldTitle'),
```

描述字段只把 `label` 换成 `fieldDescription`，placeholder 继续用 `row.payload?.description || ''`。从 `vue-i18n` 取 `locale`，在 `visible` 为真时 watch 它并调用现有 `load()`。卡标题继续 `page.shell.selectIssueTemplate`。

表单补 `import { $t } from '@/locales'`。`label="内容预览"` 改为 `:label="$t('page.issueTemplate.contentPreview')"`。提示句和取消按钮换成 `previewHint` 与 `cancel`。主按钮换成 `{{ $t('page.issueForm.createTitle') }}`。`请填写${field.label}` 保持。不要改 `constants/issueTemplates.ts`。

- [ ] **Step 5: 跑合同，确认 GREEN**

同一条 vitest 命令。期望这四份测试 PASS。失败就只补白名单内的绑定或键，不扩大页面。存 stdout/stderr/EXIT。

- [ ] **Step 6: 第二笔提交，测试与产品一起**

```bash
cd "$REPO"
git add \
  frontend/src/locales/langs/zh-cn.ts \
  frontend/src/locales/langs/en-us.ts \
  frontend/src/typings/app.d.ts \
  frontend/src/views/issue/create/index.vue \
  frontend/src/views/issue/edit/index.vue \
  frontend/src/views/issue/create/surface.test.ts \
  frontend/src/locales/__tests__/issue-form-property-chrome.test.ts \
  frontend/src/components/MarkdownEditor.vue \
  frontend/src/components/IssueTemplateSelector.vue \
  frontend/src/components/IssueTemplateForm.vue \
  frontend/src/locales/__tests__/issue-composer-chrome.test.ts \
  frontend/src/components/__tests__/markdown-editor-chrome.test.ts
git diff --cached --name-only
git commit -m "fix: localize issue composer chrome for English"
test -z "$(git status --porcelain)" || exit 1
```

cached 名单必须恰好是这 12 个产品/测试路径，不能带 docs（docs 已在第一笔）。hook 规则与 Task 0 相同。ENOENT 则 STOP。

### Task 3: 四门对照当次 baseline

**Files:** 无新路径。**Consumes:** 第二笔提交后的 HEAD。**Produces:** 仓库外四门原件。

- [ ] **Step 1: 再跑同一 `run-gates.sh final`**

vitest 与 build 必须 EXIT 0。tsc 与 eslint 的新增诊断必须是 0；基线里已有的诊断可以还在，把两边的诊断列在证据里，不要写成全绿。build 的 outDir 在 `$EVIDENCE/dist`，不把 dist 提交。tracked diff 必须仍空。

- [ ] **Step 2: 浏览器只在实施阶段、并且只在这刀表面**

en-US 与 zh-CN 浅色各看新建页（打开模板对话框，描述区和附件按钮可见）和编辑页。范围内文案应是第 3 节的句子。自定义字段卡、toast、详情顶栏不作为失败条件。浏览器不可用就在证据里写明，合同测试仍是验收依据。不要写 dual Grok Approve，除非另有独立 Approve 行。

### Task 4: STOP

获批后的实施到第二笔提交和四门证据为止。不 push，不开 PR，不 merge，不部署，不开始详情顶栏或设置页。第三笔只在审查指出 `resolvedPlaceholder` 在短路前没读 locale 时才补，本 plan 不预写那笔。

## 自检

- design 第 3 节 19 + 8 + 23 个键都在 Task 1 数组里，调用次数与 design 表一致。
- 决策 A/B/C 都写进了 Global Constraints，否决路径是先改文档。
- 白名单 14 条与 design 第 8 节相同。`issue-form-property-chrome.test.ts` 的改动限于 110–111 行。
- 没有 `TBD`。没有宽泛 `not.toContain('中文词')`。
- 插入种子、toast、详情顶栏、自定义字段卡、加载中，都有保持原样的断言或明确范围外句子。
- 实施命令都在获批之后。本草稿本身不执行这些命令。
