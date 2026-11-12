# 问题详情页英文铬

第 5 刀 design 草稿，送 Yuri 代审；没有审批结论。未来 repo 路径：`docs/superpowers/specs/2026-11-12-issue-detail-en-chrome-design.md`。本文与 plan 是一组。盘点报告在同目录 `inventory-REPORT.md`，不入库。行号以精确 base `290c3ed3be0cbd760eafca15e3a682b13b7b7004` 上的盘点为准。

## 1. 问题与证据

PR16 已限定交付。本刀起点为 `290c3ed3be0cbd760eafca15e3a682b13b7b7004`。`en-us.ts` 无汉字。`fallbackLocale` 是 `'en'`，注册的语言只有 `'zh-CN'` 和 `'en-US'`，缺 key 不会退回中文。英文界面上还能看见的中文，通常是写死字符串，或被上一刀测试冻住、故意不走 `$t` 的文案。

PR13–PR16 的页面骨架仍在，没有退回成写死中文。列表工具栏、创建/编辑描述列、SLA 页与回收站页骨架、详情右侧上半属性（状态、负责人、优先级、冲刺、类型、开始日、截止日、关注者、报告人）已经是 `$t`。同一条问题页序列上，点进详情后顶栏、描述、活动、评论框、右侧下半和关联/PR 面板仍是中文。这是本刀要收的接缝。

`MarkdownEditor` 已在 PR16 原地翻译：没有 locale prop，没有 fork。工具栏、语法帮助说明、编辑/预览、字数、页脚走 `page.markdownEditor.*`。`insertText` 种子和帮助里的 `<code>` 示例仍是中文，本刀不改。详情评论把中文 placeholder 传进编辑器，会盖过默认英文占位；本刀只改详情宿主传入的占位和按钮，不改编辑器本体。

盘点已复核：`page.issueList.messages.noneCycle` 与 `page.issueList.noneCycle` 的英文都是 “No cycle”，不要为合并 key 开片。「使用模板」不在详情页；创建页已走 `page.issueComposer.useTemplate`。创建页「自定义字段（可选）」和编辑页「加载中...」仍在，但被 PR16 测试写成范围外，不进本刀。

## 2. 方案与推荐

A（推荐）：新建与 `page.issueForm` / `page.issueComposer` 并列的 `page.issueDetail`，反应、外链、PR 面板分设 `page.issueReaction`、`page.issueLink`、`page.issuePr`。页级与三个只被详情引用的组件继续用已有的 `@/locales` `$t`。活动流 `formatTimelineAction` 改读 `page.issueStatus` / `page.issuePriority` 和本刀新键，不再写死状态词。已有可复用的整句优先复用，不造近义 key。

B：把这些键全部塞进 `page.issueForm` 或 `page.issueComposer`。少几个 namespace，但把属性卡、编写器和详情宿主焊在一起，上一刀的键集合测试也要重开。不采用。

C：先做盘点第三片（壳层收藏、工作区切换、快捷键），详情留到以后。壳层更小，也不碰 composer 的范围外断言；但详情顶栏和主栏才是这条问题页序列上整块仍是中文的表面。不采用（决定 G）。

选 A。已有 `$t('page.issueForm.*')`、`$t('page.issueComposer.*')`、`$t('page.issueTrash.restore')`、`$t('common.edit')`、`$t('common.delete')`、`$t('common.cancel')`、`$t('common.confirm')`、`$t('page.shell.addSubIssue')` 不重写其键值。不要把既有 `$t` 改成局部 `t()`。不要改 `constants/issue.ts` 的中文 label。详情属性下拉已经只用 value + `useLabelTable`。

脚本里若新增调用 `$t` 的 computed，第一句必须是 `void locale.value;`，位于任何短路之前。`no-void` 只用 `eslint-disable-next-line` 盖住这一句，或紧贴该 computed 的 disable/enable 块。禁止文件级 `eslint-disable no-void`。模板里的 `$t` 不包 computed。命名参数插值必须写成 `$t('…', { n: … })`，禁止 `.replace('{n}', …)` 迁就测试。

