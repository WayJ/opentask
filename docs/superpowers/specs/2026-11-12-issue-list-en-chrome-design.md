# 问题列表英文铬

Yuri 已确认三个盘点草稿成立，并指定先只写第 1 刀的 design/plan，代审后再 TDD。第 2、第 3 刀按已划界等待，不平行实施。建议共同 base 仍是 PR12 tip `18a63574c4b40baf48e7990160be5516e075b89e`（`cursor/issue-detail-generic-focus-4333`）。获批前不建产品分支，不 commit，不改产品代码，不改 PR6–11 头，不改已接受的焦点规则，不 merge，不部署。

证据：只读盘点包 sha256 `c681fcc704dc0588c06fb8cdeb7fbeee34c52314486b774cc637c232bb40cf55`。Yuri 已独立核过该包与 12 张原图。本文字符串与行号以该 SHA 上 `frontend/src/views/issue/list/index.vue` 为准。

## 1. 问题

英文下列表页头已经走 `page.shell.*`（Issues / List / Board / Export / Import / Trash / New issue，搜索框和空态也已翻译）。单元格类型、状态、优先级已经走 `useLabelTable('page.issueType' | 'page.issueStatus' | 'page.issuePriority')`，原图上是 Bug / Open / Medium。

同一屏仍有写死中文，浅色 1280、深色 1280（`htmlClass` 为 `dark`，`html.dark` 为 true，`prefers` 仍为 light）和 390×844 都一样：

- 页签：我的待办 / 开放中 / 已关闭 / 全部（约 1655–1688 行）
- 工具条：视图、保存视图、星标、收藏到侧栏 / 取消侧栏、另存为、筛选、语法帮助、显示、排序、创建时间、降序、分组、不分组，以及这些按钮的说明（约 1712–1848 行）
- 列标题：编号、标题、类型、状态、优先级、估点、负责人、报告人、创建时间、操作（约 1309–1438 行）
- 行按钮：详情、删除（1445–1446 行）

`frontend/src/views/issue/list/surface.test.ts` 把其中几处中文冻在断言里（`详情`、`删除`、`确认删除`、`问题删除成功` 等）。改文案时必须同步改这份测试，不能假装原文还在。

## 2. 方案

只在列表页把用户可见的写死中文改成 `$t`，中英两套文案一起补。已有 `import { $t } from '@/locales'`。单元格继续用现有 label table，不改枚举值。

新键放在 `page.issueList`，不要往已经拥挤的 `page.shell` 里堆。`frontend/src/typings/app.d.ts` 里的 `App.I18n.Schema.page` 必须同步加上同一棵形状，否则 `$t` 的 `I18nKey` 过不了类型检查。`zh-cn.ts` 与 `en-us.ts` 的键集合必须与 Schema 一致。

已经语义匹配的公共键直接复用，不另造：行「删除」和删除框确认按钮用 `common.delete`（删除 / Delete），取消用 `common.cancel`（取消 / Cancel）。不要复用 `common.confirmDelete`（文案是「确认删除吗？」/ “Are you sure you want to delete?”，与当前「确定要删除问题 "…" 吗？」不同），也不要复用 `common.deleteSuccess`（“Delete Success”）或 `common.index`（「序号」，不是「编号」）。

`groupByOptions` 来自 `@/utils/groupIssuesBy` 的 `GROUP_BY_OPTIONS` / `buildGroupByOptions`，里面的「不分组」「状态」等是共享中文。**不准改** `groupIssuesBy.ts`、`IssueBoard.vue` 或其它调用方。只在本页对内建 `value`（`none` / `status` / `assignee` / `priority` / `type` / `label`）映射到 `page.issueList.groupBy.*`；自定义字段名保持原名。排序下拉里本地拼出的公式后缀「（计算值）」用 `page.issueList.computedFieldSuffix`；分组下拉来自 `buildGroupByOptions` 的「（计算值·只读）」用独立键 `page.issueList.computedFieldSuffixReadonly`，中文原词保持不变，不要把只读后缀改成「（计算值）」，也不要改工具函数。

排序选项、列标题、页签、工具条、筛选占位和语法帮助都在 `index.vue` 本地，直接改成 `$t`。用于选项和列定义的 computed 必须读取当前语言（例如 `i18n.global.locale.value` 或 `getLocale()`），这样切换语言时下拉和表头会更新，不必整页重载。

带问题标题的删除确认用具名插值：`$t('page.issueList.messages.deleteConfirmContent', { title: issue.title })`，对应文案保留引号中的标题。

## 3. 范围

