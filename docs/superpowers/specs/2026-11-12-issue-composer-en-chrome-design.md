# 新建与编辑描述列英文铬

第 4 刀 design 草稿，送 Yuri 代审；没有审批结论。未来 repo 路径：`docs/superpowers/specs/2026-11-12-issue-composer-en-chrome-design.md`。本文与 plan 是一组。盘点报告在同次 artifacts 的 `inventory-REPORT.md`，不入库。

## 1. 问题与证据

PR15 已限定交付。本刀起点为 `a1debf14bd754fcf34a788535c2a4d3a5684ed16`。`en-us.ts` 无汉字。`fallbackLocale: 'en'` 与消息表 `'en-US'` 不是同一张表，缺键不会显示中文。en-US 下的中文来自写死文案。

PR14 已把新建/编辑的页内标题、主按钮和属性卡接到 `page.issueForm`。同一屏留下的描述列和页头在 `a1debf14` 上仍是中文（行号以该 SHA 为准）：

- 新建 `create/index.vue`：405 返回列表 (Esc)，410 未保存，422 使用模板，425 从模板创建问题，438 编辑模式/预览模式，461 输入问题标题...，472–477 描述、Markdown 提示、详细描述这个问题...，497/535 附件与添加附件，543/547 预览与暂无描述内容，700–703 退出四句。486「自定义字段（可选）」不在本刀。
- 编辑 `edit/index.vue`：279 加载中...不在本刀。291 返回详情 (Esc)，296 未保存，311 预览切换，335/346/347/351 标题占位与描述区，360/364 预览与空态，503–506 退出四句。编辑页没有模板按钮和附件区。
- `MarkdownEditor.vue` 91–213 行工具栏、语法帮助、空预览、字符数、页脚仍是中文。14 行默认占位是「支持 Markdown 语法...」。
- 选择器 104/109/137/139 与表单 139/142/154/155 仍是中文。卡标题已经是 `page.shell.selectIssueTemplate`（Choose an issue template），本刀不改这句。

PR14 银测试把范围外的两句冻在 create 源码上：`issue-form-property-chrome.test.ts` 110–111 行，`create/surface.test.ts` 18–19 行。本刀要改这两处断言，其余 PR14 冻结保持，包括 create 上 `page.issueForm.createTitle` 仍恰好 2 次、三条创建 toast、详情顶栏 `startEdit('status'` 按钮仍含「状态」。

列表语法帮助已经是 `page.issueList.toolbar.syntaxHelp` 与 `page.issueList.syntax.*`。详情顶栏、关注者「取消」、侧栏 FavoritesNav、自定义字段、设置四页不在本刀。

## 2. 方案与推荐

A（推荐）：新建两个与 `page.issueForm` 并列的对象 `page.issueComposer`、`page.issueTemplate`，编辑器另建 `page.markdownEditor`。页级新调用用已有的 `@/locales` `$t`。编辑器默认占位放进先读 `locale.value` 的 computed。选择器回退字段在 `mapRow` 里 `$t`，对话框打开时 `watch(locale)` 再 `load()`。表单主按钮复用 `page.issueForm.createTitle`，不新造「Create issue」。

B：把这些键塞进 `page.issueForm`。少一个 namespace，但把属性卡和描述列焊在一起，PR14 的键集合测试也要重开。不采用。

C：编辑器复用 `page.issueList.toolbar.syntaxHelp`，退出框复用 `common`。列表「语法帮助」和编辑器「语法帮助」不是同一块 UI，common 也没有这四句退出文案。不采用。

选 A。已有 `$t('page.issueForm.*')`、`$t('page.shell.issueUploadHint')`、`$t('page.shell.selectIssueTemplate')` 不重写。编辑页已经 `import { $t } from '@/locales'`，不要改成别的绑定。模板表单今天没有这份 import，实施时补上。不要把既有 `$t` 改成局部 `t()`。

`resolvedPlaceholder` 是本刀唯一新增的、在脚本里调用 `$t` 的 computed。函数体第一条语句是 `void locale.value;`，位于 `if (props.placeholder !== undefined)` 之前。这条语句上一行可以是 `eslint-disable-next-line no-void`。eslint `no-void` 只盖这一句，或改用紧贴该 computed 的 disable/enable 块。禁止文件级 disable，也禁止两套 disable 叠在一起。模板里的 `$t` 不包 computed。

## 3. 锁定文案

英文 sentence case。中文逐字保留，包括 ASCII `...`、全角括号、间隔号 `•`。不改 `route.issue_create` / `route.issue_edit`。不改 `page.issueForm.createTitle` 的值（创建问题 / Create issue）。

