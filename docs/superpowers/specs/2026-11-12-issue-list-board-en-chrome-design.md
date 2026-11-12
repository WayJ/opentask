# 问题列表看板英文铬

第 6 刀 design 草稿，送 Yuri 代审；没有审批结论。未来 repo 路径：`docs/superpowers/specs/2026-11-12-issue-list-board-en-chrome-design.md`。本文与 plan 是一组。盘点报告在 `/workspace/designs/post-pr17-polish-inventory/INVENTORY.md`，摘录在同目录 `priority-surfaces.md`，都不入库。行号与现文案以精确 base `6b6ad3b4784fd65ce917c42fb3ec978c10e4b557`（PR17 tip）上的盘点与摘录为准。不要用 `290c3ed3` 当实施 base。

## 1. 问题与证据

PR17 已限定交付。本刀起点为 `6b6ad3b4784fd65ce917c42fb3ec978c10e4b557`。`en-us.ts` 无汉字。`fallbackLocale` 是 `'en'`，注册的语言只有 `'zh-CN'` 和 `'en-US'`，缺 key 不会退回中文。英文界面上还能看见的中文，通常是写死字符串，或被上一刀测试冻住、故意不走 `$t` 的文案。

第 5 刀详情宿主铬已经在 tip 上，不是本刀范围，也不要重开。列表工具栏、筛选、语法帮助、分组下拉和搜索框由列表传入的占位已经是 `$t`。`views/issue/list/index.vue` 的 `<template>` 里没有汉字。切到看板、打开「显示」、多选，或在搜索框里看建议和已解析芯片时，仍掉回整块中文。这是问题页这条序列上，详情宿主译完之后最大的接缝，也是盘点第 6 节建议的第一片。

盘点已复核：`page.issueList.messages.noneCycle` 与 `page.issueList.noneCycle` 的英文都是 “No cycle”，不要为合并 key 开片。壳层收藏 / 工作区 / 快捷键（第二片）以及创建页「自定义字段（可选）」和编辑页「加载中...」（第三片）真实存在，本刀只在范围外说明，不实施。

## 2. 方案与推荐

在已有 `page.issueList` 下增设清晰分组：`board`、`displayOptions`、`bulk`、`search`、`searchSuggestions`，并同步 `App.I18n.Schema`。页级与只被列表引用的组件继续用已有的 `@/locales` `$t`。已有可复用的整句优先复用，不造近义 key。卡片优先级与批量条状态下拉改走已有 `useLabelTable` / `lookupLabel`，不改 `constants/issue.ts`。显示选项在组件内覆盖常量表与公式后缀，不改 `display-prefs.ts` 的源串。搜索建议只译 `generateSearchSuggestions` 横线后的说明。

不把这些键塞进 `page.issueForm` 或 `page.issueDetail`。也不改先做壳层或创建/编辑各剩一句。

脚本里若新增调用 `$t` 的 computed，或会缓存文案的函数（含 `generateSearchSuggestions`、批量条 `countLabel`、显示选项泳道/字段 computed、搜索芯片 `activeFilters`），第一句必须是 `void locale.value;`，位于任何短路之前。`no-void` 只用 `eslint-disable-next-line` 盖住这一句，或紧贴该 computed / 函数的 disable/enable 块。禁止文件级 `eslint-disable no-void`。模板里的 `$t` 不包 computed。命名参数插值必须写成 `$t('…', { n: … })` 或 `$t('…', { count: … })`（与已有键签名一致），禁止 `.replace('{n}'`、`.replace('{count}'` 或同类字符串替换迁就测试。

不要把既有 `$t` 改成局部 `t()`。不要为了测试删掉 `useI18n` 或改组件 identity。`IssueSmartSearch` 优先继续用从 `@/locales` 导入的 `$t` / `locale`，不要无故改成 `useI18n()`，以免 `tests/issue/index.test.ts` 的既有挂载无插件就失败。

## 3. 锁定文案

英文 in-page copy 用 sentence case。中文逐字保留，包括 ASCII `...`、全角括号、`≤`、`depth-1`、`Sprint`、`bug`、`<id>`、`range`、`E46`、`cf:key:value` 以及语法 token。`en-us.ts` 不得有汉字。不改 route 键值。不改已复用键的既有译文。下面「调用」按盘点可见点计；实施时以 tip 源码为准，测试按实际调用次数钉死。

