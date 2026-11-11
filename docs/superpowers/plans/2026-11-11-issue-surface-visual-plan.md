# 问题列表与新建表单局部视觉 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让问题列表和新建问题表单在明暗下共用一套局部表面令牌，补上实测不足 4.5 的按钮字色和新建标题焦点，同时保持 PR5 表布局、长标题换行和现有文案。

**Architecture:** 新建 `frontend/src/styles/issue-surface.css`，选择器只命中 `.issue-list-container` 和 `.issue-create-page`。两个页面各自 import 它。不改 `design-system.css`、`design-tokens.css`、`theme/settings.ts`、列宽函数、路由和文案。

**Tech Stack:** Vue 3 `<script setup>`、Naive UI、Vitest、`vue-tsc`、Vite 7。命令都在 `frontend/` 下执行。包管理器是 pnpm。不要用 `pnpm lint`，那个脚本带 `--fix`。

## Global Constraints

- 规格：`docs/superpowers/specs/2026-11-11-issue-surface-visual-design.md`。Yuri 已批准，按该文件 §11 执行。第一笔提交只含这两份文档。
- 起点 SHA 必须是 `75cc03e21e1ce44e9687e8d9fee9201a9df510a5`。未来 PR base 为 `cursor/residual-copy-design-658f`，正文含 `Depends on PR6`。禁止向该分支推送。禁止合并 PR6。
- 强调色保持 `#5e6ad2`。暗色焦点描边用现有 `--vk-accent` 暗色值 `#828fff`。不引入新的紫色，不改回 `#646cff`。
- 不改信息架构、路由、权限、API、字段集合、按钮顺序、toast/dialog 文案和时机、空态文案。
- 不改 `column-layout.ts`。375 表宽 349 与 768 表宽 522 的操作列保持不钉；1280 表宽 1034 保持 `sticky`。
- 单行行高保持约 41px。禁止 `max-height`、`line-clamp`、减小 `6px 12px` 单元格 padding。
- 「详情」「删除」盒尺寸保持 ≥ 48×28。
- `vue-tsc` 现有 29 条（`issue.d.ts(75,5) TS1357` 与 `components.d.ts` 242–255 行的 `TS1134`/`TS1005`）不得被修改或替换。
- 全库 ESLint 基线 190 errors / 680 warnings。不要求清零。两个 Vue 文件不得新增诊断。列表 script 里已有的 6 个 error 不要顺手修。
- 独立评审必须换人。实施者不能把自己的检查写成独立评审。
- 截图和测试日志放在仓库外。不要把合成预览脚本提交进仓库。

---

### Task 0: 批准后的分支

**Files:**

- 不改文件。

**Interfaces:**

- Consumes: 远程 `cursor/residual-copy-design-658f` 与 `main`。
- Produces: 一个新的本地分支，HEAD 仍等于 `75cc03e21e1ce44e9687e8d9fee9201a9df510a5`，直到 Task 1 提交。

- [ ] **Step 1: 核对远程没有前进**

```bash
cd /agent/repos/opentask
git fetch origin main cursor/residual-copy-design-658f
git rev-parse HEAD
git rev-parse origin/main
git rev-parse origin/cursor/residual-copy-design-658f
```

Expected: HEAD 与 PR6 远程都是 `75cc03e21e1ce44e9687e8d9fee9201a9df510a5`，`origin/main` 是 `22c8d8b3e3681e9d6b79d6e72fd200c2156cbd34`。任一不符就停止并报告，不要继续。

- [ ] **Step 2: 从精确 SHA 建新分支**

把下面的后缀换成执行时代理规则要求的后缀。不要使用 `cursor/residual-copy-design-658f`。

```bash
git checkout -b cursor/issue-surface-visual-SUFFIX 75cc03e21e1ce44e9687e8d9fee9201a9df510a5
git rev-parse HEAD
git status --porcelain
```

Expected: HEAD 仍是该 SHA，工作区干净。实际分支名是 `cursor/issue-surface-visual-ab12`。

- [ ] **Step 3: 先提交两份文档**