## 3. 锁定文案

英文 sentence case。中文逐字保留，包括 ASCII `...`、全角省略号、全角括号。协议词与字段名保留：`@`、`+ISSUE-xxx`、`+PROJECT-xxx`、`+REQUIREMENT-xxx`、`parent_issue_id`、`https://github.com/org/repo/pull/1`、emoji。不改 route 键值。不改 `page.issueForm`、`page.issueComposer`、`page.issueTrash`、`page.issueStatus`、`page.issuePriority` 已有译文，复用时按已有英文走。

下面「调用」按盘点可见点计；实施时以源码为准，测试按实际调用次数钉死。

### 复用已有键（不新造近义句）

| 表面 | 中文 | 键 | 英文 |
|---|---|---|---|
| 顶栏恢复 | 恢复 | `page.issueTrash.restore` | Restore |
| 顶栏编辑 | 编辑 | `common.edit` | Edit |
| 顶栏状态 | 状态 | `page.issueForm.status` | Status |
| 顶栏删除；评论/外链删除 | 删除 | `common.delete` | Delete |
| 主栏描述标题 | 描述 | `page.issueComposer.description` | Description |
| 主栏附件标题 | 附件 | `page.issueComposer.attachments` | Attachments |
| 评论/弹层取消 | 取消 | `common.cancel` | Cancel |
| 弹层确认 | 确认 | `common.confirm` | Confirm |
| 侧栏未设置 | 未设置 | `page.issueForm.unset` | Not set |
| 侧栏估点标题 | 估点 | `page.issueList.columns.estimate` | Estimate |
| 活动「导出 CSV」 | 导出 CSV | `page.insights.exportCsv` | Export CSV |
| 子问题弹层标题 | （已是 `$t`） | `page.shell.addSubIssue` | Add sub-issue |

顶栏收藏复用列表已有 `page.issueList.toolbar.pinToSidebar` / `unpinFromSidebar`（Pin to sidebar / Unpin from sidebar），不再新造 unpin 键。`zh-cn.ts` 里 `pinToSidebar` 已是「收藏到侧栏」，与顶栏现文案一致；`unpinFromSidebar` 是「取消侧栏」。复用后，顶栏会从「取消侧栏收藏」变成「取消侧栏」。这是接受的中文变化，不是笔误。测试按复用后的中英文断言，并确认源码不再出现字面量「取消侧栏收藏」。

不要复用：

- `page.issueComposer.noDescription`（中文「暂无描述内容」，详情空态是「暂无描述」）
- `page.issueForm.linkedProject`（“Linked project”，详情短标签是「项目」）
- `page.shell.addSubIssue` 去覆盖主栏「子问题 / + 添加 / 暂无子问题」三处
- `page.issueList.blocks` / `blockedBy`（带 `{count}` 的列表计数句）去当关系类型名
- `route.workspace_custom-fields`（Custom Fields）去当侧栏小标题；本刀用新键，英文 sentence case：Custom fields
- 关注者行内「取消」：不要用 `common.cancel`（Cancel），也不要绑到顶栏的 `unwatch`（中文是「取消关注」）。另设 `unwatchInline`：zh「取消」、en Unwatch，以逐字保留行内短文案

### `page.issueDetail`（新键）