**在范围（必须）：** `frontend/src/views/issue/list/index.vue` 上的页签、工具条（含按钮说明）、列标题、行按钮「详情 / 删除」，以及展开后的筛选占位和「重置筛选」、语法帮助面板（查询词 `assignee:@me` 等保持原文，只译文案说明）、列表顶栏「收藏视图」和「当前视图：」前缀、报告人回退「系统」。

**在范围（同文件顺手带上的提示）：** 保存视图弹窗和相关 toast；删除确认框和删除结果 toast；应用 / 星标 / 另存为已保存视图的 toast；设为个人默认显示的 toast；分组自定义字段不受支持而回退的警告。同一函数里泳道回退那句也一起翻译，只为避免留下中文兄弟句，不因此去改看板文件。导入 CSV 弹窗里仍写死的说明和「下载模板 CSV」也一起翻译（弹窗标题已是 `page.shell.importIssueCsv`）。

**不在范围：** 已翻译的页头、搜索框、空态和单元格；`IssueBoard.vue`、`DisplayOptionsPanel.vue`（「显示」按钮在 `index.vue` 内，在范围；面板正文不在）、`IssueListGrouped.vue`、`IssueBulkBar`、快捷键选择器、`groupIssuesBy.ts`、`constants/issue.ts`；左侧边栏「收藏」标题和收藏条目（不是本页工具条的「收藏到侧栏」）；第 2 刀属性区、第 3 刀 SLA / 回收站；已接受的详情编辑焦点和通用 `*:focus-visible`；`route.issue_edit`；PR6–11 头。390 宽首屏只看到「编号」「标题」不单独立项，不把未量的 `scrollWidth` 当布局缺陷。

下面是锁定文案。实施不得另撰英文。中文保持现有用户可见用词，只是改成键。

### 3.1 页签 `page.issueList.tabs`

| 键 | zh-CN | en-US |
|---|---|---|
| myTodos | 我的待办 | My to-dos |
| open | 开放中 | Active |
| closed | 已关闭 | Closed |
| all | 全部 | All |

这个页签在源码里过滤的是 `open` + `in_progress` + `feedback`，与状态值 `page.issueStatus.open`（待办 / Open）不是同一含义。英文必须用 `Active`，不能用 `Open`，以免同一屏上页签和状态徽章都写成 Open。中文保持「开放中」。

「已关闭」英译仍用 Closed。它与状态 Closed 有部分重叠（页签还含 resolved / rejected），本刀不另造词。分组后的桶文案（未分配、无标签等）仍在 `groupIssuesBy.ts` 里，本刀维持中文。英文锁定表里的弯引号（如 `Couldn’t`、`“{title}”`）实施和测试必须与表逐字相同。

### 3.2 工具条 `page.issueList.toolbar`

| 键 | zh-CN | en-US |
|---|---|---|
| views | 视图 | Views |
| saveView | 保存视图 | Save view |
| saveViewHint | 将当前筛选保存为个人或共享视图 | Save the current filters as a personal or shared view |
| star | 星标 | Star |
| starHint | 星标视图（列表顶栏 chips，≠ 侧栏收藏） | Star a view (chips on the list toolbar, not the sidebar) |
| pinToSidebar | 收藏到侧栏 | Pin to sidebar |
| unpinFromSidebar | 取消侧栏 | Unpin from sidebar |
| pinToSidebarHint | 固定到左侧边栏 Favorites（独立于星标） | Pin to the sidebar favorites (separate from starring) |
| saveAs | 另存为 | Save as |
| saveAsHint | 复制为个人视图（共享只读成员可用） | Duplicate as a personal view (for read-only members of a shared view) |
| filters | 筛选 | Filters |
| collapseFilters | 收起筛选面板 | Collapse filters |
| expandFilters | 展开筛选面板 | Expand filters |
| syntaxHelp | 语法帮助 | Syntax help |
| syntaxHelpHint | 查看搜索语法帮助 | View search syntax help |
| display | 显示 | Display |
| sort | 排序 | Sort |
| group | 分组 | Group |

排序字段 `page.issueList.sortBy`：`createdAt` 创建时间 / Created；`updatedAt` 更新时间 / Updated；`priority` 优先级 / Priority；`status` 状态 / Status；`title` 标题 / Title；`dueDate` 截止日期 / Due date。排序方向 `page.issueList.sortOrder`：`desc` 降序 / Descending；`asc` 升序 / Ascending。