被阻塞 / 阻塞已有键的插值是 `{count}`，不是 `{n}`。产品侧必须 `$t('page.issueList.blockedBy', { count: … })` / `$t('page.issueList.blocks', { count: … })`，禁止 `.replace`。批量条「已选 {n} 项」和图标集「{n} 条规则」用 `{n}`。

### 复用已有键（不新造近义句）

| 表面 | 中文 | 键 | 英文 |
|---|---|---|---|
| 看板空状态；分组空状态 | 暂无问题 | `page.shell.noIssues` | No issues |
| 看板卡片「被阻塞 {n}」 | 被阻塞 {count} | `page.issueList.blockedBy` | Blocked by {count} |
| 看板卡片「阻塞 {n}」 | 阻塞 {count} | `page.issueList.blocks` | Blocks {count} |
| 看板卡片「估点」 | 估点 | `page.issueList.columns.estimate` | Estimate |
| 看板卡片「项目」 | 项目 | `page.issueList.filters.project` | Project |
| 看板卡片「冲刺」；批量条占位「冲刺」 | 冲刺 | `page.issueForm.cycle` | Cycle |
| 看板卡片优先级标签 | 低 / 中 / 高 / 紧急 | `page.issuePriority.*`（`useLabelTable` + `lookupLabel`） | 已有译文 |
| 显示选项字段「编号」 | 编号 | `page.issueList.columns.key` | Key |
| 显示选项字段「负责人」；批量条占位「负责人」；芯片「负责人」 | 负责人 | `page.issueList.columns.assignee` | Assignee |
| 显示选项字段「优先级」；芯片「优先级」 | 优先级 | `page.issueList.columns.priority` | Priority |
| 显示选项字段「标签」；芯片「标签」；泳道选项「标签」 | 标签 | `page.issueList.groupBy.label` | Label |
| 显示选项字段「类型」；芯片「类型」 | 类型 | `page.issueList.columns.type` | Type |
| 显示选项字段「估点」 | 估点 | `page.issueList.columns.estimate` | Estimate |
| 显示选项字段「截止日期」 | 截止日期 | `page.issueForm.dueDate` | Due date |
| 显示选项字段「项目」；芯片「项目」 | 项目 | `page.issueList.filters.project` | Project |
| 显示选项「重置」 | 重置 | `common.reset` | Reset |
| 泳道选项「负责人」 | 负责人 | `page.issueList.groupBy.assignee` | Assignee |
| 泳道选项「优先级」 | 优先级 | `page.issueList.groupBy.priority` | Priority |
| 泳道选项「类型」 | 类型 | `page.issueList.groupBy.type` | Type |
| 泳道下拉公式后缀 | （计算值·只读） | `page.issueList.computedFieldSuffixReadonly` | (computed, read-only) |
| 批量条占位「状态」；芯片「状态」 | 状态 | `page.issueForm.status` / `page.issueList.columns.status`（同句，占位用 `issueForm.status`，芯片用 `columns.status`） | Status |
| 批量条占位「优先级」 | 优先级 | `page.issueForm.priority` | Priority |
| 批量条「取消 (Esc)」里的「取消」 | 取消 | `common.cancel`，模板再接 ` (Esc)` | Cancel |
| 芯片「报告人」 | 报告人 | `page.issueList.columns.reporter` | Reporter |
| 芯片「搜索」 | 搜索 | `common.search` | Search |
| 搜索建议「只显示待办中的问题」 | 只显示待办中的问题 | `page.issueList.syntax.isOpen` | Show only open issues |
| 搜索建议「只显示已完成的问题」 | 只显示已完成的问题 | `page.issueList.syntax.isClosed` | Show only completed issues |
| 搜索建议「只显示进行中的问题」 | 只显示进行中的问题 | `page.issueList.syntax.isInProgress` | Show only in-progress issues |
| 搜索建议「只显示紧急优先级的问题」 | 只显示紧急优先级的问题 | `page.issueList.syntax.priorityUrgent` | Show only urgent-priority issues |
| 搜索建议「指派给我」 | 指派给我 | `page.issueList.scopeTitle.assignedToMe` | Assigned to me |

「指派给我」与 `syntax.assigneeMe`（「显示分配给我的问题」）不是同一句，禁止复用那个近义键。它与已有 `page.issueList.scopeTitle.assignedToMe`（指派给我 / Assigned to me）是同一句，按「已有整句优先复用，禁止近义新键」复用该键，不新造一份相同的 searchSuggestions 键。