| 键 | zh-CN | en-US |
|---|---|---|
| `parentPrefix` | 父问题： | Parent: |
| `copyIssue` | 复制问题 | Copy issue |
| `changeParent` | 更换父 | Change parent |
| `setAsChild` | 设为子项… | Set as child... |
| `promoteToRoot` | 提升为根 | Promote to root |
| `watch` | 关注 | Watch |
| `unwatch` | 取消关注 | Unwatch |
| `unwatchInline` | 取消 | Unwatch |
| `copyBranchName` | 复制分支名 | Copy branch name |
| `noDescription` | 暂无描述 | No description |
| `subIssues` | 子问题 | Sub-issues |
| `add` | + 添加 | + Add |
| `noSubIssues` | 暂无子问题 | No sub-issues |
| `activity` | 活动 ({n}) | Activity ({n}) |
| `reply` | 回复 | Reply |
| `noActivity` | 暂无活动 | No activity |
| `replyPlaceholder` | 写下回复...支持 Markdown | Write a reply... Markdown supported |
| `commentPlaceholder` | 添加评论...支持 Markdown 语法。使用 @提及用户，+ISSUE-xxx 引用问题、+PROJECT-xxx 引用项目、+REQUIREMENT-xxx 引用需求等 | Add a comment... Markdown supported. Use @ to mention a user, +ISSUE-xxx to reference an issue, +PROJECT-xxx for a project, +REQUIREMENT-xxx for a requirement, and similar |
| `postReply` | 发表回复 | Post reply |
| `postComment` | 发表评论 | Post comment |
| `chooseMilestone` | 选择 Milestone | Choose a Milestone |
| `noMilestone` | 无 Milestone | No Milestone |
| `project` | 项目 | Project |
| `timeTracking` | 工时 | Time tracking |
| `estimated` | 预估: | Est.: |
| `actual` | 实际: | Actual: |
| `slaPaused` | 已暂停 | Paused |
| `customFields` | 自定义字段 | Custom fields |
| `customerRequests` | 客户需求 | Customer requests |
| `linkedIssues` | 关联问题 | Linked issues |
| `noLinks` | 暂无关联 | No links yet |
| `targetIssuePlaceholder` | 目标问题 ID 或 KEY-N | Target issue ID or KEY-N |
| `confirmAdd` | 确认添加 | Confirm add |
| `remove` | 移除 | Remove |
| `relationBlocks` | 阻塞 | Blocks |
| `relationBlockedBy` | 被阻塞 | Blocked by |
| `relationRelated` | 关联 | Related |
| `relationDuplicates` | 重复 | Duplicates |
| `relationDependsOn` | 依赖 | Depends on |
| `relationDuplicatedBy` | 被重复 | Duplicated by |
| `relationDependedOnBy` | 被依赖 | Depended on by |
| `tags` | 标签 | Tags |
| `noTags` | 暂无标签 | No tags yet |
| `chooseTag` | 选择标签 | Choose a tag |
| `createdAt` | 创建于 | Created |
| `updatedAt` | 更新于 | Updated |
| `viewedNTimes` | 浏览 {n} 次 | Viewed {n} times |
| `quickActions` | 快速操作 | Quick actions |
| `getAgentInstructions` | 获取 Agent 指令 | Get agent instructions |
| `refresh` | 刷新数据 | Refresh |
| `changeParentTitle` | 更换父问题 | Change parent |
| `setAsChildTitle` | 设为子项 | Set as child |
| `changeParentHint` | 选择同工作区的父问题（排除自身；环由服务端校验）。 | Pick a parent in this workspace (itself is excluded; cycles are checked on the server). |
| `searchIssues` | 搜索问题… | Search issues... |
| `addSubIssueHint` | 将创建挂在当前问题下的子项（parent_issue_id）。 | This creates a child of the current issue (parent_issue_id). |
| `subIssueTitle` | 子问题标题 | Sub-issue title |
| `create` | 创建 | Create |

`commentPlaceholder` 的中文已按盘点摘录 `detail/index.vue:1796` 逐字写入。英文保留 `@`、`+ISSUE-xxx`、`+PROJECT-xxx`、`+REQUIREMENT-xxx`，并用 “and similar” 对应句末「等」。`addSubIssueHint` 保留括号内 `parent_issue_id`。`activity` 与 `viewedNTimes` 使用 `$t('…', { n: … })`。