把规格和本计划写入 `docs/superpowers/specs/2026-11-11-issue-surface-visual-design.md` 与 `docs/superpowers/plans/2026-11-11-issue-surface-visual-plan.md`。这一笔只含这两个路径。然后才做 Task 1。

---

### Task 1: 局部令牌与对比测试

**Files:**

- Create: `frontend/src/styles/issue-surface.css`
- Test: `frontend/src/styles/__tests__/issue-surface.test.ts`

**Interfaces:**

- Consumes: 无。
- Produces: 自定义属性 `--issue-canvas`、`--issue-surface`、`--issue-surface-muted`、`--issue-ink`、`--issue-ink-secondary`、`--issue-line`、`--issue-accent`、`--issue-on-accent`、`--issue-danger`、`--issue-on-danger`、`--issue-focus`。它们定义在 `.issue-list-container, .issue-create-page` 与 `html.dark .issue-list-container, html.dark .issue-create-page` 上。

- [ ] **Step 1: 写会失败的测试**

创建 `frontend/src/styles/__tests__/issue-surface.test.ts`：

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';
import { describe, expect, it } from 'vitest';

function channel(hex: string, index: number) {
  const value = Number.parseInt(hex.slice(1 + index * 2, 3 + index * 2), 16) / 255;
  return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
}

function contrast(foreground: string, background: string) {
  const lum = (hex: string) => 0.2126 * channel(hex, 0) + 0.7152 * channel(hex, 1) + 0.0722 * channel(hex, 2);
  const lighter = Math.max(lum(foreground), lum(background));
  const darker = Math.min(lum(foreground), lum(background));
  return (lighter + 0.05) / (darker + 0.05);
}

function block(css: string, startPattern: RegExp) {
  const match = startPattern.exec(css);
  if (!match) throw new Error(`missing ${startPattern}`);
  const next = css.indexOf('\n}', match.index);
  return css.slice(match.index, next);
}

function token(section: string, name: string) {
  const match = section.match(new RegExp(`${name}:\\s*(#[0-9a-fA-F]{6})`));
  if (!match) throw new Error(`missing ${name}`);
  return match[1];
}