不要复用：

- `page.issueForm.dueDate` 去当看板卡片短标签「截止」（该键中文是「截止日期」，复用会把卡片改长）
- `page.issueForm.unassigned` 去当卡片「未指派」（该键中文是「未分配」，`zh-cn.ts:571`；复用会把卡片中文改掉）。旧盘点把该键中文记成「未指派」，本 tip 上不成立。
- `page.issueList.filters.cycle` 去覆盖显示选项字段名里已经是拉丁字母 `Cycle` 的那一项（该键中文是「冲刺」）
- `page.issueList.groupBy.none`（不分组 / No grouping）去当「无泳道」
- `common.confirm`（确认 / Confirm）去当批量条「应用」
- 整句复用 `common.cancel` 去当「取消 (Esc)」；只复用「取消」，再在模板接 ` (Esc)`
- `page.issueForm.assignee`（指派人）去当批量条或芯片的「负责人」
- `page.issueList.messages.personalDefaultSaved`（已设为个人默认显示 / Saved as your personal default）去当按钮「设为个人默认」
- `page.issueList.noneCycle` / `messages.noneCycle`（无 Cycle / No cycle）去当建议说明「无冲刺」
- `page.issueList.syntax.assigneeMe`、`syntax.typeFeature`、`syntax.customField` 去当对应建议说明（近义不同句）
- `page.shell.searchIssues`（列表已传入的占位，Search issue number or title...）去改写或替换 `IssueSmartSearch` 的组件默认占位

批量条 Labels 占位在 tip 上已经是拉丁字母 `Labels`，保持原样。芯片值（`open`、用户 id、标签名、`cf.key` 等）是数据或 token，不译。芯片短标签在模板里再加冒号，不要把冒号烤进新句子。芯片 `Cycle:` 已是拉丁字母，改走下面的 `displayOptions.fieldCycle`（中英文都是 `Cycle`）再在模板加冒号，不要用 `filters.cycle`。

### `page.issueList.board`（新键）

| 键 | zh-CN | en-US |
|---|---|---|
| `unassigned` | 未指派 | Unassigned |
| `due` | 截止 | Due |
| `moveFailed` | 看板移动失败 | Couldn’t move the issue |
| `groupedListHint` | 列表分组为展示泳道；泳道内 depth-1 嵌套。跨泳道拖拽改字段不在本 Sprint 范围。 | Grouped list is a display swimlane; issues nest at depth-1 inside a lane. Dragging across lanes to change a field is out of scope for this Sprint. |

`groupedListHint` 保留 `depth-1` 与 `Sprint`。`moveFailed` 覆盖 `IssueBoard.vue:214` 与 `:224` 两处 toast。

### `page.issueList.displayOptions`（新键）

| 键 | zh-CN | en-US |
|---|---|---|
| `title` | 显示选项 | Display options |
| `cardFields` | 卡片字段 | Card fields |
| `customFieldColumns` | 自定义字段列 | Custom field columns |
| `boardSwimlanes` | 看板泳道 | Board swimlanes |
| `hideEmptyLanes` | 隐藏空泳道 | Hide empty swimlanes |
| `conditionalFormats` | 条件格式（≤10） | Conditional formats (≤10) |
| `remove` | 删 | Delete |
| `addRule` | 添加规则 | Add a rule |
| `colorScales` | 色阶（≤5） | Color scales (≤5) |
| `addColorScale` | 添加色阶 | Add a color scale |
| `iconSets` | 图标集（≤5） | Icon sets (≤5) |
| `ruleCount` | {n} 条规则 | {n} rules |
| `addIconSet` | 添加图标集 | Add an icon set |
| `setPersonalDefault` | 设为个人默认 | Set as your personal default |
| `noSwimlane` | 无泳道 | No swimlane |
| `fieldCycle` | Cycle | Cycle |

`conditionalFormats` / `colorScales` / `iconSets` 的中文全角括号与 `≤10` / `≤5` 逐字保留。`ruleCount` 用于 `DisplayOptionsPanel.vue:204` 的 `{{ iset.rules.length }} 条规则`，写成 `$t('page.issueList.displayOptions.ruleCount', { n: iset.rules.length })`。「重置」复用 `common.reset`，不进本表。

`fieldCycle` 中文仍写 `Cycle`，不是「冲刺」。显示选项字段勾选与搜索芯片的 Cycle 短标签都走此键。

