# 新建编辑与详情属性英文铬

Yuri 已独立核远端并限定交付 [PR13](https://github.com/WayJ/opentask/pull/13) `7aed13703c8b6e117db4d7f0c00b7f2069afa8d2`，并指定现在只写第 2 刀的 design/plan，代审后再 TDD。第 3 刀文档仍不写。建议 base 是当前已接受头 `7aed13703c8b6e117db4d7f0c00b7f2069afa8d2`（`cursor/issue-list-en-chrome-4333`）。获批前不建产品分支，不 commit，不改产品代码，不改 PR6–13 已存提交，不 merge，不部署。

证据：只读盘点包 sha256 `c681fcc704dc0588c06fb8cdeb7fbeee34c52314486b774cc637c232bb40cf55`（取自 PR12 tip `18a63574`）。PR13 的 8 个路径不含新建/编辑/详情页或 `constants/issue.ts`，这三份 Vue 与常量在 `7aed1370` 上与盘点时一致。本文字符串与行号以 GitHub raw 在 `7aed1370` 上的源文件为准：`frontend/src/views/issue/create/index.vue`（951 行）、`edit/index.vue`（768 行）、`detail/index.vue`（2899 行）。

## 1. 问题

英文下这三个视图的**文档标题**已经走路由键（Create Issue / Edit Issue / Issue Detail），不是本刀要修的泄漏。新建/编辑的**类型**下拉已经走 `useLabelTable('page.issueType')` + `labeledOptions`，原图上是 Bug。

同一屏仍有写死中文，浅色 1280 原图可见：

- 新建页内标题和主按钮「创建问题」（401、438 行）；属性卡「属性设置 / 类型 / 优先级 / 中 / 关联项目 / 选择项目（可选） / 高级选项」（551–620 行）。优先级选项直接绑 `issuePriorityOptions`，所以英文下仍显示「中 / 低 / 高 / 紧急」。
- 编辑页同样的属性卡，加上页内标题「编辑问题」（286 行）和主按钮「保存更改」（311 行）。
- 详情侧栏：「状态 / 待办」「指派人 / 未分配」「优先级 / 中」「冲刺 / 未分配」、已是英文的 Milestone、「类型 / Bug」「开始」「截止日期」「关注者 / 暂无关注者」「报告人」（1798–2019 行）。状态和优先级的展示值与选项来自 `issueStatusOptions` / `issuePriorityOptions` 的中文 `label`（232–233、1799、1870 行）。

`frontend/src/views/issue/create/surface.test.ts` 把其中几处中文冻在断言里（`创建问题`、`高级选项`、`关联任务 ID`、`关联需求 ID`、`负责人 ID`，以及范围外的 `使用模板` 和创建结果 toast）。改范围内文案时必须同步改这份测试，不能假装原文还在。编辑页 `surface.test.ts` 和详情 `focus.test.ts` / `description-surface.test.ts` 没有冻结这些标签。

## 2. 方案

只把这三个视图里、已划进本刀的用户可见写死中文改成 `$t` 或已有 label table，中英两套文案一起补。不改枚举值，不改 `frontend/src/constants/issue.ts` 的中文展示串，只把这三个视图切到已有表。

新键放在 `page.issueForm`，不要写进 `page.shell` 或 `page.issueList`。`frontend/src/typings/app.d.ts` 的 `App.I18n.Schema.page` 必须同步加上同一棵形状。`zh-cn.ts` 与 `en-us.ts` 的键集合必须与 Schema 一致。注意 Schema 里已有 `page.shell.issueForm: string`（导航「问题表单」）；本刀的 `page.issueForm` 是 `page` 下与 `issueList` 并列的**对象**。键完整性测试在 typings 里提取时，必须匹配 `issueForm\s*:\s*\{`，不得误打到前面那个字符串字段。

状态、优先级、类型的**选项值**必须复用已有表，不在 `page.issueForm` 里再造一套：

- 状态：`useLabelTable('page.issueStatus')` + `labeledOptions(issueStatusOptions.map(o => o.value), …)`。英文 `open` 是 Open，中文是待办。这与列表徽章同一对，本刀不得改成 To do / Backlog。
- 优先级：同样走 `page.issuePriority`。英文 `critical` 已是 **Urgent**（不是 Critical），中文是紧急。实施必须沿用表内用词。
- 类型：新建/编辑/详情侧栏已经这样接线，本刀保持，不重做。

`issueTypeOptions` / `issuePriorityOptions` / `issueStatusOptions` 仍只用来提供枚举 `value` 顺序，不把它们的中文 `label` 画到这三页上。

字段标签放在 `page.issueForm`，即使英文与列表列标题相同也不去引用 `page.issueList.columns.*`：列表「负责人」与侧栏「指派人」不是同一个中文词，不宜混用命名空间。

唯一允许跨命名空间复用的铬键：详情冲刺下拉的空项「无 Cycle」与列表已锁定的 `page.issueList.noneCycle`（无 Cycle / No cycle）逐字相同，直接复用，不另造。

编辑页今天没有 `import { $t } from '@/locales'`，实施时补上。新建页和详情页已经有。所有用 `$t` 拼出来的 computed（冲刺/指派人空态、状态/优先级 options）必须读取当前语言（`useLabelTable` 已会依 locale 重算；手写 `$t` 的 computed 要读 `locale` 或等价依赖），切换语言时侧栏和下拉要更新。

## 3. 范围

**在范围（Yuri 已划，必须）：**

- 新建/编辑页内标题与主操作：创建问题（标题与主按钮同一串）、编辑问题、保存更改。
- 属性卡标签：属性设置、类型、优先级、关联项目、选择项目（可选）、高级选项。
- 详情侧栏该列字段标签：状态、指派人、优先级、冲刺、类型、开始、截止日期、关注者、报告人。
- 这三页上状态/优先级选项值改走 `page.issueStatus` / `page.issuePriority`。

**在范围（同控件/同卡顺手带上，请一并拍板）：** 不扩到新视图，只避免范围内控件展开后仍留中文兄弟句。

- 属性卡同一套下拉的占位：选择类型、选择优先级（源码有，盘点未单列）。
- 「高级选项」展开后同一张卡里的：关联任务 ID、输入任务 ID、关联需求 ID、输入需求 ID、负责人 ID、输入负责人 ID。源码无省略号，折叠按钮文案就是「高级选项」。
- 侧栏空态与编辑占位：未分配（指派人/冲刺的展示回退和 placeholder）、暂无关注者、未设置（仅报告人的展示回退和 placeholder）、选择指派人（首位=负责人）、选择冲刺、选择报告人。
- 冲刺下拉空项「无 Cycle」复用 `page.issueList.noneCycle`。

「未分配」在详情里还用作 Milestone 的展示回退和 placeholder（`milestoneDisplayValue` 与 placeholder，约 197、1913 行），与冲刺/指派人是同一句中文。已确认这是对「不改 Milestone」的狭义例外：这两处**允许**接 `page.issueForm.unassigned`，英文为 Unassigned。**不改** Milestone 标签，也不改「无 Milestone」「选择 Milestone」。

**不在范围：** 描述编辑区铬（描述、Markdown 提示、预览、语法帮助、字符、占位「输入问题标题… / 详细描述这个问题…」）；使用模板及其说明「从模板创建问题」；预览/编辑模式切换；附件卡；「自定义字段（可选）」；返回列表 (Esc) / 返回详情 (Esc)；未保存；退出确认框；创建/保存/更新类 toast 与校验句（如「请输入问题标题」「问题创建成功」）；详情顶栏其余项，以及顶栏里 `startEdit('status'` 按钮上的「状态」（约 1517 行，不是侧栏的 `label="状态"`）；评论、附件、子问题、关联关系、Agent 指令正文。Agent 指令生成器里负责人回退的「未分配」（约 419 行）必须保留写死。侧栏未列入的字段（项目、估点、工时）及它们的「未设置」保持写死。关注者行里的「取消」；看板/批量/快捷；第 3 刀 SLA / 回收站；`constants/issue.ts`；已接受的列表铬和焦点规则；PR6–13 头。路由标题不重做。禁止全局替换「未分配」「未设置」。

下面是锁定文案。实施不得另撰英文。中文保持现有用户可见用词，只是改成键。内页标题用句式大小写（Create issue），与列表铬（New issue、Save view）一致；文档标题仍是路由里已有的 Title Case（Create Issue / Edit Issue），本刀不改路由键。不要复用 `page.shell.createIssue`（新建问题 / New issue）或 `route.issue_create`（问题登记 / Create Issue）来表示「创建问题」。不要复用 `route.issue_edit` 来表示页内「编辑问题」，以免和文档标题的 Edit Issue 绑死大小写。

冲刺在产品里是 `cycle_id` + `fetchCycles`，已有产品英文是 Cycle（`page.issueList` 过滤项、`page.shell.groupCycles` 为 Cycles）。英文锁定 **Cycle**，不用 Sprint。

### 3.1 页内标题与主操作 `page.issueForm`

| 键 | zh-CN | en-US |
|---|---|---|
| createTitle | 创建问题 | Create issue |
| editTitle | 编辑问题 | Edit issue |
| saveChanges | 保存更改 | Save changes |

`createTitle` 同时用于新建页标题和主按钮，因为源码是同一句中文。测试必须真正锁住这两处：该 `$t` 键出现两次，且标题 NText 字面量和主按钮那一行独立的「创建问题」都已消失。

### 3.2 属性卡 `page.issueForm`

| 键 | zh-CN | en-US |
|---|---|---|
| propertySettings | 属性设置 | Property settings |
| type | 类型 | Type |
| priority | 优先级 | Priority |
| linkedProject | 关联项目 | Linked project |
| selectProjectOptional | 选择项目（可选） | Select project (optional) |
| selectType | 选择类型 | Select type |
| selectPriority | 选择优先级 | Select priority |
| advanced | 高级选项 | Advanced options |
| linkedTaskId | 关联任务 ID | Linked task ID |
| enterTaskId | 输入任务 ID | Enter task ID |
| linkedRequirementId | 关联需求 ID | Linked requirement ID |
| enterRequirementId | 输入需求 ID | Enter requirement ID |
| assigneeId | 负责人 ID | Assignee ID |
| enterAssigneeId | 输入负责人 ID | Enter assignee ID |

`type` / `priority` 也用于详情侧栏同名标签，不拆第二套键。中文「选择项目（可选）」保持全角括号；英文用半角括号。

### 3.3 详情侧栏 `page.issueForm`

| 键 | zh-CN | en-US |
|---|---|---|
| status | 状态 | Status |
| assignee | 指派人 | Assignee |
| cycle | 冲刺 | Cycle |
| start | 开始 | Start |
| dueDate | 截止日期 | Due date |
| watchers | 关注者 | Watchers |
| reporter | 报告人 | Reporter |
| unassigned | 未分配 | Unassigned |
| unset | 未设置 | Not set |
| noWatchers | 暂无关注者 | No watchers |
| selectAssignees | 选择指派人（首位=负责人） | Select assignees (first is primary) |
| selectCycle | 选择冲刺 | Select cycle |
| selectReporter | 选择报告人 | Select reporter |

`assignee` 的中文必须是「指派人」，不要改成列表列标题的「负责人」。英文 Assignee 与列表列标题相同，但是新键。`selectAssignees` 里的 first is primary 与详情侧栏头像已有的英文 title 后缀 `(primary)` 对齐。

复用、不写进本表：`page.issueList.noneCycle` = 无 Cycle / No cycle。

### 3.4 已有选项表（只接线，不改表）

`page.issueStatus`：待办 / Open，进行中 / In progress，等待反馈 / Waiting for feedback，已解决 / Resolved，已关闭 / Closed，已拒绝 / Rejected。

`page.issuePriority`：低 / Low，中 / Medium，高 / High，紧急 / Urgent。

`page.issueType`：缺陷 / Bug，功能 / Feature，问题 / Question，反馈 / Feedback，事件 / Incident，改进 / Improvement（已接线）。

## 4. 验收

- 英文浅色 1280×800，新建/编辑/详情各一张原图：范围内铬为第 3 节锁定英文，不是中文，不是原始 key。状态徽章/选项在 `open` 时是 Open；优先级 `medium` 是 Medium，`critical` 是 Urgent。类型仍是 Bug 等已有英文。
- 中文浅色 1280×800 对照：中文用词与改前一致（创建问题、编辑问题、保存更改、属性设置、指派人、冲刺、待办、中 等），不是英文，也不是原始 key。
- 切换语言后，页内标题、属性卡、侧栏标签和状态/优先级选项不必整页重载即可更新。
- 页面和文档标题不得出现 `page.issueForm` 或其它原始 key。文档标题仍是 Create Issue / Edit Issue / Issue Detail。
- 「使用模板」及其说明「从模板创建问题」、描述区、附件卡、「自定义字段（可选）」、详情顶栏（含 `startEdit('status'` 上的「状态」）、评论区仍可保持现有中文，不视为本刀失败。
- Milestone 标签在两种语言下仍是 Milestone；「无 Milestone」「选择 Milestone」保持原样。共享的「未分配」展示回退和 placeholder（约 197、1913 行）按第 3 节接线后，Milestone 空态为 Unassigned。
- 不测焦点环，不量对比度。不改 `constants/issue.ts`。其它调用方若仍读该文件的中文 `label`，保持原样。

源码合同由测试锁住。

`create/surface.test.ts` 必须断言 `$t('page.issueForm.createTitle')` **出现两次**（标题 NText 和主按钮各一次）。标题字面量 `<NText strong style="font-size: 16px; margin-left: 12px">创建问题</NText>` 必须消失；主按钮那一行独立的「创建问题」（源码约 438 行，行内只有缩进和这四个字）也必须消失。不要只用 `not.toContain('>创建问题<')`，它只能抓到标题，抓不到按钮那一行。也不要写 `not.toContain('创建问题')`，它会误伤范围外的「从模板创建问题」。同一文件继续冻结范围外的「使用模板」「从模板创建问题」和创建结果 toast，以及范围内的 `page.issueForm.advanced` 与高级选项三个标签键。

另增 `frontend/src/locales/__tests__/issue-form-property-chrome.test.ts`：断言 `page.issueForm` 在 `en-us.ts`、`zh-cn.ts` 与 typings Schema 三者键齐全（必须读取 typings 源文件，按对象形状提取，不能只比较两份 locale，也不能只靠已失败的 vue-tsc 基线兜底），抽查锁定值（含 `createTitle` 英文为 Create issue 而非 New issue 或 Create Issue，`cycle` 英文为 Cycle 而非 Sprint，`assignee` 中文为指派人，`page.issuePriority.critical` 英文仍为 Urgent），并断言三份 Vue 已接到 `$t('page.issueForm…')` / `useLabelTable('page.issueStatus'|'page.issuePriority')`，且 `constants/issue.ts` 仍含中文「待办」「紧急」。这份银测试还要锁：编辑页字面量「保存更改」消失（不只是 `saveChanges` 的 `$t` 出现）；详情顶栏 `startEdit('status'` 按钮仍含文本「状态」；Agent 指令里负责人三元的「未分配」仍在；`label="Milestone"`、`'无 Milestone'`、`选择 Milestone` 仍在；项目/估点仍是 `placeholder="未设置"`。编辑/详情既有 surface 与 focus 测试不改职责。

## 5. 限制（照单保留）

盘点包 git-meta 无 pid 59419 / 63047 进程表原件；生成文件「启动后未变」无 sha256 原件；Vite 有 `VITE_OTHER_SERVICE_BASE_URL is not a valid json5 string`，未记录该值，页面仍渲染；盘点深色当时只采了列表（本刀验收按第 4 节采新建/编辑/详情浅色；深色不作本刀失败条件，有余力可附一张详情深色）；对比度未量；合成 token。

本刀也不改焦点 CSS，不重做 `route.issue_edit` / `route.issue_create`，不改 PR13 已存两个提交。

## 6. 实施边界

获批后从精确 `7aed13703c8b6e117db4d7f0c00b7f2069afa8d2` 开普通隔离检出（`.git` 为目录，不是 worktree），再开分支。不改实施克隆、PR11 克隆、MAIN、PIN、OLD，不动 9541 pid 59419，不改写已验 SHA。白名单只允许文档、两份 locale、`app.d.ts`、新建/编辑/详情三份 `index.vue`、`create/surface.test.ts`、以及本刀铬测试。先文档提交，再 RED，再改产品。四门禁与双 grok-4.7-high 按既有工作流。不 push、不开 PR、不 merge、不部署，停下来等验收。第 3 刀不得在本计划内开写。