Milestone 标签本身已经是英文 `Milestone`，不新造 label 键。

### 活动流（`formatTimelineAction`，决定 B）

状态与优先级改读 `page.issueStatus.*` / `page.issuePriority.*`。中文活动流里 `open` 的「待处理」改为与属性栏一致的「待办」；英文为 Open / In progress 等已有译文。不要新造一套状态词，也不要改 `constants/issue.ts`。Agent 指令正文里的「待处理」本刀不动（决定 A）。

活动流动词与其余字面收入上面的 `timeline*` 键。SLA 芯片前缀 `slaMetricBadgePrefix` 本刀不改（决定 D）。侧栏芯片在英文详情上仍可能以「状态 SLA / 首响 SLA」开头并与「Paused」混排，直到有人明确改 `sla.test.ts`。

「未分配」在活动流里保留为独立键（Unassigned），不要改分组函数，也不要和看板「未指派」强行并成同一个中文源串。

### `page.issueReaction`

| 键 | zh-CN | en-US |
|---|---|---|
| `add` | 添加反应 | Add reaction |
| `thumbsUp` | 赞成 | Thumbs up |
| `thumbsDown` | 反对 | Thumbs down |
| `heart` | 喜欢 | Heart |
| `tada` | 庆祝 | Celebration |
| `rocket` | 火箭 | Rocket |
| `eyes` | 关注 | Eyes |
| `confused` | 困惑 | Confused |
| `smile` | 开心 | Smile |
| `others` | {a}, {b} 和其他 {n} 人 | {a}, {b}, and {n} others |

emoji 保留。名字按常见 GitHub 反应，不用「Like」去译「喜欢」，以免和按钮语义打架。

### `page.issueLink` 与 `page.issuePr`

外链面板与 PR 面板只有详情引用。模板与脚本 toast 一起进本刀，不要扩散成全局 toast 片。取消 / 编辑 / 删除复用 `common.cancel` / `common.edit` / `common.delete`。精确 base 上没有 `common.save`，「保存」用 `page.issueLink.save`。中文逐字保留。PR URL 示例 `https://github.com/org/repo/pull/1` 保留。下方表已锁定英文。

### `page.issueLink`

取消 / 编辑 / 删除复用 `common.cancel`、`common.edit`、`common.delete`。没有 `common.save`，「保存」用本对象的 `save`。

| 键 | zh-CN | en-US |
|---|---|---|
| `title` | 链接 | Links |
| `empty` | 添加设计稿、文档或仪表盘链接 | Add a design, doc, or dashboard link |
| `titleOptional` | 标题（可选） | Title (optional) |
| `save` | 保存 | Save |
| `addLink` | 添加链接 | Add link |
| `loadFailed` | 加载外链失败 | Couldn't load links |
| `urlRequired` | 请输入链接 URL | Enter a link URL |
| `httpOnly` | 仅支持 http:// 或 https:// 链接 | Only http:// or https:// links are supported |
| `addFailed` | 添加失败 | Couldn't add the link |
| `added` | 已添加链接 | Link added |
| `updateFailed` | 更新失败 | Couldn't update the link |
| `updated` | 已更新 | Updated |
| `deleteFailed` | 删除失败 | Couldn't delete the link |
| `deleted` | 已删除 | Deleted |

这些 toast 只存在于本文件，随面板进本刀，不扩散到详情页那几十条 `window.$message`。

### `page.issuePr`

`titleOptional` 复用 `page.issueLink.titleOptional`。URL 示例字符保留。