公式字段泳道选项：在 `DisplayOptionsPanel` 内按列表页已有桥的同样方式，用源串 `（计算值·只读）` 做 `endsWith`，再替换成 `$t('page.issueList.computedFieldSuffixReadonly')`。不改 `display-prefs.ts:510`，不改 `groupIssuesBy.ts:341`，不改 `list/index.vue` 的桥。

### `page.issueList.bulk`（新键）

| 键 | zh-CN | en-US |
|---|---|---|
| `selected` | 已选 {n} 项 | Selected {n} items |
| `apply` | 应用 | Apply |
| `selectFieldWarning` | 请至少选择一项要修改的字段 | Select at least one field to change |
| `updateFailed` | 批量更新失败 | Couldn’t update in bulk |
| `updateSuccess` | 批量更新成功 | Updated in bulk |

`selected` 用于 `IssueBulkBar.vue:30` 的 `countLabel` computed：第一句 `void locale.value;`，然后 `$t('page.issueList.bulk.selected', { n: selection.count.value })`。`updateFailed` 覆盖 `:73` 与 `:85`。状态下拉 / 优先级下拉的可见汉字来自 `constants/issue.ts`，本刀只在批量条用 `useLabelTable('page.issueStatus')` / `useLabelTable('page.issuePriority')` 与 `lookupLabel` 覆盖 options 的 `label`，常量本身留给壳层快捷键浮层。

### `page.issueList.search`（新键，组件默认占位与芯片铬）

| 键 | zh-CN | en-US |
|---|---|---|
| `defaultPlaceholder` | 搜索问题... (支持 is:open, field:key:value 等) | Search issues... (supports is:open, field:key:value, and similar) |
| `appliedFilters` | 应用过滤器 | Applied filters |
| `field` | 字段 | Field |

`defaultPlaceholder` 中文逐字保留 ASCII `...`、半角括号与 token `is:open`、`field:key:value`。只作组件 `withDefaults` 在未传入 `placeholder` 时的默认值。列表 `:1795` 已传入 `$t('page.shell.searchIssues')`，不要改那一句，也不要把默认值改成那一句。

`appliedFilters` 在模板里再接冒号，例如 `$t('page.issueList.search.appliedFilters') + ':'` 或模板 `{{ … }}:`。`field` 用于 `字段 ${cf.key}: ${cf.value}`，不要把冒号或 key 烤进句子。

### `page.issueList.searchSuggestions`（新键，决定 F）

只译横线后的说明。语法 token 原样保留：`is:open`、`is:closed`、`is:in_progress`、`assignee:@me`、`label:bug`、`type:feature`、`priority:urgent`、`cycle:__none__`、`project:<id>`、`field:severity:s1`、`field:score:10`、`cf:score>=8`。`bug`、`<id>`、`range`、`E46`、`cf:key:value` 保留。

| 键 | 用于建议 | zh-CN | en-US |
|---|---|---|---|
| `labelBug` | `label:bug` | 只显示标签为 bug 的问题 | Show only issues labeled bug |
| `typeFeature` | `type:feature` | 只显示类型为功能的问题 | Show only issues whose type is feature |
| `cycleNone` | `cycle:__none__` | 无冲刺 | No cycle |
| `filterByProject` | `project:<id>` | 按项目过滤 | Filter by project |
| `customField` | `field:severity:s1` | 自定义字段过滤（cf:key:value 亦可） | Custom field filter (cf:key:value also works) |
| `formulaEquals` | `field:score:10` | 公式字段按计算值等值过滤（只读） | Filter a formula field by exact computed value (read-only) |
| `formulaRange` | `cf:score>=8` | 公式/数字字段 range 过滤（E46） | Formula/number field range filter (E46) |

`typeFeature` 不要写成 `syntax.typeFeature`（「只显示功能类型的问题」/ Show only feature issues）。`customField` 不要写成 `syntax.customField`（「按自定义字段过滤（亦可用 cf:key:value）」）。`cycleNone` 的中文必须是「无冲刺」，即使英文与 `noneCycle` 同为 No cycle 也要新键，不能把中文改成「无 Cycle」。

`generateSearchSuggestions` 内拼接为 `` `${token} - ${$t('…')}` ``，函数开头 `void locale.value;`。`tests/issue/index.test.ts:111-114` 只断言 token，不要削弱。

## 4. 范围

**范围内**

