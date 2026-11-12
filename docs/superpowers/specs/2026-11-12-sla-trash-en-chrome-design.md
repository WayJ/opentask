# SLA 与回收站英文铬

第 3 刀 design 草稿，送 Yuri 代审；没有审批结论。未来 repo 路径：`docs/superpowers/specs/2026-11-12-sla-trash-en-chrome-design.md`。本文与 plan 是一组，不把盘点旧 base 当新执行基线。

## 1. 问题与证据

PR14 已限定交付；本刀起点为 `5bc1f604a22aad1517eaeae16ada004ba14fc11a`。`source/` 保存本次引用原件（不是交付文档）：

- `sla-index.vue`，28804 字节，sha256 `af6142b9479fd381cd2cf5d003523e04315d1a7d4a7c8d033724f900cb1ac401`；与 `trash-index.vue`、两份 locale、`frontend__src__typings__app.d.ts`、`issueTrashMeta.ts` 及测试原件均为已下载的精确 base 文件。SLA 372–435 行列、567–660 行策略卡/新建卡、738–822 行假日包；trash 54–102 行列、109–125 行页铬，71/78 行原值标签。
- `inventory-REPORT.md` 第 3 节与 `inventory-RECEIPT.txt`：盘点 base 为 `18a63574c4b40baf48e7990160be5516e075b89e`，证据包 sha256 `c681fcc704dc0588c06fb8cdeb7fbeee34c52314486b774cc637c232bb40cf55`。PR13/14 未改这两份页面；新执行基线仍须在 PR14 tip 当次重跑。
- `inventory-vite.readonly.config.mjs` 是旧盘点的仓库外配置原件，只作结构参考，不把其中旧路径/端口用于新执行。
- `template-design.md` / `template-plan.md` 只作第 2 刀结构与语气参照，不是本刀批准或执行记录。

英文 SLA 已有 help、Run due checks、Business hours、度量/状态翻译；仍露中文卡标题、表头、按钮与新建卡内铬。假日包默认收起。回收站文档标题已是 Trash，但页内中文；空列表截图未显示 `row.status`/`row.priority` 原值，本刀必须用非空 fixture 测试证明修复，不能拿空截图充数。

## 2. 方案与推荐

A（推荐）：扩展既有 `page.sla`，回收站另建同级对象 `page.issueTrash`；两页 columns 改 computed，先读 `locale.value` 再算标题/label；状态/优先级复用 `useLabelTable` + `lookupLabel`。边界清楚，不改 API、枚举和路由标题。

B：复用 `page.issueList.columns.*`、`route.issue_trash`、`common` 刷新。少键但把独立页面与路由耦合，也违背第 2 刀页内标题纪律，不采用。

C：建一个混合 SLA/trash 总 namespace。键看似集中，实际跨领域；已有 `page.sla` 还要迁移，不采用。

选 A；新铬的脚本调用统一导入 `@/locales` 的 `$t`，原 SLA 的 `t`、help 等绑定不重写。新建卡与假日包局部做接线，不重构整页。trash 的 `trashEmptyHint()` 改为 `$t('page.issueTrash.empty')`，页面用先读 locale 的 computed `emptyHint`，其余 helper 保持中文。两页 columns 都是 computed 回调第一句 `void locale.value;`（在任何短路左侧），SLA `packRegionFilterOptions` 仍 computed 且先读 locale；`packYearFilterOptions` 从常量改 computed。保留各列 render/动作/权限逻辑。

## 3. 锁定文案

英文 sentence case；中文除决策 A 推荐的「删→删除」外逐字保留。数字及 pack summary 参数名锁定如下。`holidayPack` 用于单个策略行动作，`holidayPacks` 用于包集合卡标题，不能让一个英语单数同时承担集合标题。

### `page.sla` 新增（28 键）

| 键 | zh-CN | en-US |
|---|---|---|
| `policies` | SLA 策略 | SLA policies |
| `refresh` | 刷新 | Refresh |
| `newPolicy` | 新建策略 | New policy |
| `name` | 名称 | Name |
| `startStopStatuses` | 启停状态 | Start and stop statuses |
| `enabled` | 启用 | Enabled |
| `actions` | 操作 | Actions |
| `minutes` | {n} 分钟 | {n} min |
| `holidayPack` | 假日包 | Holiday pack |
| `holidayPacks` | 假日包 | Holiday packs |
| `clearOverride` | 清除覆盖 | Clear override |
| `delete` | 删除 | Delete |
| `notifyAssignee` | 通知负责人 | Notify assignee |
| `notifyWatchers` | 通知关注者 | Notify watchers |
| `calendarOverride` | 日历覆盖 | Calendar override |
| `calendarOverrideHint` | 关闭=继承工作区；开启后仅填写字段覆盖，其余仍继承 | Off inherits the workspace. When on, only filled fields override; the rest still inherit. |
| `timezoneOverride` | 时区覆盖 | Time zone override |
| `inheritWorkspace` | （继承工作区） | (Inherit workspace) |
| `exceptionOverride` | 例外覆盖（填写则整表替换 WS 例外；留空=继承） | Exception override (a filled table replaces workspace exceptions; empty inherits) |
| `create` | 创建 | Create |
| `allRegions` | 全部地区 | All regions |
| `allYears` | 全部年份 | All years |
| `region` | 地区 | Region |
| `year` | 年份 | Year |
| `packTitle` | 国家/地区假日包（一键合并例外日） | Country and region holiday packs (merge exception days) |
| `preview` | 预览 | Preview |
| `applyPack` | 确认应用 | Apply |
| `packPreviewSummary` | 变更：+{added} / 覆盖 {replaced} / 保留 {kept} （{before} → {after}） | Changes: +{added} / replaced {replaced} / kept {kept} ({before} → {after}) |

