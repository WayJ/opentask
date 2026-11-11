# 详情与编辑表面设计规格

日期：2026-11-12。基线 SHA：`088a34308cb0fe75a95f129432ee67b8f54067c3`。  
本文件只覆盖详情与编辑。侧栏密度是另一条已按有限范围验收的切片，不在本 diff 里，也不在本规格的实施范围内。

材料是已批准的组合设计第 5、6、10.2 节，以及详情/编辑计划。数值与 `frontend/src/styles/issue-surface.css` 里现有的 `--issue-*` 相同。那个文件本身不改。

## 1. 范围

只做两件事：

- 补一对已复验仍缺的 `route.issue_edit`。
- 编辑页使用本页局部表面变量和可见焦点环；暗色详情只覆盖 `.description-content` 里的正文、行内代码和链接。

不改字段集合、高级选项默认关闭、主按钮位置、message 渠道、保存后进入详情的路由。不改 `MarkdownRenderer.vue`、`MarkdownEditor.vue`、`issue-surface.css`、列表页、新建页、路由表、侧栏。围栏代码块可以保持浅色。评论区不改。

未来 PR 的 base 是 `cursor/issue-surface-visual-ab12`，正文写 Depends on PR7。本分支从精确 `088a343` 另开，不包含侧栏提交。

## 2. 已复验事实

`zh-cn.ts` 与 `en-us.ts` 的 `route` 段有 `issue_detail` 和 `issue_create`，没有 `issue_edit`。路由 meta 已经是 `i18nKey: 'route.issue_edit'`。在 `/issue/edit?id=issue-long` 上，中文和英文的 `document.title` 与应用内页签都是 `route.issue_edit`。页内 `NText` 是硬编码「编辑问题」，英文界面也仍是这四个字。只补标题键。页内标题不改成 `$t`。

编辑页根是 `.issue-edit-page`。作者样式把页背景写成 `#f5f7fa`，主栏和标题没有暗色成对变量。`advancedExpanded` 默认 `false`。空标题提示「请输入问题标题」且不发请求。有效保存走 `issueStore.updateIssue`，消息是「问题更新成功」，然后进入 `/issue/detail?id=`。未定义的 `task_id`、`requirement_id`、`assignee_id` 不出现在 JSON 里。

标题 `input` 和描述 `textarea` 的焦点 `outline` 与 `box-shadow` 都不是可见环。保存按钮已有 `2px solid rgb(94, 106, 210)`。类型、优先级、项目的选择器祖先是否另有背景变化，基线没有记录，所以不能预先断定必须加环或已经有环。

暗色编辑页实测表面分裂：页底 `rgb(1, 1, 2)`，主栏白，属性栏 `rgb(245, 247, 250)`，属性卡片 `rgb(24, 24, 28)`。

暗色详情的标题和操作对比已经过线。描述来自共享渲染器的浅色 `.markdown-body`：背景白，段落 `rgb(36, 41, 47)`，链接 `rgb(9, 105, 218)`，行内 code 同段落色。围栏 `pre.hljs` 是浅色。样例里有 `.hljs-keyword`。`.hljs-built_in` 和 `.hljs-symbol` 没有节点，算未测。这些浅色岛上的对比不能写成暗色描述已经验收。

详情主操作顺序保持：编辑、复制问题、设为子项…、状态、删除、关注、收藏到侧栏、复制分支名。从 `body` 起的前 16 次 Tab 没有走到「编辑」，那只说明前缀不够，不能写成 1280 不可达。

## 3. 批准的做法

### 3.1 文案

紧跟现有 `issue_detail`：

- `zh-cn.ts`：`issue_edit: '编辑问题'`
- `en-us.ts`：`issue_edit: 'Edit Issue'`

不加别的键。

### 3.2 编辑页局部表面

在 `.issue-edit-page` 上定义，亮色与暗色成对，数值与列表/新建页已有 `--issue-*` 相同：

| 变量 | 亮色 | 暗色 |
|---|---|---|
| `--issue-canvas` | `#f5f6f6` | `#010102` |
| `--issue-surface` | `#ffffff` | `#0f1011` |
| `--issue-surface-muted` | `#f5f6f6` | `#141516` |
| `--issue-ink` | `#000000` | `#f7f8f8` |
| `--issue-ink-secondary` | `#62666d` | `#d0d6e0` |
| `--issue-line` | `#e6e7e8` | `#23252a` |
| `--issue-accent` | `#5e6ad2` | `#5e6ad2` |
| `--issue-on-accent` | `#ffffff` | `#ffffff` |
| `--issue-focus` | `2px solid #5e6ad2` | `2px solid #828fff` |

页背景用画布色。顶栏和主栏用主表面。属性栏用弱表面。卡片用主表面，不和弱表面涂成同一个色。标题和 placeholder 用字色与次级字色。强调色按钮仍是 `#5e6ad2`。