分组内建项 `page.issueList.groupBy`：`none` 不分组 / No grouping；`status` 状态 / Status；`assignee` 负责人 / Assignee；`priority` 优先级 / Priority；`type` 类型 / Type；`label` 标签 / Label。`computedFieldSuffix`：（计算值） / (computed)。`computedFieldSuffixReadonly`：（计算值·只读） / (computed, read-only)。

### 3.3 列与行按钮 `page.issueList.columns` / `actions`

| 键 | zh-CN | en-US |
|---|---|---|
| columns.key | 编号 | Key |
| columns.title | 标题 | Title |
| columns.type | 类型 | Type |
| columns.status | 状态 | Status |
| columns.priority | 优先级 | Priority |
| columns.estimate | 估点 | Estimate |
| columns.assignee | 负责人 | Assignee |
| columns.reporter | 报告人 | Reporter |
| columns.createdAt | 创建时间 | Created |
| columns.actions | 操作 | Actions |
| actions.view | 详情 | View |
| actions.systemReporter | 系统 | System |

列键用 `columns.key`，英译为 Key，因为这一列的字段是 `issue_code`，不是序号；不要复用 `common.index`。

删除按钮用 `common.delete`。

### 3.4 筛选、语法帮助、视图铬

`page.issueList.filters`：`project` 项目 / Project；`cycle` 冲刺 / Cycle；`type` 类型 / Type；`priority` 优先级 / Priority；`reset` 重置筛选 / Reset filters。

`page.issueList.syntax`：`title` 搜索语法帮助 / Search syntax help；`tipPrefix` 提示：可以组合使用多个过滤器，如 / Tip: you can combine filters, for example；各条 `desc` 保持现有中文意思，英文为：Show issues assigned to me；Show only open issues；Show only completed issues；Show only in-progress issues；Show only feature issues；Show only bug issues；Show only urgent-priority issues；Show only high-priority issues；Filter by a custom field (cf:key:value also works)。查询词本身不翻译。

`page.issueList.views`：`currentPrefix` 当前视图： / Current view:；`favoriteViews` 收藏视图 / Starred views；`savePersonalTitle` 保存为个人视图 / Save as personal view；`saveSharedTitle` 保存为共享视图 / Save as shared view；`save` 保存 / Save；`namePlaceholder` 视图名称，例如：我的高优缺陷 / View name, e.g. My high-priority bugs；`shareWithWorkspace` 共享给工作区 / Share with the workspace。取消用 `common.cancel`。

范围标题 `page.issueList.scopeTitle`：`watching` 我关注的 / Watching；`dueSoon` 即将到期 / Due soon；`assignedToMe` 指派给我 / Assigned to me；`createdByMe` 我创建的 / Created by me。

导入 `page.issueList.import`：`downloadTemplate` 下载模板 CSV / Download template CSV。中间的 `<code>cf.&lt;key&gt;</code>` 保留在模板里不翻译。前后两段分键：`helpBefore` 列需含 title；可选 issue_code（本工作区已存在则更新）。自定义字段用 / Columns must include title; optional issue_code (updates when it already exists in this workspace). Custom fields use；`helpAfter` 列（模板已含当前工作区字段；multi 逗号分隔，boolean 用 true/false）。未知 key 不阻断主字段写入。 / columns (the template already includes this workspace’s fields; separate multi values with commas, and use true/false for booleans). Unknown keys do not block writing the main fields.

### 3.5 提示 `page.issueList.messages`