复用已有键：新建卡「添加例外」=`page.sla.addException`（添加例外 / Add exception）；决策 A 若同意，短按钮=`page.sla.removeException`（删除 / Remove）。已有 Business hours 两个同名绑定不动，最终两键 `$t` 调用各 2 次。preview 行继续 `packAdded`（新增 / Added）、`packReplaced`（覆盖 / Replaced）。

### `page.issueTrash` 新增（11 键，对象，与 `page.sla` 并列）

| 键 | zh-CN | en-US |
|---|---|---|
| `title` | 回收站 | Trash |
| `backToList` | 返回列表 | Back to list |
| `refresh` | 刷新 | Refresh |
| `empty` | 回收站为空 | Trash is empty |
| `key` | 编号 | Key |
| `issueTitle` | 标题 | Title |
| `status` | 状态 | Status |
| `priority` | 优先级 | Priority |
| `updatedAt` | 更新时间 | Updated |
| `actions` | 操作 | Actions |
| `restore` | 恢复 | Restore |

`title` 是卡标题，列「标题」必须叫 `issueTitle`，不得重复键。回收站列不用 `page.issueList.columns.*`；刷新不用 common。文档标题继续 `route.settings_sla`=SLA 策略 / SLA、`route.issue_trash`=回收站 / Trash；页内卡标题只用 page 键，不改 route。

状态表继续 `page.issueStatus.open`=待办 / Open；优先级表继续 `page.issuePriority.critical`=紧急 / Urgent，不改成 To do / Critical。未知值由 `lookupLabel` 原样回退，保留 tag 类型函数与枚举值。

## 4. 范围

**范围内**

- SLA 策略卡：标题、刷新、名称/启停状态/启用/操作列、`N 分钟`、假日包/清除覆盖/删除行按钮。
- **同页新建策略卡也包含 inner chrome**：标题、名称占位、通知负责人/关注者、日历覆盖、继承提示、时区覆盖及继承选项、例外覆盖长提示、添加例外、创建、短删按钮。不是只翻卡标题（见决策 B）。`YYYY-MM-DD`、时区 ID、用户策略名、表单行为不改。
- 假日包卡：卡标题、展开/收起 header、全部地区/年份、地区/年份占位、预览/确认应用、带数量 summary。箭头、筛选值、包数据/API、target 语义不改。
- 回收站：卡标题、返回列表/刷新、空态、六列表头、恢复按钮与状态/优先级展示值。恢复/分页/跳转/API 行为不改。

**范围外**

- 所有 `window.$message`（已翻译者也不重写）与 run-due `扫描 ${n} · 违约 ${n} · 通知 ${n}`。包括加载回收站失败、恢复失败（需要 member 权限）、restoreSuccessMessage 的「已恢复」。不得全文件替换中文。
- 整张 Business hours 卡：既有 businessHours/hoursIntro/hoursEnabled/weekdayPreset/hoursWindowPlaceholder/exceptionDays/noExceptions/defaultWindow/removeException/addException/windowPlaceholder/saveHours 等绑定及词值不改。help、runDue、holidayIntro、defaultPolicyName 不改。`policy-name.ts` 不改；不重做 `policyNameAfterLocaleChange` 与其行为断言，只适配 labels 测试占位查询。
- `deletedReadonlyBanner()` 属于详情 readonly，仍是「此问题已在回收站中，只读。恢复后可继续编辑。」；不把详情 banner/restore 测试改成英文。Naive-UI 空表 No Data 为库默认，范围外。
- 路由、常量、枚举、列表/表单/详情、焦点 CSS、暗色/对比度、假日包数据、后端均不动。`residual-copy.test.ts` 的 help/defaultPolicyName 断言不重写。

## 5. Yuri 待决策（不能悄悄当成已批）

**决策 A：推荐复用 `page.sla.removeException`，可见 zh 从「删」变「删除」，en=Remove。** 这是唯一有意中文变化。请确认或改；不自行造 删/Del 第三措辞。下方 plan 暂按接受 A 编排，若不接受先同步修订两文档、重审，再执行。