| 键 | zh-CN | en-US |
|---|---|---|
| `title` | 关联的 PR | Linked PRs |
| `empty` | 暂无关联的 Pull Request | No linked pull requests |
| `unlink` | 解除关联 | Unlink |
| `urlPlaceholder` | PR URL（如 https://github.com/org/repo/pull/1） | PR URL (e.g. https://github.com/org/repo/pull/1) |
| `add` | 关联 PR | Link PR |
| `loadFailed` | 加载 PR 关联失败 | Couldn't load linked PRs |
| `urlRequired` | 请输入 PR URL | Enter a PR URL |
| `linkFailed` | 关联失败 | Couldn't link the PR |
| `linked` | 已关联 PR | PR linked |
| `unlinkFailed` | 解除关联失败 | Couldn't unlink the PR |
| `unlinked` | 已解除关联 | Unlinked |

### `page.issueDetail` 活动流键

状态与优先级标签走 `page.issueStatus.*` / `page.issuePriority.*`（决定 B）。其余：

| 键 | zh-CN | en-US |
|---|---|---|
| `timelineUnassigned` | 未分配 | Unassigned |
| `timelineEmpty` | 空 | Empty |
| `timelineCreated` | 创建了此问题 | Created this issue |
| `timelineRestored` | 从回收站恢复了此问题 | Restored this issue from the trash |
| `timelineUpdated` | 更新了问题 | Updated the issue |
| `timelineCommented` | 添加了评论 | Added a comment |
| `timelineStatusChanged` | 将状态从 "{from}" 改为 "{to}" | Changed status from "{from}" to "{to}" |
| `timelineAssigneeChanged` | 将负责人从 "{from}" 改为 "{to}" | Changed assignee from "{from}" to "{to}" |
| `timelinePriorityChanged` | 将优先级从 "{from}" 改为 "{to}" | Changed priority from "{from}" to "{to}" |
| `timelineDueDateChanged` | 修改了截止日期 | Changed the due date |
| `timelineStartDateChanged` | 修改了计划开始日 | Changed the start date |
| `timelineRelationAdded` | 添加了关联: {type} | Added a link: {type} |
| `timelineRelationRemoved` | 移除了关联 | Removed a link |
| `timelineAttachmentAdded` | 添加了附件 | Added an attachment |
| `timelineAttachmentRemoved` | 移除了附件 | Removed an attachment |
| `timelineTagAdded` | 添加了标签 | Added a tag |
| `timelineTagRemoved` | 移除了标签 | Removed a tag |
| `timelineReactionAdded` | 添加了反应 {emoji} | Added a {emoji} reaction |
| `timelineReactionRemoved` | 移除了反应 {emoji} | Removed a {emoji} reaction |
| `timelineMarkedResolved` | 标记为已解决 | Marked as resolved |
| `timelineClosed` | 关闭了此问题 | Closed this issue |
| `timelineReopened` | 重新打开此问题 | Reopened this issue |
| `timelineCustomFieldChanged` | 将自定义字段 {key} 从 {from} 改为 {to} | Changed custom field {key} from {from} to {to} |
| `timelineCycleChanged` | 将冲刺从 {from} 改为 {to} | Changed cycle from {from} to {to} |
| `timelineEstimateChanged` | 将估分从 {from} 改为 {to} | Changed estimate from {from} to {to} |
| `timelineProjectChanged` | 将项目从 {from} 改为 {to} | Changed project from {from} to {to} |
| `timelineSlaPaused` | 暂停了{metric} SLA（{name}） | Paused {metric} SLA ({name}) |
| `timelineSlaResumed` | 恢复了{metric} SLA（{name}） | Resumed {metric} SLA ({name}) |
| `timelineSlaMetricFirstResponse` | 首响 | first-response |
| `timelineSlaMetricStatus` | 状态 | status |

中文「估分」按源码保留，不改成「估点」。SLA 活动流句子可以整句英文化；侧栏芯片前缀仍不改（决定 D）。`timelineRelationAdded` 的 `{type}` 用本刀关系类型键，不要改 `constants/issue.ts`。带参数的键一律 `$t('…', { from, to, type, emoji, key, metric, name })`，禁止 `.replace`。

## 4. 范围