锁定中英对照（节选键名，实施按 plan 全文写入）：`enterViewName` 请输入视图名称 / Enter a view name；`viewSaved` 视图已保存 / View saved；`sharedViewSaved` 共享视图已保存 / Shared view saved；`saveViewFailed` 保存视图失败 / Couldn’t save the view；`viewApplied` 已应用视图「{name}」 / Applied view “{name}”；`viewNotFound` 未找到该视图 / View not found；`applyViewFirst` 请先应用一个已保存视图 / Apply a saved view first；`sharedViewCantStar` 共享视图不支持收藏，可另存为个人视图后再收藏 / Shared views can’t be starred. Save as a personal view first；`starred` 已收藏 / Starred；`unstarred` 已取消收藏 / Star removed；`updateStarFailed` 更新收藏失败 / Couldn’t update the star；`pinnedToSidebar` 已收藏到侧栏 / Pinned to the sidebar；`unpinnedFromSidebar` 已从侧栏移除 / Unpinned from the sidebar；`updateSidebarPinFailed` 更新侧栏收藏失败 / Couldn’t update the sidebar pin；`savedAsPersonal` 已另存为个人视图 / Saved as a personal view；`saveAsFailed` 另存为失败 / Couldn’t save a copy；`copySuffix` （副本） / (copy)；`deleteTitle` 确认删除 / Delete issue；`deleteConfirmContent` 确定要删除问题 "{title}" 吗？ / Delete issue “{title}”?；`deleteSuccess` 问题删除成功 / Issue deleted；`deleteFailed` 问题删除失败 / Couldn’t delete the issue；`personalDefaultSaved` 已设为个人默认显示 / Saved as your personal default；`personalDefaultFailed` 保存个人默认失败 / Couldn’t save the personal default；`groupCfUnsupported` 该自定义字段类型不支持分组，已回退为不分组 / This custom field type can’t be used for grouping, so grouping was cleared；`savedGroupCfUnsupported` 已保存的分组自定义字段类型不受支持，已回退为不分组 / The saved grouping field type isn’t supported, so grouping was cleared；`swimlaneCfUnsupported` 该自定义字段类型不支持泳道，已回退为无泳道 / This custom field type can’t be used for swimlanes, so swimlanes were cleared；`savedSwimlaneCfUnsupported` 已保存的泳道自定义字段类型不受支持，已回退为无泳道 / The saved swimlane field type isn’t supported, so swimlanes were cleared；`groupSyncFailed` 分组已切换，但同步到已保存视图失败 / Grouping changed, but saving it to the view failed；`exportedCsv` 已导出 CSV / Exported CSV；`exportFailed` 导出失败 / Couldn’t export；`templateDownloadFailed` 模板下载失败 / Couldn’t download the template；`importFailed` 导入失败 / Couldn’t import；`noneCycle` 无 Cycle / No cycle。

源码里的「被阻塞 / 阻塞」计数若仍写死，一并改到 `page.issueList.blockedBy` / `blocks`（被阻塞 {count} / Blocked by {count}；阻塞 {count} / Blocks {count}），不要留在这一刀的可见铬里。

## 4. 验收

在最终干净 SHA、合成工作区、`http://127.0.0.1:<new-port>/issue/list` 上核对：

- `en-US` 浅色 1280×800、`en-US` 深色 1280×800（点击页眉主题，不重新加载；`html.dark` 为 true）、`en-US` 390×844：上述页签、工具条、列标题（390 首屏至少「编号 / Key」和「标题 / Title」）、「详情 / View」和「删除 / Delete」为英文；「开放中」页签是 Active，不是 Open；单元格状态徽章仍可以是 Open（对应待办），连同 Bug / Medium；页头仍是 Issues / New issue。
- `zh-CN` 浅色 1280×800：中文用词与改前一致（我的待办、详情、删除等），不是英文，也不是原始 key。
- 页面和文档标题不得出现 `page.issueList` 或其它原始 key。
- 不测焦点环，不量对比度，不把 390 首屏未出现的其余列当成失败。

源码合同由测试锁住：`surface.test.ts` 改为冻结 `$t` 键和布局原句（`white-space: normal`、`scroll-x="1400"`、`page.shell.noIssues` 等），不再冻结中文「详情 / 删除 / 确认删除」。另增测试断言 `page.issueList` 在 `en-us.ts`、`zh-cn.ts` 与 `frontend/src/typings/app.d.ts` 的 `App.I18n.Schema.page.issueList` 三者键齐全（测试必须读取 typings 源文件提取同一组键，不能只比较两份 locale，也不能只靠已失败的 vue-tsc 基线兜底），并抽查英文值不等于中文值，以及 `tabs.open` 英文为 Active 而非 Open。

## 5. 限制（照单保留）

盘点包 git-meta 无 pid 59419 / 63047 进程表原件；生成文件「启动后未变」无 sha256 原件；Vite 有 `VITE_OTHER_SERVICE_BASE_URL is not a valid json5 string`，未记录该值，页面仍渲染；深色当时只采了列表（本刀验收仍要采列表深色）；对比度未量；合成 token；假日包介绍未展开（与本刀无关，仍记录）。

本刀也不改焦点 CSS，不重做 `route.issue_edit`。

## 6. 实施边界

获批后从精确 `18a63574` 开普通隔离检出（`.git` 为目录，不是 worktree），再开分支。不改实施克隆、PR11 克隆、MAIN、PIN、OLD，不动 9541 pid 59419。白名单只允许文档、两份 locale、`app.d.ts`、`index.vue`、以及列表铬测试。先文档提交，再 RED，再改产品。四门禁与双 grok-4.7-high 按既有工作流。不 push、不开 PR、不 merge、不部署，停下来等验收。
