# 详情与编辑表面 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. 任务按顺序做。侧栏分支已经按有限范围验收，本计划不改那条分支。

**Goal:** 在精确提交 `088a34308cb0fe75a95f129432ee67b8f54067c3` 上补上已复验的 `route.issue_edit`，让编辑页用本页局部表面变量和可见焦点环，并只在暗色详情描述里覆盖正文、行内代码和链接。

**Architecture:** 标题键进两个 locale 文件。编辑页的变量和 `:deep` 覆盖写在 `views/issue/edit/index.vue`。详情描述的暗色覆盖写在 `views/issue/detail/index.vue` 的 `.description-content` 下。共享的 `MarkdownRenderer.vue`、`MarkdownEditor.vue` 和 `issue-surface.css` 不改。围栏代码块保持浅色。实施时测量实际出现的 token 类。

**Tech Stack:** Vue 3、vue-i18n 消息表、Vitest 源码合同、Playwright 真实 Tab、仓库外合成 API `127.0.0.1:7377`。

## Global Constraints

- 基线提交只允许 `088a34308cb0fe75a95f129432ee67b8f54067c3`。分支从该提交另开，不从侧栏 HEAD 开。
- 未来 PR base 是 `cursor/issue-surface-visual-ab12`，正文写 Depends on PR7。本轮停在开 PR 之前。
- diff 不得包含 `frontend/src/layouts/modules/global-sider/`、`issue-surface.css`、`MarkdownRenderer.vue`、`MarkdownEditor.vue`、列表页、新建页或路由文件。
- 只新增一对键：中文 `issue_edit` = `编辑问题`，英文 `issue_edit` = `Edit Issue`。页内硬编码「编辑问题」保持中文。
- 编辑页强调色保持 `#5e6ad2`。暗色焦点环保持 `#828fff`。变量数值与现有 `--issue-*` 相同，定义在 `.issue-edit-page` 本地。
- 高级选项默认 `advancedExpanded = false`。保存仍走 `issueStore.updateIssue` 和「问题更新成功」，然后进入 `/issue/detail?id=`。空标题仍是「请输入问题标题」，不发请求。
- 详情主操作顺序不改。描述覆盖不作用于 `.comment-text`。
- 围栏代码可以保持浅色。`.hljs-built_in` 与 `.hljs-symbol` 没有节点就写 `absent`，不算通过。
- 每个新行为的失败测试必须先于对应产品改动。完整 stdout、stderr、退出码、当时 SHA 和工作区 diff 记在当次日志里。不变量已经成立的断言若失败，停止，不把它写成预期红。
- 写选择器进产品文件之前，用本仓库 `@vue/compiler-sfc` 3.5.44 的 `compileStyle` 保存实际 stdout 和返回 CSS。
- 暗色是否生效以浏览器计算样式为准。
- 不用 `eslint --fix`，不格式化整个仓库。每次审查、探测和测试前后记录 `git status --porcelain`。出现白名单以外的已跟踪改动就停止，不悄悄还原。
- typecheck 29 条、退出码 2，以及 ESLint 非零退出，在最终记录里写成失败，不得报成全绿。
- 文档路径恰好 2 个。产品与测试路径恰好 7 个。合计 9 个。

---

### Task 0: 文档入库

**Files:**
- Create: `docs/superpowers/specs/2026-11-12-issue-detail-edit-design.md`
- Create: `docs/superpowers/plans/2026-11-12-issue-detail-edit-surface.md`

- [ ] **Step 1: 核对暂存数量后提交**

`git diff --name-only --cached` 恰好是上面 2 行。出现侧栏或产品文件就停止。提交消息 `docs: add issue detail and edit surface spec`。

---

### Task 1: 标题键

**Files:**
- Modify: `frontend/src/locales/__tests__/route-labels.test.ts`
- Modify: `frontend/src/locales/langs/zh-cn.ts`
- Modify: `frontend/src/locales/langs/en-us.ts`

- [ ] **Step 1: 在 `uses the approved object names` 末尾追加**

```ts
expect(zh.route.issue_edit).toBe('编辑问题');
expect(en.route.issue_edit).toBe('Edit Issue');
expect(zh.route.issue_edit).not.toBe('route.issue_edit');
expect(en.route.issue_edit).not.toBe('route.issue_edit');
```

不改该文件里已经存在的其他期望。

- [ ] **Step 2: 运行并保存当次失败**

在 `frontend/` 运行 `pnpm exec vitest run src/locales/__tests__/route-labels.test.ts`。预期失败，因为 `zh.route.issue_edit` 现在是 `undefined`。保存完整 stdout、stderr 和退出码。

- [ ] **Step 3: 只加这一对键**

中文紧跟 `issue_detail`：`issue_edit: '编辑问题'`。英文紧跟 `issue_detail: 'Issue Detail'`：`issue_edit: 'Edit Issue'`。不把编辑页里的 `<NText>编辑问题</NText>` 改成 `$t`。

- [ ] **Step 4: 再跑到通过并提交**

消息：`feat: add issue edit route title`。暂存恰好是这三个 locale 路径。

---

### Task 2: 编辑页表面的失败合同

**Files:**
- Create: `frontend/src/views/issue/edit/surface.test.ts`