**范围内**

- 详情顶栏仍写死的可见按钮与「父问题：」前缀（恢复复用 `page.issueTrash.restore`）
- 主栏描述标题与空态、附件区标题（AttachmentList 内部不改）、子问题三句、活动标题/空态/导出/回复/删除
- 详情评论宿主：取消、两则 placeholder、发表回复 / 发表评论。不改 `MarkdownEditor.vue`
- 右侧下半：项目、估点、工时、已暂停、自定义字段标题、客户需求、关联问题、关系类型名、标签、创建于 / 更新于 / 浏览次数、快速操作（获取 Agent 指令、刷新数据）。自定义字段编辑器内部不改
- Milestone 的「选择 Milestone」占位和选项「无 Milestone」。Milestone 标签本身已是英文
- 顶栏 `:1545`「取消关注 / 关注」走 `unwatch` / `watch`。关注者行内 `:2026` 短文案「取消」走 `unwatchInline`（zh「取消」、en Unwatch），不要绑到 `unwatch`，也不要用 `common.cancel`
- 更换父 / 设为子项等弹层标题、说明、搜索占位、子问题标题与按钮（弹层标题已走 `page.shell.addSubIssue` 的不重写）
- `IssueReactions.vue`、`IssueLinksPanel.vue`、`IssuePrPanel.vue` 的可见铬与文件内 toast
- `formatTimelineAction.ts` 及配套测试（决定 B）
- 会被字面量打断的现有测试：`issue-composer-chrome.test.ts` 里要求详情仍含「状态」「删除」「取消」的那段；`detail/focus.test.ts` 里用「编辑」定位顶栏按钮的那段

**范围外**

- `MarkdownEditor.vue` 本体、`insertText` 种子、语法 `<code>` 示例
- `AttachmentList.vue`（详情里附件区内部继续中文，留到以后的附件片）
- `IssueCustomFieldsEditor.vue` 内部（「公式 / 文本 / 草稿 / 暂无自定义字段」等）
- `service/api/sla.ts` 的 `slaMetricBadgePrefix`（决定 D）。英文详情上 SLA 标签仍以「状态 SLA / 首响 SLA」开头
- `utils/issueTrashMeta.ts` 的 `deletedReadonlyBanner` 与 `restoreSuccessMessage`（决定 C）。顶栏「恢复」可译，横幅与恢复成功 toast 在英文详情上暂时保持中文
- `detail/index.vue` 里全部 `window.$message` toast（约 `:282`–`:1398`）
- Agent 指令弹层的标题、说明和生成正文（决定 A）
- 未挂路由的 `views/issue/detail/components/*` demo 卡片
- `constants/issue.ts`
- 创建页「自定义字段（可选）」、编辑页「加载中...」、创建/编辑 toast、`IssueTemplateForm` 的 `请填写${field.label}`
- 列表看板、显示选项、批量条、搜索建议（第二片）；壳层收藏、工作区、快捷键（第三片，决定 G 不提前）
- 设置四页、工作流 / 知识库 / 需求详情等大模块
- `noneCycle` 合并
- 暗色、对比度、焦点 CSS（改顶栏文案时只改 `focus.test.ts` 的定位字面量，不改样式）
- 不 merge、不部署、未经再授权不 push、不开新 PR。不改写 PR6–16 已存提交或头 SHA

## 5. 决定（批准前确认）

按盘点推荐案写入本文。否决任一条，先改 design 与 plan，再实施。