- `IssueBoard.vue`：空状态、卡片「未指派」、被阻塞 / 阻塞计数、估点 / 截止 / 项目 / 冲刺标签、优先级标签改 `lookupLabel`、`:214` / `:224` toast「看板移动失败」。列头与状态/类型/优先级泳道已经在用 `useLabelTable` 的保持。不要在组件里按四个桶常量覆盖泳道标题。
- `DisplayOptionsPanel.vue`：面板标题与各节标题、字段名勾选（常量表在组件内映射）、泳道下拉（内建项 + 公式后缀替换 + 「无泳道」）、「隐藏空泳道」、条件格式 / 色阶 / 图标集铬、「删」「添加规则」「添加色阶」「添加图标集」「设为个人默认」，「重置」复用 `common.reset`。自定义字段列的 `opt.name` 是字段名数据，不译。
- `IssueListGrouped.vue`：空状态与底部脚注。`bucket.label` 四个桶字按决定 E 先留。
- `IssueBulkBar.vue`：已选计数、占位、应用、取消 (Esc)、三则 toast、状态/优先级 options 的 label 覆盖。不改 Labels 占位。不改常量文件。
- `IssueSmartSearch.vue`：组件默认占位、芯片短标签与「应用过滤器」。不改列表传入的 placeholder。不译芯片值。
- `issueSearchParser.ts` 仅 `generateSearchSuggestions`（约 `:307-321`）的说明半句。
- 语言包 `en-us.ts` / `zh-cn.ts`、`frontend/src/typings/app.d.ts`。
- 新建 `frontend/src/locales/__tests__/issue-list-board-chrome.test.ts`。
- 实施时 `cmp` 已批原文进入 `docs/superpowers/specs/2026-11-12-issue-list-board-en-chrome-design.md` 与 `docs/superpowers/plans/2026-11-12-issue-list-board-en-chrome.md`。
- `tests/issue/index.test.ts` 仅当不改产品 identity 的前提下，既有挂载因缺少 i18n plugin 而无法跑住时，才允许补 `plugins: [i18n]`（真实 `@/locales`），且不得削弱 token 断言。能不改就不改。

**范围外**

- `views/issue/list/index.vue` 已 `$t` 的工具栏、语法帮助、搜索占位、公式后缀桥（`:144` 与 `:157-160`）
- `groupIssuesBy.ts` 及 `groupIssuesBy.test.ts`（四个桶字「未分配」「无标签」「空」「计算错误」与相等比较；`GROUP_BY_OPTIONS`）
- `display-prefs.ts` 的「（计算值·只读）」源串（`:510`）以及布尔「是/否」（`:490`；`common.yesOrNo` 已有 Yes/No，默认不进本刀，只记为限制）
- `constants/issue.ts`
- `detail/index.vue`、PR17 范围断言、`MarkdownEditor.vue`、`AttachmentList`、自定义字段内部、设置页、大模块、`noneCycle` 键合并、命令面板 keywords、用户内容/协议词
- 详情回复条「回复 @…」、SLA 剩余/逾期/已用时长、`EntityDocsPanel`、详情 toast
- 壳层（盘点第二片）：收藏、工作区切换、实时连接、快捷键浮层、命令面板估点动作
- 创建页「自定义字段（可选）」、编辑页「加载中...」、创建/编辑 toast、`IssueTemplateForm` 的「请填写」
- 不 merge、不部署、未经再授权不 push、不开新 PR。不改写 PR6–17 已存提交或头 SHA

## 5. 决定（批准前确认）

按盘点推荐案写入本文，作为本刀锁定建议，供 Yuri 确认。否决任一条，先改 design 与 plan，再实施。

- **E（推荐，本刀锁定）。** 不改源字符串「（计算值·只读）」。显示选项泳道下拉在 `DisplayOptionsPanel` 内按后缀替换成已有 `page.issueList.computedFieldSuffixReadonly`。不改 `groupIssuesBy.ts`。泳道/分组标题上的「未分配」「无标签」「空」「计算错误」本刀先留。卡片「未指派」走新键 `page.issueList.board.unassigned`，中文仍是「未指派」，英文 Unassigned；**禁止**复用 `page.issueForm.unassigned`。不要在组件里默默覆盖四个桶字。是否改分组函数或仅做显示覆盖，另定。
- **F（推荐，本刀锁定）。** 只译 `generateSearchSuggestions` 横线后的说明，语法 token 不动。与 `page.issueList.syntax.isOpen` / `isClosed` / `isInProgress` / `priorityUrgent` 同句的才复用这些 syntax 键。「指派给我」不复用近义的 `syntax.assigneeMe`，但复用同句的 `scopeTitle.assignedToMe`。「只显示类型为功能的问题」「自定义字段过滤（cf:key:value 亦可）」「无冲刺」以及没有同句的几条走 `searchSuggestions` 新键，不要硬复用近义句。`bug`、`<id>`、`E46`、`range`、token 本身保留。
- 本刀只实施盘点第一片。第二片（壳层）与第三片（创建/编辑各剩一句）存在，但不在本刀实施。不要改先做壳层来回避 E/F。