**决策 B：推荐包括新建策略卡的 notify/calendar 内部铬。** 盘点原话是「卡片、表头、按钮和空态」；这里依第 2 刀 same-card 规则明确扩到同一卡内的字段标签/提示/占位。Yuri 可收窄，收窄后先删掉对应键/接线/测试合同，再批准，不带未批范围实施。

## 6. 验收合同

- 两份 locale 与 `App.I18n.Schema.page.sla` 完整 leaf 集合一致（已有全部保留+28 新键），`page.issueTrash` 恰好 11 leaf。typings walker 使用 `sla\s*:\s*\{` / `issueTrash\s*:\s*\{` 对象定位，不撞 route/settings_sla。逐字冻结表中中英文与既有 help、Business hours、holidayIntro、defaultPolicyName、runDue。
- plan 内给出完整可落地测试：真实 `$t` 调用数，`:title` 绑定，精确 title/placeholder/独立按钮行/列 title/raw render 缺席检查。不写宽泛 `not.toContain('回收站')` / `('SLA 策略')` / `('刷新')` / `('名称')` / `('假日包')`。旧词会留在 toast/注释/route 中。
- fixture API 返回 WAY-1 open/critical 与未知状态/优先级第二行；真组件的 columns render 经 table stub 执行，zh 待办+紧急，切 en 不 remount 后 Open+Urgent；未知值不丢。不是对空表做标签断言。空态另测无 remount 切语种。
- `labels.test.ts` 仅把四处名称 input 查询改为 `input[placeholder="${i18n.global.t('page.sla.name')}"]` 动态查询；保留进行中停留→Time in progress、自填 My policy 不覆盖、loaded/dirty 的全部断言。NCard stub 不呈现标题，卡标题主要用源码接线证明，不依赖 wrapper.text()。
- 先 docs-only commit，再 tests-only RED 原件（不要求额外 RED commit），再最小产品 GREEN；四门对照**当次干净精确 base**。baseline tsc/lint 非 0 就如实保留，新增诊断必须 0（行号可漂）；不得挪用第 2 刀数字称全绿。
- en/zh 浅色 SLA，假日包展开、日历覆盖展开；en/zh trash 尽量 fixture 行。浏览器仍空就明确写空并依赖 fixture 单测。两份独立 grok-4.7-high 原文；没有单独 `Approve` 行不得写 dual Grok Approve。

## 7. 限制

旧盘点回收站为空，原值泄漏仅源码证据；holidayIntro 默认收起不是截图验过；SLA/trash 无暗色图；对比度未量。旧包缺进程表与生成文件 hash 原件，Vite 有 json5 提示，合成 token/workspace 非生产登录，这些不能用本刀草稿抹去。新执行的 tsc/lint 可能仍失败；toast 与 run-due 结果继续中文是约定范围，不宣称全页全英。

## 8. 实施边界

- 本轮只交本地草稿；获批口令为「design ok，开写」，不是现在执行。Yuri 决策 A/B 未确认前不得实施。
- 精确 base：`5bc1f604a22aad1517eaeae16ada004ba14fc11a`（PR14 tip，`cursor/issue-form-property-en-chrome-4333`）。不改写 PR6–14 已存提交。
- 后续仅普通隔离 clone（`.git` 为目录），不用 worktree；不写/reset MAIN `244c93e296a047cf138a880fa24d683b4be8203d` 或 PIN `250fc34af9c64e828aab706567b0430d3d74e452`，不改已有实施检出或既有服务。
- 不买额度，不 merge，不部署；未经后续授权不 push、不开 PR。本轮不建产品分支、不改产品、不 TDD、不 commit、不联系任何人。

只允许下列 12 路径；审查增加路径须先改文档获批，不能偷偷扩大：

- `docs/superpowers/specs/2026-11-12-sla-trash-en-chrome-design.md`
- `docs/superpowers/plans/2026-11-12-sla-trash-en-chrome.md`
- `frontend/src/locales/langs/zh-cn.ts`
- `frontend/src/locales/langs/en-us.ts`
- `frontend/src/typings/app.d.ts`
- `frontend/src/views/settings/sla/index.vue`
- `frontend/src/views/settings/sla/__tests__/labels.test.ts`
- `frontend/src/locales/__tests__/sla-trash-chrome.test.ts`
- `frontend/src/views/issue/trash/index.vue`
- `frontend/src/utils/issueTrashMeta.ts`
- `frontend/src/utils/issueTrashMeta.test.ts`
- `frontend/src/views/issue/trash/__tests__/chrome.test.ts`

hook 只在新 clone 处理：删除 pre-commit、保留 commit-msg、core.hooksPath 为空，不用 SKIP/--no-verify，不改 verifier。commit EXIT 0 不证明它读了本 checkout；若 frontend/.git/COMMIT_EDITMSG 或类似 ENOENT，原件落盘后立即停止，不二次 retry。第三笔 locale-read 修补只在审查发现短路 bug 才补，不预安排第三提交。当前未实施。