### `page.issueComposer`（19 键）

| 键 | zh-CN | en-US | create 调用 | edit 调用 |
|---|---|---|---|---|
| `backToList` | 返回列表 (Esc) | Back to list (Esc) | 1 | 0 |
| `backToDetail` | 返回详情 (Esc) | Back to detail (Esc) | 0 | 1 |
| `unsaved` | 未保存 | Unsaved | 1 | 1 |
| `useTemplate` | 使用模板 | Use template | 1 | 0 |
| `useTemplateHint` | 从模板创建问题 | Create an issue from a template | 1 | 0 |
| `previewMode` | 预览模式 | Preview mode | 1 | 1 |
| `editMode` | 编辑模式 | Edit mode | 1 | 1 |
| `titlePlaceholder` | 输入问题标题... | Enter an issue title... | 1 | 1 |
| `description` | 描述 | Description | 1 | 1 |
| `markdownHint` | 支持 Markdown 语法，+ 引用其他资源 | Markdown supported. + mentions other resources | 1 | 1 |
| `descriptionPlaceholder` | 详细描述这个问题... | Describe this issue... | 1 | 1 |
| `attachments` | 附件 | Attachments | 1 | 0 |
| `addAttachment` | 添加附件 | Add attachment | 1 | 0 |
| `preview` | 预览 | Preview | 1 | 1 |
| `noDescription` | 暂无描述内容 | No description yet | 1 | 1 |
| `exitTitle` | 确认退出 | Leave page | 1 | 1 |
| `exitContent` | 你有未保存的更改，确定要退出吗？ | You have unsaved changes. Leave anyway? | 1 | 1 |
| `exitDiscard` | 放弃更改 | Discard changes | 1 | 1 |
| `exitKeep` | 继续编辑 | Keep editing | 1 | 1 |

`preview` 是预览区标题。编辑器切换按钮用 `page.markdownEditor.preview`，两键英文都是 Preview，不要合并。`markdownHint` 保留加号，它是产品里的引用标记。退出四句的英文属于决策 C，表内是推荐措辞。

### `page.issueTemplate`（8 键）

| 键 | zh-CN | en-US | 调用 |
|---|---|---|---|
| `intro` | 选择一个模板来快速创建规范的问题（工作区模板） | Pick a template to create a well-formed issue (workspace templates) | selector 1 |
| `empty` | 暂无可用模板 | No templates available | selector 1 |
| `footerHint` | 提示：你也可以不使用模板，直接创建空白问题 | Tip: you can skip templates and start a blank issue | selector 1 |
| `cancel` | 取消 | Cancel | selector 1，form 1 |
| `fieldTitle` | 标题 | Title | selector 2（回退 label 与 placeholder） |
| `fieldDescription` | 描述 | Description | selector 1（只回退 label） |
| `contentPreview` | 内容预览 | Content preview | form 1 |
| `previewHint` | 以下内容将填充到问题描述中： | This text will be filled into the issue description: | form 1 |

表单主按钮「创建问题」复用 `page.issueForm.createTitle`，在 `IssueTemplateForm.vue` 恰好 1 次。create 页上该键仍然恰好 2 次。选择器标题继续 `page.shell.selectIssueTemplate`，恰好 1 次，不新造 title 键。

### `page.markdownEditor`（23 键）

按钮 `title` 与帮助说明如果中英完全相同，共用一键，调用次数为 2。快捷键那三枚和「引用 / 引用块」分开。

| 键 | zh-CN | en-US | 调用 |
|---|---|---|---|
| `boldTitle` | 粗体 (Ctrl+B) | Bold (Ctrl+B) | 1 |
| `italicTitle` | 斜体 (Ctrl+I) | Italic (Ctrl+I) | 1 |
| `inlineCodeTitle` | 行内代码 (Ctrl+`) | Inline code (Ctrl+`) | 1 |
| `codeBlockTitle` | 代码块 | Code block | 2 |
| `linkTitle` | 链接 | Link | 2 |
| `bulletListTitle` | 无序列表 | Bulleted list | 2 |
| `quoteTitle` | 引用 | Quote | 1 |
| `headingTitle` | 标题 | Heading | 2 |
| `taskListTitle` | 任务列表 | Task list | 2 |
| `edit` | 编辑 | Edit | 1 |
| `preview` | 预览 | Preview | 1 |
| `syntaxHelp` | 语法帮助 | Syntax help | 1 |
| `syntaxTitle` | Markdown 语法 | Markdown syntax | 1 |
| `glossBold` | 粗体 | Bold | 1 |
| `glossItalic` | 斜体 | Italic | 1 |
| `glossInlineCode` | 行内代码 | Inline code | 1 |
| `glossQuote` | 引用块 | Quote block | 1 |
| `glossMention` | 提及用户 | Mention a user | 1 |
| `glossIssueRef` | 引用问题 | Reference an issue | 1 |
| `defaultPlaceholder` | 支持 Markdown 语法... | Markdown supported... | 1 |
| `emptyPreview` | 输入内容后预览 | Nothing to preview yet | 1 |
| `characters` | {n} 字符 | {n} characters | 1 |
| `footerHint` | 支持 Markdown 语法 • Ctrl+Enter 快速提交 | Markdown supported • Ctrl+Enter to submit | 1 |