## 6. 测试与验收口径

- 新测试统计 `$t('…')` 调用点，字面缺失用精确正则。禁止宽泛的 `not.toContain('取消')` / `('状态')` / `('重置')` / `('应用')`。
- 真实 `@/locales` 切换 `zh-CN` / `en-US`。不要自己造一套残缺 messages。
- `blockedBy` / `blocks` 必须是 `$t('…', { count: … })`，并 `not.toContain(".replace('{count}'")` 与 `not.toContain(".replace('{n}'")`。`bulk.selected` 与 `displayOptions.ruleCount` 必须是 `$t('…', { n: … })`。
- 有 `useI18n()` 的组件，Vue Test Utils 挂载必须 `plugins: [i18n]`（已有 pinia 则 `[pinia, i18n]`）。不要为了测试删掉 `useI18n` 或改组件 identity。Vue Test Utils stub 必须同时覆盖 naive-ui 真实 `name` 与 `N*` 别名。
- `tests/issue/index.test.ts` 的 token 断言（`is:open`、`label:bug`、`type:feature`、`priority:urgent`）不得削弱。若必须加 i18n plugin 才能挂住 `IssueSmartSearch`，须把该文件列为白名单修订，只补 plugin，不改 token 期望。
- 正向保留：`groupIssuesBy.ts` 仍含四个桶字源串；`groupIssuesBy.test.ts:70` 仍是「未分配」；`display-prefs.ts:510` 仍拼「（计算值·只读）」；`:490` 仍是「是」/「否」；`list/index.vue` 后缀桥仍在；`constants/issue.ts` 的中文 label 仍在；`IssueSmartSearch` 默认占位被换绑后，列表传入的 `page.shell.searchIssues` 仍在 `list/index.vue:1795`。
- 四门对照当次干净 `6b6ad3b4` 基线。tsc/eslint 基线非 0 则保持 added 0 / removed 0，不得写成全绿，不得借用 PR15/PR16/PR17 的失败行号。不能写 dual Grok Approve。
- 不要求本刀截图作为验收门。若实施时拿得到，只作为附证。
- 证据包必须含每一笔提交相对其第一父提交的 name-only、diffstat 与完整 diff，以及相对精确 base 的 `final.diff`。不得只用 `final.diff`。第一笔（docs）的分笔 diff 须恰好是两份 docs。若后来多出修订笔，每一笔同样要有这三份，不要 amend 前序提交来补证据。

## 7. 限制（写入验收说明）

- 第一次在仓库根提交若再出现 `Script not found "sa"`，必须 STOP 并记入限制；plan 已收入第 4 刀已接受的根 hook 拷贝与 gitignore 相对软链步骤，避免再踩同一坑，但那不是改 hook 正文。
- commit hook EXIT 0 不是路径证明，需要 strace 显示只读打开克隆根 `.git/COMMIT_EDITMSG`。
- `.env.prod` 不得入库、不得把正文写入证据包。prod build 只允许使用 sha256 仍为 `b686d37a6c470d295b5cf4165eea1c3a6ca3a43fcc08d0155b5a27634d2d2ce7`（1896 字节）的已核 `.env.prod` 副本；哈希不符或缺失则该门记 EXIT STOP（与 PR17 相同限制，不是本刀开写或必修复项），不用 `.env.example` 顶替，也不因此中断 TDD 与其它门禁。
- prod build 若弄脏 `frontend/src/typings/components.d.ts`，必须从仓库根 `git checkout --` 再跑 tsc/eslint，打包还原前后 porcelain，不提交该文件。
- 列表自定义字段布尔格的「是 / 否」（`display-prefs.ts:490`）本刀不译，英文列表自定义字段列会继续出现中文「是/否」，直到另有授权。