删掉 `.title-input:focus { outline: none; }`。未聚焦时可以保持 `outline: none`。标题和 `textarea.markdown-textarea` 的 `:focus-visible` 使用 `outline: var(--issue-focus)` 与 `outline-offset: 2px`。预览里的 `.markdown-body`、链接和行内 code 只在 `.issue-edit-page .preview-content` 下覆盖。不给 `pre`、`pre code` 或 `.hljs` 设暗色背景。

选择器焦点：实施时用真实 Tab 走到类型、优先级、关联项目，读取 `activeElement` 及其祖先的 `outline`、`box-shadow`、`background-color`。某一层已经有可见环就不再加规则。三处都没有可见环时，才在 `.issue-edit-page .sidebar` 下为 `.n-base-selection:focus-within` 和 `.n-input:focus-within` 加本页焦点环。

### 3.3 暗色详情描述

只在 `html.dark` 且只在 `.issue-detail-container .description-content` 下：

- `.markdown-body` 的背景是 `var(--color-bg-primary)`，字色是 `var(--color-text-primary)`。
- `h6` 与 `blockquote` 用 `var(--color-text-secondary)`。
- 链接 `#828fff`。
- 行内 `code:not([lang]):not([class])` 用 `var(--color-text-primary)` 和背景 `#23252a`。

不写 `pre`、`.hljs`、`pre code` 的背景。不改 `.comment-text :deep(.markdown-body)` 现有的 `white-space: normal`。评论区 `.markdown-body` 应仍是共享渲染器的浅色。

围栏代码保持浅色是允许的。条件是这次样例里实际出现的每个 `.hljs-*` 都重新测过。没有节点的类写 `absent`，不算通过。`.hljs-keyword` 若低于 4.5，停止并报告，不把代码岛改成暗色来凑对比。

### 3.4 选择器必须先由本仓库编译器证明

写任何选择器进产品文件之前，用已安装的 `@vue/compiler-sfc` 3.5.44 的 `compileStyle({ scoped: true })` 跑当前脚本，保存 stdout 和返回的 CSS。计划里写过的编译结果不能代替这次输出。

候选写法：

- `html.dark .issue-edit-page` 应把 `data-v` 加在 `.issue-edit-page` 上，而不是加在 `html` 上。编辑页根就是这个类。
- `html.dark .issue-detail-container .description-content :deep(.markdown-body)` 应把 `data-v` 留在 `.description-content` 上，`.markdown-body` 不再要求 `data-v`。
- `:global(html.dark) .issue-edit-page` 会丢掉后面的类，禁止使用。

源码里出现这些字符不等于暗色生效。通过条件是浏览器计算样式：`html.dark` 下 `.issue-edit-page` 的 `--issue-canvas` 为 `#010102`，`.main-content` 背景为 `#0f1011`，`.sidebar` 背景为 `#141516`，卡片背景为 `#0f1011`。若计算值仍是改前的颜色，把暗色规则移到同一 SFC 的第二段不带 `scoped` 的 `<style>`，选择器仍以本页根类开头，然后再读一次计算样式。

## 4. 文件

文档恰好 2 个：本文件，以及 `docs/superpowers/plans/2026-11-12-issue-detail-edit-surface.md`。

产品与测试恰好 7 个：

- `frontend/src/locales/langs/zh-cn.ts`
- `frontend/src/locales/langs/en-us.ts`
- `frontend/src/locales/__tests__/route-labels.test.ts`
- `frontend/src/views/issue/edit/index.vue`
- `frontend/src/views/issue/edit/surface.test.ts`
- `frontend/src/views/issue/detail/index.vue`
- `frontend/src/views/issue/detail/description-surface.test.ts`

## 5. 验收

- 中文文档标题和页签是「编辑问题」，英文是「Edit Issue」。页内 `NText` 仍是「编辑问题」。
- 编辑暗色主栏、属性栏、卡片来自同一组变量，不再是三种互不相关的底色。强调色仍是 `#5e6ad2`。
- 标题和描述 textarea 在真实 Tab / Shift+Tab 下有可见焦点环。保存按钮现有环还在。
- 高级选项默认关闭。展开后填写的三个值在收起再展开后还在。
- 空标题不发 PUT，并出现「请输入问题标题」。普通保存和展开高级选项后的保存都保留原描述、类型、优先级；只有展开并填写后，JSON 才带那三个 ID。成功消息仍是「问题更新成功」，并进入详情。
- 暗色描述的段落、链接、行内 code 对比至少 4.5，背景是详情暗色表面。围栏代码可以仍是浅色。无节点的 token 类保持未测。
- 375、768、1280，明暗，以及 480 低高度都要采样。长标题在详情和编辑都要看。
- `vue-tsc` 的 29 条和退出码 2、ESLint 的非零退出，都记成失败，不报成全绿。生产构建退出码 0 不能代替这两项。

## 6. 本规格不关闭

1280 列表 sticky、明色列表叠色、disabled 原生语义、CI 全绿，以及更早 SHA 上的 6 个错误 / 25 个警告原文，都不在本切片。`.hljs-built_in` 与 `.hljs-symbol` 若仍无节点，继续算未测。