`inlineCodeTitle` 的括号内是一个反引号字符。帮助列表里的 markdown 样例（含三反引号那一行、`**粗体**`、`@username`、`#OT-1`）保持原字符，只译破折号后的说明。`codeBlockTitle` 的第 2 次调用就是代码块那条说明，不再单设 gloss。

插入种子保持写死，决策 C：粗体文本、斜体文本、代码、代码块、链接文本、列表项、引用文本、标题、待办事项。

## 4. 范围

**范围内**

- 新建与编辑的页头：返回 tooltip、未保存、预览切换 tooltip。新建另有使用模板及其 tooltip。
- 新建与编辑的描述列：区标题、Markdown 提示、标题占位、描述占位、预览区标题、空态。
- 新建的附件区标题和「添加附件」。已有的 `page.shell.issueUploadHint` 不动。
- 两页退出确认的 title、content、positive、negative。推荐英文见上表，决策 C。
- `MarkdownEditor` 的工具栏 title、编辑/预览、语法帮助、帮助说明、默认占位、空预览、字符数、页脚。决策 A。
- 选择器介绍、空态、页脚、取消、API 缺字段时的「标题 / 描述」回退。表单的内容预览、提示、取消、主按钮。决策 B。

**范围外**

- 新建 486「自定义字段（可选）」；编辑 279「加载中...」。
- 全部 `window.$message`，含请输入问题标题、问题创建成功、问题创建失败、问题更新成功、模板表单「请填写…」、文件大小与上传警告。
- `constants/issueTemplates.ts` 种子名称和字段。它们会写进问题正文。
- 详情页整个文件：顶栏、只读描述、附件卡、评论占位、关注者「取消」、自定义字段、项目/估点/工时、Milestone、回收站 banner 和「恢复」。
- `AttachmentList.vue`、`IssueCustomFieldsEditor.vue`、FavoritesNav、显示面板、看板、批量条、四个设置页。
- 列表 `page.issueList`、表单 `page.issueForm` 已有键值、`page.shell.selectIssueTemplate`、`page.shell.issueUploadHint`、路由键。
- 暗色、对比度、焦点 CSS、`edit/surface.test.ts`、`constants/issue.ts`。

## 5. Yuri 待决策（不能悄悄当成已批）

**决策 A：推荐就地翻译 MarkdownEditor，所有挂载点的编辑器铬跟着变。** 详情评论、workflow、知识库 git 编辑的工具栏在 en-US 下也会变成英文；这些页传入的 placeholder 和周围按钮保持中文。不新增 prop，不分叉组件。否决则先从两份文档删掉 `page.markdownEditor`、`MarkdownEditor.vue` 和对应测试，再批准。

**决策 B：推荐包括选择器与模板表单的页铬。** 主按钮复用 `page.issueForm.createTitle`。种子正文不在内。否决则白名单去掉两个组件，只保留新建页上的使用模板按钮和 tooltip。

**决策 C：推荐退出四句用第 3 节英文，插入种子不译。** 这是本刀唯一需要拍板的英文，其余键按表锁定。不接受就先改表和测试合同，不带另一套英文实施。

## 6. 验收合同