- **A. Agent 指令弹层。** 本刀不包含弹层标题、说明和生成正文。正文是给外部 agent 的中文操作稿，内含 CLI 示例。若只译按钮、留下正文，弹层会中英混排。整段留到以后。
- **B. 活动流状态词。** `formatTimelineAction` 复用 `page.issueStatus` / `page.issuePriority`。中文活动流的 `open` 从「待处理」变成「待办」，与属性栏一致。
- **C. 回收站横幅。** 不改 `deletedReadonlyBanner` 和 `restoreSuccessMessage`。顶栏「恢复」走已有 `page.issueTrash.restore`。横幅在英文详情上暂时保持中文，直到有人明确改 PR15 的冻结测试。
- **D. SLA 芯片前缀。** 不改 `slaMetricBadgePrefix`。接受英文详情上「状态 SLA / 首响 SLA」前缀仍为中文；若「已暂停」译成 Paused，芯片可能出现中英混排。不在本刀改 `sla.test.ts`。
- **E / F。** 属于建议的第二片（分组「未分配」、搜索建议只译说明），本刀只记录，不实施。
- **G。** 第一片仍是详情宿主，不改先做壳层。

## 6. 测试与验收口径

- 新测试统计 `$t('…')` 调用点，字面缺失用正则。禁止宽泛的 `not.toContain('描述')` / `('预览')` / `('附件')` / `('编辑')` / `('取消')` / `('标题')` / `('状态')`。
- `watch`、`unwatch`、`unwatchInline` 分别计 `countCalls`。顶栏走前两键；行内「取消」只走 `unwatchInline`。行内「取消」的缺失正则必须带周围 markup，避免误伤评论宿主的 `common.cancel` 或 toast。
- 顶栏收藏按复用后的中英文断言：`pinToSidebar` 仍是「收藏到侧栏」/ Pin to sidebar，`unpinFromSidebar` 是「取消侧栏」/ Unpin from sidebar；源码不再出现字面量「取消侧栏收藏」。
- 更新 `issue-composer-chrome.test.ts` 里把详情顶栏「状态」「删除」「取消」冻成范围外的那段，改为要求走本刀键，且不再把这三字当作详情必须留下的中文。不改写 PR16 已存提交。
- 更新 `detail/focus.test.ts` 里用字面量「编辑」定位顶栏按钮的断言，改为对 `common.edit` 译文或稳定选择器定位。不改焦点 CSS。
- 有 `useI18n()` 的组件，Vue Test Utils 挂载必须 `plugins: [i18n]`（已有 pinia 则 `[pinia, i18n]`）。不要为了测试删掉 `useI18n` 或改组件 identity。
- `formatTimelineAction.test.ts` 必须接入真实 `@/locales` i18n（可切换 `zh-CN` / `en-US`），不要只改期望字符串，也不要自己造一套残缺 messages。
- 字符数或 `{n}` 插值：产品用 `$t('…', { n: … })`，测试接受并要求这种写法。
- 四门对照当次干净 `290c3ed3` 基线。tsc/eslint 基线非 0 则保持 added 0 / removed 0，不得写成全绿，不得借用 PR15/PR16 的失败行号。不能写 dual Grok Approve。
- 不要求本刀截图作为验收门（创建/编辑/详情同样依赖后端与已登录会话）。若实施时拿得到，只作为附证。

## 7. 限制（写入验收说明）

- 第一次在仓库根提交若再出现 `Script not found "sa"`，必须 STOP 并记入限制；plan 已收入第 4 刀已接受的根 hook 拷贝与 gitignore 相对软链步骤，避免再踩同一坑，但那不是改 hook 正文。
- commit hook EXIT 0 不是路径证明，需要 strace 显示只读打开克隆根 `.git/COMMIT_EDITMSG`。
- `.env.prod` 不得入库、不得把正文写入证据包。prod build 只允许使用 sha256 仍为 `b686d37a6c470d295b5cf4165eea1c3a6ca3a43fcc08d0155b5a27634d2d2ce7`（1896 字节）的已核副本；哈希不符或缺失则 STOP，不用 `.env.example` 顶替。
- prod build 若弄脏 `frontend/src/typings/components.d.ts`，必须从仓库根 `git checkout --` 再跑 tsc/eslint，打包还原前后 porcelain，不提交该文件。