合同断言编辑页源码含 `.issue-edit-page` 上的 `--issue-canvas: #f5f6f6`、`html.dark .issue-edit-page` 上的 `--issue-canvas: #010102`、两套 `--issue-focus`、`outline: var(--issue-focus)` 和 `outline-offset: 2px`，以及 `const advancedExpanded = ref(false)`。`issue-surface.css` 和 `MarkdownRenderer.vue` 不得出现 `.issue-edit-page`。共享文件那条在基线上已经成立；它若失败，说明工作树已被改过，停止。

- [ ] **Step 1: 写测试并保存当次失败**

`pnpm exec vitest run src/views/issue/edit/surface.test.ts`。预期因编辑页还没有 `--issue-canvas: #f5f6f6` 而失败。字符串断言不能代替浏览器计算样式。

---

### Task 3: 编辑页局部表面和焦点

**Files:**
- Modify: `frontend/src/views/issue/edit/index.vue`

- [ ] **Step 1: 先跑 compiler-sfc，再写选择器**

保存 `compileStyle({ scoped: true })` 对候选选择器返回的 CSS。禁止 `:global(html.dark) .issue-edit-page`。

- [ ] **Step 2: 写入规格第 3.2 节的成对变量和后代规则**

替换页背景、顶栏、主栏、属性栏、标题、placeholder 和 768px 分隔线上的写死颜色。给标题和 `textarea.markdown-textarea` 加 `:focus-visible`。预览正文只覆盖 `.preview-content` 下的 `.markdown-body`。不给 `pre` 或 `.hljs` 设暗色背景。

- [ ] **Step 3: 选择器焦点等真实 Tab 测量**

测量写到仓库外。已有可见环就不加规则。三处都没有才加 `.sidebar` 下的 `:focus-within` 环，并另一次提交，消息 `feat: show edit page select focus`。

- [ ] **Step 4: 合同通过后提交**

消息：`feat: use local tokens on the issue edit page`。暂存恰好是 `index.vue` 和 `surface.test.ts`。

---

### Task 4: 详情描述的暗色覆盖

**Files:**
- Create: `frontend/src/views/issue/detail/description-surface.test.ts`
- Modify: `frontend/src/views/issue/detail/index.vue`

- [ ] **Step 1: 先写失败测试**

断言详情源码含 `html.dark .issue-detail-container .description-content :deep(.markdown-body)`、`background-color: var(--color-bg-primary);`、`color: #828fff;`、`background-color: #23252a;`。断言没有 `html.dark .issue-detail-container .comment-text :deep(.markdown-body)`，共享渲染器不含 `.issue-detail-container`。

- [ ] **Step 2: 保存当次失败，再按规格第 3.3 节追加样式**

不改评论的 `white-space: normal`。不写 `pre` 或 `.hljs` 背景。

- [ ] **Step 3: 通过后单独提交**

消息：`feat: theme issue detail description prose in dark mode`。这一提交可以单独回退，而不带回标题键和编辑页表面。

---

### Task 5: 浏览器与最终命令

不提交探测脚本。合成环回只打 `127.0.0.1`。

- [ ] **Step 1: 标题、真实 Tab、高级选项、两条保存路径**

中文标题是 `编辑问题 - OpenTask`，英文是 `Edit Issue - OpenTask`，页内标题始终是「编辑问题」。从标题 Tab 到描述 textarea 和「高级选项」。Shift+Tab 第一步是「保存更改」，环仍含 `rgb(94, 106, 210)`。亮色焦点环是 `2px solid rgb(94, 106, 210)`，暗色是 `2px solid rgb(130, 143, 255)`，偏移 `2px`。

详情从 `body` Tab，最多 80 次，记录里要出现「编辑」。80 次未出现写成 `inconclusive`，不写成不可达。

高级选项首次不渲染三个 ID 输入框。展开、填入 `task-syn` / `req-syn` / `user-syn`、收起、再展开，值还在。默认代码仍是 `ref(false)`。

空标题保存不更新 PUT 记录，URL 仍在编辑页，消息是「请输入问题标题」。恢复标题「合成保存标题」后，带高级字段的保存 JSON 含原描述、`type: bug`、`priority: medium` 和三个 ID，然后出现「问题更新成功」并进入详情。另一次不展开高级选项的保存，JSON 里不得出现那三个未填写的 ID。

- [ ] **Step 2: 视口、暗色表面、代码岛**

375、768、1280，高度 800 和 480，明暗都采样。480 若没有容器 `scrollHeight > clientHeight`，再量 320 并写明。暗色编辑页背景应分别来自 `#010102`、`#0f1011`、`#141516`、`#0f1011`。暗色详情段落、链接、行内 code 用叠色链重算，对比至少 4.5。记录每一个实际存在的 `.hljs-*`。评论区 `.markdown-body` 仍是共享渲染器的浅色。

- [ ] **Step 3: 同一 FINAL SHA 上的完整命令**

工作树干净之后，在 `frontend/` 一次跑完 `pnpm exec vitest run`、`pnpm exec vue-tsc --noEmit --skipLibCheck`、`pnpm exec eslint .`、`pnpm exec vite build --mode prod`。`set +e`，每份日志写上同一个 SHA 和退出码。vue-tsc 与基线 29 条逐条对照。eslint 不加 `--fix`，与当次 `088a343` 基线逐条对照，非零记为失败。

- [ ] **Step 4: 两个只读 Grok 复审，然后停止**

一个对照本规格。一个只读最终 9 个路径的已提交 blob。没有 Critical 或 Important 才算这道门通过。通过之后仍不开 PR，也不合并、不部署。