- 三份 locale 与 `App.I18n.Schema` 的 `page.issueComposer`（19 leaf）、`page.issueTemplate`（8）、`page.markdownEditor`（23）一致。walker 用 `issueComposer\s*:\s*\{`、`issueTemplate\s*:\s*\{`、`markdownEditor\s*:\s*\{`，不得打到 `page.shell` 的字符串字段。
- 逐字冻结第 3 节中英文。`page.issueForm.createTitle` 仍是创建问题 / Create issue。`page.shell.selectIssueTemplate` 与 `page.shell.issueUploadHint` 的值不改。
- 调用次数按第 3 节的表，用源码里 `$t('page.issueComposer.useTemplate')` 这种精确串计数。create 上 `page.issueForm.createTitle` 仍是 2。表单上该键是 1。
- 精确字面缺失用正则，对着用户可见绑定，不扫注释。禁止 `not.toContain('描述')`、`('预览')`、`('附件')`、`('编辑')`、`('取消')`、`('标题')`。注释里的「描述编辑器」「预览模式」可以留下。
- 必须消失的绑定包括：`/^\s+使用模板\s*$/m`、`/从模板创建问题/`、`/<NText strong>描述<\/NText>/`、`/placeholder="输入问题标题\.\.\."/`、`/placeholder="详细描述这个问题\.\.\."/`、`/<NText strong>附件<\/NText>/`、`/^\s+添加附件\s*$/m`、`/<NText strong>预览<\/NText>/`、`/description="暂无描述内容"/`、`/title="确认退出"/`、退出 content 与 positive/negative 的中文属性、`/showPreview \? '编辑模式' : '预览模式'/`、`/^\s+返回列表 \(Esc\)\s*$/m`、`/^\s+返回详情 \(Esc\)\s*$/m`、`/>未保存</`。新建和编辑各自适用其中存在的那些。
- 范围外冻结：create 仍含请输入问题标题、问题创建成功、问题创建失败；仍含 `$t('page.shell.issueUploadHint')` 与「自定义字段（可选）」；编辑仍含「加载中...」；MarkdownEditor 仍含 `insertText('**', '**', '粗体文本')` 等种子；详情仍含顶栏「状态」「删除」和关注者行「取消」；选择器仍含 `page.shell.selectIssueTemplate`。
- `MarkdownEditor` 挂载测试：不传 placeholder 时，zh 占位是「支持 Markdown 语法...」，`setLocale('en-US')` 且不 remount 后变为 Markdown supported...。传入 placeholder 时，切语种后仍是传入值。工具栏文本含语法帮助 / Syntax help。stub 同时覆盖 naive-ui 真实 name 与 `N*` 别名（Button/NButton、ButtonGroup/NButtonGroup、Empty/NEmpty、Popover/NPopover、Space/NSpace、Text/NText）。不给产品组件加 `defineOptions({ name })`。
- `resolvedPlaceholder` 的第一条语句是 `void locale.value;`，下一条是 `if (props.placeholder !== undefined) return props.placeholder;`。其上可以有一行 `eslint-disable-next-line`。`no-void` 抑制恰好一处。
- 先 docs-only commit，再 tests-only RED（不要求单独的 RED commit），再最小产品 GREEN。四门对照**当次干净精确 base**。baseline 的 vitest 与 build 必须是 0 才继续；tsc / eslint 若非 0，保留既有诊断，新增诊断必须是 0。不得把 PR15 的数字写成全绿。
- 实施阶段浏览器若可用，采 en/zh 浅色新建页（模板对话框打开、描述区可见）和编辑页各一张。本草稿不做视觉验收。没有单独 Approve 行不得写 dual Grok Approve。

## 7. 限制

本盘点没有跑四门，没有量对比度，没有暗色截图。详情评论、workflow、知识库会跟着决策 A 换编辑器工具栏，宿主页其余中文还在，不能说成全页英文。模板种子在 API 空数据时仍是中文。toast 仍是中文。`fallbackLocale: 'en'` 本刀不改。

## 8. 实施边界

- 本轮只交本地草稿。获批口令为「design ok，开写」。决策 A/B/C 未确认前不得实施。
- 精确 base：`a1debf14bd754fcf34a788535c2a4d3a5684ed16`（PR15 tip）。不改写 PR6–15 已存提交或头。
- 后续仅普通隔离 clone（`.git` 为目录），不用 worktree。不写/reset MAIN `244c93e296a047cf138a880fa24d683b4be8203d` 或 PIN `250fc34af9c64e828aab706567b0430d3d74e452`。不碰 pid 服务。
- 不买额度，不 merge，不部署。未经再授权不 push、不开 PR。本轮不建产品分支、不改产品、不 TDD、不 commit、不联系任何人。

只允许下列 14 路径。审查要加路径，先改文档再批准：

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

`issue-form-property-chrome.test.ts` 只改 110–111 行对「使用模板」「从模板创建问题」的冻结，改成新键存在，并用正则确认这两句中文绑定不在。该文件其余断言不动。

hook 只在新 clone 处理：删除 pre-commit，保留 commit-msg，`core.hooksPath` 为空。不用 SKIP / `--no-verify`。commit EXIT 0 不证明 hook 读了本 checkout。若 `frontend/.git/COMMIT_EDITMSG` 或类似 ENOENT，原件落盘后立即停止，不二次 retry。不预安排第三笔提交。当前未实施。