describe('issue surface tokens', () => {
  const css = readFileSync(resolve(process.cwd(), 'src/styles/issue-surface.css'), 'utf8');
  const light = block(css, /\.issue-list-container,\s*\.issue-create-page\s*\{/);
  const dark = block(css, /html\.dark \.issue-list-container,\s*html\.dark \.issue-create-page\s*\{/);

  it('keeps the current accent and pairs text against both surfaces', () => {
    expect(token(light, '--issue-accent')).toBe('#5e6ad2');
    expect(token(dark, '--issue-accent')).toBe('#5e6ad2');
    expect(token(light, '--issue-on-accent')).toBe('#ffffff');
    expect(token(dark, '--issue-on-accent')).toBe('#ffffff');
    expect(contrast('#ffffff', '#5e6ad2')).toBeGreaterThanOrEqual(4.5);
    expect(contrast(token(light, '--issue-ink-secondary'), '#ffffff')).toBeGreaterThanOrEqual(4.5);
    expect(contrast(token(dark, '--issue-ink-secondary'), '#0f1011')).toBeGreaterThanOrEqual(4.5);
    expect(contrast(token(light, '--issue-ink'), '#ffffff')).toBeGreaterThanOrEqual(4.5);
    expect(contrast(token(dark, '--issue-ink'), '#0f1011')).toBeGreaterThanOrEqual(4.5);
    expect(contrast('#ffffff', token(light, '--issue-danger'))).toBeGreaterThanOrEqual(4.5);
    expect(contrast('#ffffff', token(dark, '--issue-danger'))).toBeGreaterThanOrEqual(4.5);
    expect(token(light, '--issue-danger')).toBe('#cf1322');
    expect(css).toContain('outline: var(--issue-focus)');
    expect(css).toContain(':not(.n-button--disabled)');
    expect(css).toContain('--n-color-hover: #a8071a !important');
    expect(css).toContain('--n-color-pressed: #820014 !important');
    expect(css).toContain('.issue-create-page .markdown-textarea');
    expect(css).not.toContain('#646cff');
    expect(css).not.toContain('#f5222d');
    expect(css).not.toContain('--n-color-disabled');
    expect(css).not.toMatch(/background-color:\s*(var\(--issue-danger\)|#cf1322)/);
  });
});
```

- [ ] **Step 2: 确认失败**

```bash
pnpm exec vitest run src/styles/__tests__/issue-surface.test.ts
```

Expected: FAIL，`ENOENT` 或 `missing .issue-list-container`。不是修改 `column-layout` 或删掉现有断言造出来的失败。

- [ ] **Step 3: 写入令牌文件**

创建 `frontend/src/styles/issue-surface.css`：

```css
.issue-list-container,
.issue-create-page {
  --issue-canvas: #f5f6f6;
  --issue-surface: #ffffff;
  --issue-surface-muted: #f5f6f6;
  --issue-ink: #000000;
  --issue-ink-secondary: #62666d;
  --issue-line: #e6e7e8;
  --issue-accent: #5e6ad2;
  --issue-on-accent: #ffffff;
  --issue-danger: #cf1322;
  --issue-on-danger: #ffffff;
  --issue-focus: 2px solid #5e6ad2;
}

html.dark .issue-list-container,
html.dark .issue-create-page {
  --issue-canvas: #010102;
  --issue-surface: #0f1011;
  --issue-surface-muted: #141516;
  --issue-ink: #f7f8f8;
  --issue-ink-secondary: #d0d6e0;
  --issue-line: #23252a;
  --issue-accent: #5e6ad2;
  --issue-on-accent: #ffffff;
  --issue-danger: #cf1322;
  --issue-on-danger: #ffffff;
  --issue-focus: 2px solid #828fff;
}

.issue-create-page {
  background: var(--issue-canvas);
  color: var(--issue-ink);
}

.issue-create-page .page-header,
.issue-create-page .main-content {
  background: var(--issue-surface);
  color: var(--issue-ink);
}

.issue-create-page .page-header {
  border-bottom-color: var(--issue-line);
}

.issue-create-page .sidebar {
  background: var(--issue-surface-muted);
  border-left-color: var(--issue-line);
}

.issue-create-page .title-input {
  color: var(--issue-ink);
}

.issue-create-page .title-input::placeholder {
  color: var(--issue-ink-secondary);
}

.issue-create-page .title-input:focus,
.issue-create-page .title-input:focus-visible {
  outline: var(--issue-focus);
  outline-offset: 2px;
}

.issue-create-page .attachment-section,
.issue-create-page .preview-content {
  background: var(--issue-surface-muted);
  border-color: var(--issue-line);
}

.issue-create-page .pending-file-item {
  background: var(--issue-surface);
  border-color: var(--issue-line);
}

.issue-create-page .markdown-editor {
  background: var(--issue-surface);
  border-color: var(--issue-line);
}

.issue-create-page .toolbar,
.issue-create-page .editor-footer {
  background: var(--issue-surface-muted);
  border-color: var(--issue-line);
  color: var(--issue-ink);
}

.issue-create-page .markdown-textarea {
  color: var(--issue-ink);
  background: transparent;
}

.issue-create-page .markdown-textarea::placeholder {
  color: var(--issue-ink-secondary);
}

.issue-create-page .markdown-textarea:focus-visible {
  outline: var(--issue-focus);
  outline-offset: 2px;
}

.issue-create-page .preview-pane,
.issue-create-page .preview-pane .markdown-body {
  background: var(--issue-surface);
  color: var(--issue-ink);
}

html.dark .issue-list-container .n-button.n-button--primary-type:not(.n-button--disabled):not(.n-button--secondary):not(.n-button--tertiary):not(.n-button--quaternary):not(.n-button--ghost),
html.dark .issue-create-page .n-button.n-button--primary-type:not(.n-button--disabled):not(.n-button--secondary):not(.n-button--tertiary):not(.n-button--quaternary):not(.n-button--ghost) {
  --n-text-color: var(--issue-on-accent) !important;
  --n-text-color-hover: var(--issue-on-accent) !important;
  --n-text-color-pressed: var(--issue-on-accent) !important;
  --n-text-color-focus: var(--issue-on-accent) !important;
  color: var(--issue-on-accent);
}

.issue-list-container .n-button.n-button--error-type:not(.n-button--disabled) {
  --n-color: var(--issue-danger) !important;
  --n-color-hover: #a8071a !important;
  --n-color-pressed: #820014 !important;
  --n-color-focus: var(--issue-danger) !important;
  --n-text-color: var(--issue-on-danger) !important;
  --n-text-color-hover: var(--issue-on-danger) !important;
  --n-text-color-pressed: var(--issue-on-danger) !important;
  --n-text-color-focus: var(--issue-on-danger) !important;
  color: var(--issue-on-danger);
}

.issue-list-container .n-button.n-button--primary-type:not(.n-button--disabled):focus-visible,
.issue-list-container .n-button.n-button--error-type:not(.n-button--disabled):focus-visible,
.issue-create-page .n-button.n-button--primary-type:not(.n-button--disabled):focus-visible {
  outline: var(--issue-focus);
  outline-offset: 2px;
}
```

这里的选择器在页面 import 之前不会生效。Task 1 不改 Vue 文件。

- [ ] **Step 4: 确认通过，并确认旧测试没坏**

```bash
pnpm exec vitest run src/styles/__tests__/issue-surface.test.ts src/styles/__tests__/theme-contrast.test.ts src/views/issue/list/column-layout.test.ts
```

Expected: 三个文件都 PASS。`theme-contrast` 与 `column-layout` 在基线上本来就通过，这里只是回归。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/styles/issue-surface.css frontend/src/styles/__tests__/issue-surface.test.ts
git commit -m "$(cat <<'EOF'
feat(ui): add local tokens for the issue surfaces

EOF
)"
```

---

### Task 2: 新建表单接上局部令牌

**Files:**

- Modify: `frontend/src/views/issue/create/index.vue`（script 顶部 import；`<style scoped>` 第 682–751 行和第 764–838、916 行的颜色与焦点）
- Test: `frontend/src/views/issue/create/surface.test.ts`

**Interfaces:**

- Consumes: Task 1 的 `--issue-*` 与 `.issue-create-page .title-input:focus-visible`。
- Produces: 新建页 import 该 CSS；scoped 样式不再写死 `#f5f7fa`、`#fff`、`#e8eaed`、`#1a1a1a`、`#aaa`、`#f9fafb`；不再有 `outline: none`。模板和 script 逻辑不变。

- [ ] **Step 1: 写会失败的源码断言**

创建 `frontend/src/views/issue/create/surface.test.ts`：

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';
import { describe, expect, it } from 'vitest';

describe('issue create surface', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/views/issue/create/index.vue'), 'utf8');

  it('imports the local surface sheet and drops the light-only hex colors', () => {
    expect(source).toContain("import '@/styles/issue-surface.css';");
    expect(source).not.toMatch(/#(?:fff|ffffff|f5f7fa|e8eaed|1a1a1a|aaa|f9fafb)\b/i);
    expect(source).not.toContain('outline: none');
    expect(source).toContain('background: var(--issue-surface)');
    expect(source).toContain('color: var(--issue-ink)');
    expect(source).toContain('创建问题');
    expect(source).toContain('使用模板');
    expect(source).toContain('高级选项');
    expect(source).toContain('const advancedExpanded = ref(false)');
    expect(source).toContain('请输入问题标题');
    expect(source).toContain('问题创建成功');
    expect(source).toContain('问题创建失败');
    expect(source).toContain('关联任务 ID');
    expect(source).toContain('关联需求 ID');
    expect(source).toContain('负责人 ID');
  });
});
```

- [ ] **Step 2: 确认失败**

```bash
pnpm exec vitest run src/views/issue/create/surface.test.ts
```

Expected: FAIL，因为源码仍含 `#f5f7fa` 且没有 import。不要先删掉「创建问题」或高级选项来制造别的失败。

- [ ] **Step 3: 改新建页**

在 `<script setup>` 的 import 区末尾加：

```ts
import '@/styles/issue-surface.css';
```

把 `<style scoped>` 里这些声明换成变量，保留选择器和字号：

```css
.issue-create-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--issue-canvas);
  color: var(--issue-ink);
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: var(--issue-surface);
  border-bottom: 1px solid var(--issue-line);
  box-shadow: none;
  z-index: 10;
}

.main-content {
  flex: 1;
  padding: 32px 48px;
  overflow-y: auto;
  background: var(--issue-surface);
}

.title-input {
  width: 100%;
  font-size: 32px;
  font-weight: 600;
  line-height: 1.3;
  color: var(--issue-ink);
  border: none;
  background: transparent;
  font-family:
    -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans',
    'Helvetica Neue', sans-serif;
}

.title-input::placeholder {
  color: var(--issue-ink-secondary);
}

.attachment-section {
  margin-bottom: 24px;
  padding: 16px;
  background: var(--issue-surface-muted);
  border-radius: 8px;
  border: 1px solid var(--issue-line);
}

.pending-file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 6px;
  background: var(--issue-surface);
  border: 1px solid var(--issue-line);
}

.preview-content {
  padding: 20px;
  background: var(--issue-surface-muted);
  border-radius: 8px;
  border: 1px solid var(--issue-line);
  min-height: 200px;
}

.sidebar {
  width: 320px;
  padding: 24px;
  background: var(--issue-surface-muted);
  border-left: 1px solid var(--issue-line);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
```

删除原来的 `.title-input:focus { outline: none; }`。`@media (max-width: 1024px)` 与 `@media (max-width: 768px)` 保持，其中 `.sidebar { border-top: 1px solid #e8eaed; }` 改成 `border-top: 1px solid var(--issue-line);`。标题在 1024px 仍是 28px，在 768px 仍是 24px。不要改模板里的按钮顺序、字段和 `advancedExpanded`。

非 scoped 的 `issue-surface.css` 已经画了焦点轮廓。scoped 里不要再写 `outline: none`，否则后写的 scoped 规则会盖住它。

- [ ] **Step 4: 确认通过**

```bash
pnpm exec vitest run src/views/issue/create/surface.test.ts src/styles/__tests__/issue-surface.test.ts
pnpm exec eslint src/views/issue/create/index.vue
```

Expected: 两个 vitest 文件 PASS。ESLint 仍是基线的 17 个 warning、0 error，不新增。若 import 行触发 prettier，只改这一行的格式，不要 `--fix` 全文件。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/views/issue/create/index.vue frontend/src/views/issue/create/surface.test.ts
git commit -m "$(cat <<'EOF'
fix(ui): pair the issue create form with local surface tokens

EOF
)"
```

---

### Task 3: 列表按钮对比

**Files:**

- Modify: `frontend/src/views/issue/list/index.vue`（只加 import）
- Test: `frontend/src/views/issue/list/surface.test.ts`

**Interfaces:**

- Consumes: Task 1 里 `.issue-list-container .n-button.n-button--error-type:not(.n-button--disabled)` 与暗色启用主按钮字色规则。
- Produces: 列表 import 样式表。列定义、`handleDelete`、工具条、空态、`column-layout` 调用保持原样。

- [ ] **Step 1: 写会失败的测试**

创建 `frontend/src/views/issue/list/surface.test.ts`：

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';
import { describe, expect, it } from 'vitest';

describe('issue list surface', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/views/issue/list/index.vue'), 'utf8');

  it('loads the local sheet without changing the list contract', () => {
    expect(source).toContain("import '@/styles/issue-surface.css';");
    expect(source).toContain("default: () => '详情'");
    expect(source).toContain("default: () => '删除'");
    expect(source).toContain("title: '确认删除'");
    expect(source).toContain('positiveText: \'删除\'');
    expect(source).toContain('negativeText: \'取消\'');
    expect(source).toContain("window.$message?.success('问题删除成功')");
    expect(source).toContain('white-space: normal');
    expect(source).toContain('max-height: none');
    expect(source).toContain('scroll-x="1400"');
    expect(source).toContain('page.shell.noIssues');
    expect(source).toContain('page.shell.createIssue');
    expect(source).not.toContain('line-clamp');
  });
});
```

- [ ] **Step 2: 确认失败**

```bash
pnpm exec vitest run src/views/issue/list/surface.test.ts
```

Expected: FAIL，缺少 import。其余字符串现在就在文件里，不要为了让它们先失败而去删。

- [ ] **Step 3: 只加 import**

在 `frontend/src/views/issue/list/index.vue` 的 import 区末尾加：

```ts
import '@/styles/issue-surface.css';
```

不要改 `baseColumns`、`handleDelete`、模板工具条、`.issue-title-text`、`.n-data-table-td`。

- [ ] **Step 4: 确认通过**

```bash
pnpm exec vitest run src/views/issue/list/surface.test.ts src/views/issue/list/column-layout.test.ts src/views/issue/list/__tests__/type-labels.test.ts
pnpm exec eslint src/views/issue/list/index.vue
```

Expected: vitest PASS。ESLint 仍是基线的 6 errors 与列表原有 warnings，不新增。不要修那 6 个 error。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/views/issue/list/index.vue frontend/src/views/issue/list/surface.test.ts
git commit -m "$(cat <<'EOF'
fix(ui): raise issue list button contrast with local tokens

EOF
)"
```

---

### Task 4: 回归命令与计算样式验收

**Files:**

- 不改产品文件。证据写到仓库外 `/opt/cursor/artifacts/ui-round1/after/`。

**Interfaces:**

- Consumes: Task 1–3 的全部文件。
- Produces: 命令日志和一组新的合成截图。不产生提交。

- [ ] **Step 1: 跑前端回归**

```bash
cd frontend
pnpm exec vitest run
pnpm exec vue-tsc --noEmit --skipLibCheck
pnpm exec eslint src/views/issue/list/index.vue src/views/issue/create/index.vue src/views/issue/list/surface.test.ts src/views/issue/create/surface.test.ts src/styles/__tests__/issue-surface.test.ts
pnpm exec vite build --mode prod
git diff --stat origin/cursor/residual-copy-design-658f...HEAD
```

Expected:

- vitest 在基线 504 之外增加 Task 1–3 的新用例，全部 PASS。`column-layout` 三个用例仍 PASS。
- `vue-tsc` 退出码 2。把原始完整日志与 `/opt/cursor/artifacts/ui-round1/commands/vue-tsc.txt` 逐条比对，不以 29 或规格 §8 摘要代替。
- 两个 Vue 文件的 ESLint 诊断与基线逐条相同。三个新测试的基线是空文件，出现任何 error 或 warning 都算新增。不用 `pnpm lint`，不加 `--fix`。`issue-surface.css` 被 ESLint 忽略，不把“没有 CSS 诊断”当成 CSS 通过。
- build 退出码 0。
- diff 只含两份文档、`issue-surface.css`、三个新测试、`issue/create/index.vue`、`issue/list/index.vue`。若出现 backend、CLI、`design-system.css`、`settings.ts`、locale、router、`MarkdownEditor.vue`，停止。

- [ ] **Step 2: 用同一合成夹具重拍**

沿用本轮仓库外的 `/tmp/opentask-preview/mock-server.mjs` 与 `shoot.mjs`。Vite 仍用 `VITE_SERVICE_BASE_URL=http://127.0.0.1:7378`，端口 9527。浏览器继续丢弃非回环请求。数据集仍是 `SMOKEW-1`、`SMOKEW-2`、空列表。把输出目录改到 `/opt/cursor/artifacts/ui-round1/after/`。

必须量到：

- 单行行高 40–42px。长标题行的 `scrollHeight === clientHeight`，且大于 40px。
- 375 `clientWidth` 仍约 349，操作列不是 `sticky`，`scrollLeft` 0 与末端两张都在。768 约 522，同样不钉。1280 约 1034，操作列 `sticky`。1280 且 `scrollLeft = 0` 时，操作列仍盖住「负责人」末字。记下这个重叠，不要写成整表无遮挡。
- 「详情」「删除」宽 ≥ 48、高 ≥ 28。
- 暗色新建页量这些计算前景和背景：标题、标题占位符、`.markdown-textarea`、它的 placeholder、`.toolbar`、附件区文字、属性标签、启用主按钮、次按钮。页面上若有禁用或错误控件，也量。每一项文字 ≥ 4.5。父级表面修好后若编辑器仍不可读，且修法必须改 `MarkdownEditor.vue` 或其他白名单外文件，停止并写出最小 diff，不要宣称该页通过。
- 标题输入框必须用真实 Tab 到达并截图。`outline-style` 不是 `none`，`outline-width` ≥ 2px。对元素调用 `focus()` 不算。
- 启用主按钮和启用删除钮都量默认、hover、按下、`:focus-visible` 的前景和背景。文字 ≥ 4.5，焦点轮廓对相邻表面 ≥ 3。删除钮 hover 底与默认底不同，按下底与 hover 底不同。给删除钮临时加上 `n-button--disabled` 再量一次，确认没有被收成 `#cf1322` / 白字，量完移掉该类。
- 继续真实 Tab，直到「详情」和「删除」成为活动元素，并截图。基线没有做到这一步。
- 高级选项默认关闭。点开后三个 ID 字段可见。空标题点「创建问题」仍出现「请输入问题标题」，且不出现「问题创建成功」。
- 登录、详情、SLA、1280 侧栏再拍。它们应与 `/opt/cursor/artifacts/ui-round1/screenshots/` 的对应基线一致，除了同会话页签缓存。编辑页标题仍可以是 `route.issue_edit`。

若 Naive 的内联变量压过主按钮或删除按钮，只在 `issue-surface.css` 的上述窄选择器里加 `!important`。不要改 `themeColor` 或 `otherColor.error`，也不要写死 `background-color`。

- [ ] **Step 3: 不提交验收产物**

截图、日志留在仓库外。这个任务没有 commit。

---

### Task 5: 独立规格评审和代码评审

**Files:**

- 只在评审指出 Important 或 Critical 时，才改白名单内的文件，然后重新评审最终 HEAD。

**Interfaces:**

- Consumes: 最终 HEAD 的 diff、规格、计划和 after 证据。
- Produces: 两个与实施者不是同一人的结论，一份对规格，一份对代码。没有结论就不要向 Yuri 申报完成。评审工具不可用时报告阻塞，不许编造评审者。

- [ ] **Step 1: 换人看最终 HEAD**

评审者不能是写这些提交的人，也不能看到实施会话的历史。规格评审核对实现是否满足规格 §7 和 §11。代码评审核对 diff 质量。至少包括：

- 没有改 PR6 原分支，没有合并。
- 没有改 `column-layout.ts`、locale、router、`design-system.css`、`design-tokens.css`、`settings.ts`、详情、编辑、侧栏、`MarkdownEditor.vue`。
- 删除确认文案还在；空态仍只有「暂无问题」；高级选项默认关闭。
- 长标题没有 `line-clamp`；按钮盒没有缩小；1280 仍记录「负责人」末字重叠。
- 新测试是先失败再通过的，旧的 504 条不是被改红再改绿。
- `vue-tsc` 与原始日志逐条相同，不是总数碰巧相同。
- 启用四态、暗色编辑器、真实 Tab 都有计算数字或截图。没测的项写成未测。

- [ ] **Step 2: 处理结论后再开 PR**

Important 和 Critical 改完后，再让评审者看新的 HEAD。通过后才开 PR：base `cursor/residual-copy-design-658f`，正文写 `Depends on PR6` 和 `https://github.com/WayJ/opentask/pull/6`。只用允许的 PR 工具。工具拒绝时停止，不用 `gh` 或 API。不合并、不部署、不改 PR6。

---

## 自检

- 规格里的每一条目标都有任务：令牌 Task 1，新建表单 Task 2，列表按钮 Task 3，几何与对比回归 Task 4，独立评审 Task 5。侧栏零改动，所以没有侧栏任务。
- 计划里的属性名与 Task 1 CSS 一致，没有第二套名字。
- 没有留空项。旧测试被写成回归命令，没有先改坏再修。
- 36–40 与 41px、删除色与确认框、暗色主按钮与全局 `themeColor`、空态按钮，都按规格 §10 定死。
- Yuri 已批准按 §11 执行。第一笔是文档提交，然后是 Task 1、Task 2、Task 3。Task 4 不提交。Task 5 的评审通过后才开 PR。
