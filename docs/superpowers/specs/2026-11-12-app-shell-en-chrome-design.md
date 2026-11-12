# 应用壳层英文铬

第 7 刀 design 草稿，送 Yuri 代审；没有审批结论。要等 Yuri「design ok，开写」之后才可实施。本文不是已批准范围。未来 repo 路径：`docs/superpowers/specs/2026-11-12-app-shell-en-chrome-design.md`。本文与 plan 是一组。盘点报告在 `/workspace/designs/post-pr18-polish-inventory/INVENTORY.md`（sha256 `66aaf639ef149ba7ef02097f74b71d5644bf8ae2b89a08c829e40cc456c9a1ed`，29765 字节），摘录在同目录 `priority-surfaces.md`（sha256 `ba3ba7f559a78b4a0af6035efc3aca187b0d83cd4a49460000006009453e309d`，15447 字节），都不入库。行号与现文案以精确 base `09413d292c71973d4af5fc7350be88d9d55cdc2a`（PR18 tip）上的盘点与摘录为准。不要用 `6b6ad3b4` 的旧行号当实施 base。

## 1. 问题与证据

PR18 已限定交付。本刀起点为 `09413d292c71973d4af5fc7350be88d9d55cdc2a`。`en-us.ts` 无汉字。`fallbackLocale` 是 `'en'`，注册的语言只有 `'zh-CN'` 和 `'en-US'`，缺 key 不会退回中文。英文界面上还能看见的中文，通常是写死字符串，或被上一刀测试冻住、故意不走 `$t` 的文案。

第 6 刀列表看板、显示选项、批量条、搜索建议已经在 tip 上，不是本刀范围，也不要重开。侧栏菜单和四个业务导航（`ActivityNav.vue`、`CustomersNav.vue`、`InsightsNav.vue`、`TriageNav.vue`）已经没有汉字，不要重做。英文界面上还在每一页壳层出现的残留是：收藏区两句、页头实时连接 `title`、工作区切换弹层、焦点问题快捷键浮层（含该文件内 toast），以及命令面板 `estimateTitle`「设置估点…」。这是盘点第 6 节建议的第一片候选，仍未获批。

创建/编辑剩句（创建页「自定义字段（可选）」、编辑页「加载中...」）以及列表布尔格「是/否」是后两片候选，本刀只在范围外说明，不实施。不要把壳层写成已经批准的范围。

## 2. 方案与推荐

在已有 `page.shell` 下增设清晰分组：`favorites`、`realtime`、`workspaceSwitcher`、`hotkeyPicker`，并同步 `App.I18n.Schema`。命令面板「设置估点…」补进已有 `common.commandPalette`（同文件其它动作已在此块；`en-us.ts` 的该块目前没有估点这一条）。省略号必须是 `…`（U+2026）。各文件继续沿用 tip 上已有的 `$t` 导入方式（优先 `@/locales` 的 `$t` / `locale`），不要无故改成 `useI18n()`。已有可复用的整句优先复用，不造近义 key。快捷键浮层的状态、优先级选项走已有 `useLabelTable` / `lookupLabel`，不改 `constants/issue.ts`。

不把这些键塞进 `page.issueList`、`page.issueForm` 或路由键。也不改先做创建/编辑剩句或列表「是/否」。

脚本里若新增调用 `$t` 的 computed，或会缓存文案的函数（含快捷键浮层 `title`、状态/优先级 options computed，以及命令面板里会把文案写进 `palette.setSources` 的 `watchEffect`），第一句必须是 `void locale.value;`，位于任何短路之前。`no-void` 只用 `eslint-disable-next-line` 盖住这一句，或紧贴该 computed / 函数的 disable/enable 块。禁止文件级 `eslint-disable no-void`。模板里的 `$t` 不包 computed。命名参数插值必须写成 `$t('page.shell.hotkeyPicker.points', { n: pts })`，禁止 `.replace('{n}'` 或同类字符串替换迁就测试。`{{ pts }} 点` 必须改成上述 `$t`，中文 `{n} 点`，英文 `{n} pts`。

不要把既有 `$t` 改成局部 `t()`。不要为了测试删掉 `useI18n` 或改组件 identity。

## 3. 锁定文案

英文 in-page copy 用 sentence case。中文逐字保留，包括全角括号、en dash `2–6`（U+2013）、句中已有的拉丁词 `Labels`，以及省略号 `…`（U+2026）。如需 apostrophe，用 U+2019（与已落地列表铬 “Couldn’t” 一致）。`en-us.ts` 不得有汉字。不改 route 键值。不改已复用键的既有译文。用户内容、协议词、`insertText` 种子、命令面板 `keywords` 保持原样。「暂无标签，请先到 Labels 设置页创建」里的 Labels 保留为 Labels。下面「调用」按 tip `09413d29` 可见点计；实施时以该 tip 源码为准，测试按实际调用次数钉死。

### 复用已有键（不新造近义句）

| 表面 | 中文 | 键 | 英文 |
|---|---|---|---|
| 工作区切换弹层按钮「创建」 | 创建 | `page.issueDetail.create` | Create |
| 快捷键浮层按钮「确认」（标签确认） | 确认 | `common.confirm` | Confirm |
| 快捷键浮层状态选项 | 待办 / 进行中 / 等待反馈 / 已解决 / 已关闭 / 已拒绝 | `page.issueStatus.*`（`useLabelTable` + `lookupLabel`） | 已有译文 |
| 快捷键浮层优先级选项 | 低 / 中 / 高 / 紧急 | `page.issuePriority.*`（`useLabelTable` + `lookupLabel`） | 已有译文 |

按钮「创建」只复用 `page.issueDetail.create`，不要把这个键用在标题「创建工作区」上（决定 B）。「确认」只用于标签确认按钮，不要用 `common.confirm` 去当「确认指派」。

不要复用：

- `route.workspace-onboarding` 去当弹层标题「创建工作区」（该键中英文虽是「创建工作区」/ Create workspace，但是路由标题；决定 A 要求新键，避免导航标题和弹层绑在一起）
- `route.workspace` 去当输入占位「工作区」（文案相同，仍用新键 `page.shell.workspaceSwitcher.placeholder`，理由同 A，不把路由键当输入占位）
- `page.issueList.views.favoriteViews`（收藏视图）或 `page.issueList.toolbar.pinToSidebar`（收藏到侧栏）去当「收藏」
- `page.shell.issueKeyPrefix`（问题单号 / Issue key）去当「问题单号（可选，2–6 位大写）」；该键短于这一整句，不要整句复用
- `page.issueDetail.create` 去当标题「创建工作区」
- `common.confirm` 去当「确认指派」
- `page.issueDetail.noTags`（暂无标签）去当「暂无标签，请先到 Labels 设置页创建」

### `page.shell.favorites`（新键）

| 键 | zh-CN | en-US | 调用 |
|---|---|---|---|
| `title` | 收藏 | Favorites | `FavoritesNav.vue:81`，1 次 |
| `empty` | 暂无侧栏收藏 | No sidebar favorites | `:86`，1 次 |

不要改 `typeHint` 已有的 `page.shell.favoriteProject/View/Issue/Initiative` 调用，也不要改 `utils/favorites.ts` 的 `FAVORITE_TYPE_LABEL` 兜底表。

### `page.shell.realtime`（新键）

| 键 | zh-CN | en-US | 调用 |
|---|---|---|---|
| `connected` | 实时已连接 | Live connection on | `global-header/index.vue:48`，1 次 |
| `disconnected` | 实时未连接（重连中） | Live connection off (reconnecting) | 同 loc，三元另一支，1 次 |

只改实时连接 `title`。旁边可见字符 `●`（`:51`）保持原样，不要动颜色或样式。

### `page.shell.workspaceSwitcher`（新键）

| 键 | zh-CN | en-US | 调用 |
|---|---|---|---|
| `placeholder` | 工作区 | Workspace | `workspace-switcher.vue:70`，1 次 |
| `createTitle` | 创建工作区 | Create workspace | `:77`，1 次 |
| `namePlaceholder` | 工作区名称 | Workspace name | `:82`，1 次 |
| `issueKeyPlaceholder` | 问题单号（可选，2–6 位大写） | Issue key (optional, 2–6 uppercase letters) | `:85`，1 次 |
| `issueKeyHint` | 留空则从名称自动生成；创建后可在冲刺设置中修改。 | Leave blank to generate from the name. You can change this later in cycle settings. | `:90`，1 次 |
| `createFailed` | 创建失败 | Couldn’t create the workspace | `:48`，1 次 |

中英文的 `2–6` 都必须是 en dash（U+2013）。`createFailed` 的英文弯引号是 U+2019。按钮「创建」走已有 `page.issueDetail.create`，不进本表。

### `page.shell.hotkeyPicker`（新键）

| 键 | zh-CN | en-US | 调用 |
|---|---|---|---|
| `changeStatus` | 更改状态 | Change status | `issue-hotkey-picker-host.vue:29`，1 次 |
| `assignOwner` | 指派负责人 | Assign owner | `:31`，1 次 |
| `changePriority` | 更改优先级 | Change priority | `:33`，1 次 |
| `setLabels` | 设置标签 | Set labels | `:35`，1 次 |
| `setEstimate` | 设置估点 | Set estimate | `:37`，1 次 |
| `noFocusedIssue` | 无焦点问题 | No focused issue | `:181`，1 次 |
| `selectOwner` | 选择负责人 | Select owner | `:210`，1 次 |
| `confirmAssign` | 确认指派 | Confirm assignment | `:211`，1 次 |
| `noLabels` | 暂无标签，请先到 Labels 设置页创建 | No labels yet. Create them on the Labels settings page. | `:216`，1 次 |
| `points` | {n} 点 | {n} pts | `:233`，1 次，必须 `$t('page.shell.hotkeyPicker.points', { n: pts })` |
| `clearEstimate` | 清除估点 | Clear estimate | `:235`，1 次 |
| `updateStatusFailed` | 更新状态失败 | Couldn’t update the status | `:90`，1 次 |
| `statusUpdated` | 状态已更新 | Status updated | `:93`，1 次 |
| `updateEstimateFailed` | 更新估点失败 | Couldn’t update the estimate | `:109`，1 次 |
| `estimateUpdated` | 估点已更新 | Estimate updated | `:112`，1 次 |
| `updatePriorityFailed` | 更新优先级失败 | Couldn’t update the priority | `:126`，1 次 |
| `priorityUpdated` | 优先级已更新 | Priority updated | `:129`，1 次 |
| `assignFailed` | 指派失败 | Couldn’t assign the owner | `:143`，1 次 |
| `ownerUpdated` | 负责人已更新 | Owner updated | `:146`，1 次 |
| `updateLabelsFailed` | 更新标签失败 | Couldn’t update the labels | `:160`，1 次 |
| `labelsUpdated` | 标签已更新 | Labels updated | `:163`，1 次 |

浮层 `title` computed 与状态/优先级 options computed 的第一句必须是 `void locale.value;`。状态下拉、优先级下拉继续读取 `issueStatusOptions` / `issuePriorityOptions` 的 `value`，只覆盖可见 `label`，不改 `constants/issue.ts`。「确认」复用 `common.confirm`，不进本表。`noLabels` 中文里的 `Labels` 不得改成「标签」。

### `common.commandPalette.estimateTitle`（补进已有块）

| 键 | zh-CN | en-US | 调用 |
|---|---|---|---|
| `estimateTitle` | 设置估点… | Set estimate… | `command-palette-host.vue:70`，1 次 |

只改 `estimateTitle` 这一处。同文件其它已有 `common.commandPalette.*` 与 `route.workspace_issue-templates` 调用保持原样。省略号必须是 `…`（U+2026），不要写成三个 ASCII 点。该 `watchEffect` 会缓存文案并写入 palette，第一句必须是 `void locale.value;`。不要改 `utils/command-palette.ts` 的 `keywords`。

## 4. 范围

**范围内**

- `frontend/src/layouts/modules/global-sider/FavoritesNav.vue`：标题「收藏」、空状态「暂无侧栏收藏」。不改 `typeHint` 与兜底表。
- `frontend/src/layouts/modules/global-header/index.vue`：只改实时连接 `title`。不要动旁边的 `●`。
- `frontend/src/layouts/modules/global-header/components/workspace-switcher.vue`：占位、弹层标题、名称占位、问题单号占位与说明、创建失败 toast；按钮「创建」复用 `page.issueDetail.create`。
- `frontend/src/layouts/modules/global-search/issue-hotkey-picker-host.vue`：浮层标题、空状态、负责人占位、确认指派、无标签说明、确认按钮、估点 `{n} 点`、清除估点、十则 toast；状态/优先级 options 改走 `useLabelTable` / `lookupLabel`。
- `frontend/src/layouts/modules/global-search/command-palette-host.vue`：只改 `estimateTitle`（约 `:70`）。
- 语言包 `en-us.ts` / `zh-cn.ts`、`frontend/src/typings/app.d.ts`。
- 新建 `frontend/src/locales/__tests__/app-shell-chrome.test.ts`。
- 实施时 `cmp` 已批原文进入 `docs/superpowers/specs/2026-11-12-app-shell-en-chrome-design.md` 与 `docs/superpowers/plans/2026-11-12-app-shell-en-chrome.md`。

**范围外**

- 侧栏菜单和四个业务导航（`ActivityNav.vue`、`CustomersNav.vue`、`InsightsNav.vue`、`TriageNav.vue`）
- `utils/favorites.ts` 的 `FAVORITE_TYPE_LABEL` 兜底表
- `constants/issue.ts`（`issue-list-board-chrome.test.ts` 对「待办」「低」的冻结必须留下）
- `utils/command-palette.ts` 的 `keywords`
- `detail/index.vue` 及详情 toast
- 列表后缀桥、`groupIssuesBy.ts`、`display-prefs.ts`、`list/index.vue`
- 第 6 刀已落地的看板、显示选项、批量条、搜索建议；不要改 `issue-list-board-chrome.test.ts`，其常量「待办」「低」、`display-prefs`「是/否」以及决定 E 源串的冻结必须留下
- 创建/编辑页、创建/编辑 toast、`issue-composer-chrome.test.ts`（不要削弱它对「自定义字段（可选）」「加载中...」以及范围外 toast / `insertText` 种子的冻结）
- MarkdownEditor、AttachmentList、自定义字段内部、`IssueTemplateForm` 的「请填写」、设置四页、大模块、`noneCycle` 合并
- 列表布尔自定义字段格的「是/否」、`views/agents/index.vue` 的「是/否」
- 详情回复条「回复 @…」、SLA 剩余/逾期/已用时长、`EntityDocsPanel`、Agent 指令弹层
- 不 merge、不部署、未经再授权不 push、不开新 PR。不改写 PR6–18 已存提交或头 SHA

## 5. 决定（批准前确认）

按盘点推荐案写入本文，作为本刀锁定建议，供 Yuri 确认。否决任一条，先改 design 与 plan，再实施。

- **A（推荐，本刀锁定）。** 弹层标题「创建工作区」用新键 `page.shell.workspaceSwitcher.createTitle`，不复用 `route.workspace-onboarding`，避免把导航标题和弹层绑在一起。英文 Create workspace。占位「工作区」虽与 `route.workspace` 文案相同，仍用新键 `page.shell.workspaceSwitcher.placeholder`（工作区 / Workspace），理由同本条，不把路由键当输入占位。
- **B（推荐，本刀锁定）。** 按钮「创建」复用已有 `page.issueDetail.create`（中英文都是 创建 / Create）。不要把这个键用在标题「创建工作区」上。
- **C（推荐，本刀锁定）。** 快捷键浮层的状态、优先级选项走已有 `useLabelTable` / `lookupLabel`，不改 `constants/issue.ts`。
- 本刀只实施盘点第 6 节第一片（壳层）。第二片（创建/编辑各剩一句）与第三片（列表布尔格「是/否」）存在，但不在本刀实施。不要改先做后两片来回避 A/B/C。不要重开第 6 刀。

## 6. 测试与验收口径

- 新测试统计 `$t('…')` 调用点，字面缺失用精确正则或带周围 markup 的整句。禁止宽泛的 `not.toContain('取消')` / `('状态')` / `('重置')` / `('应用')` / `('确认')` / `('创建')` / `('收藏')`。
- 真实 `@/locales` 切换 `zh-CN` / `en-US`。不要自己造一套残缺 messages。测试必须读取 typings 源文件，断言 `page.shell.favorites` / `realtime` / `workspaceSwitcher` / `hotkeyPicker` 以及 `common.commandPalette.estimateTitle` 在三份文件键齐全，不能只比较两份 locale。
- `hotkeyPicker.points` 必须是 `$t('page.shell.hotkeyPicker.points', { n: pts })` 或同等 `{ n:` 签名，并 `not.toContain(".replace('{n}'")`。
- 有 `useI18n()` 的组件，Vue Test Utils 挂载必须 `plugins: [i18n]`（已有 pinia 则 `[pinia, i18n]`）。不要为了测试删掉 `useI18n` 或改组件 identity。Vue Test Utils stub 必须同时覆盖 naive-ui 真实 `name` 与 `N*` 别名。本刀五个布局文件在 tip 上都不使用 `useI18n()`，优先继续用 `@/locales` 的 `$t` / `locale`，不要无故改成 `useI18n()`。
- 正向保留：`utils/favorites.ts` 仍含 `FAVORITE_TYPE_LABEL` 的「项目」「视图」「问题」「举措」；`constants/issue.ts` 仍含 `label: '待办'` 与 `label: '低'`；`issue-list-board-chrome.test.ts` 仍冻住这些常量以及 `display-prefs.ts` 的 `return value ? '是' : '否'`；`issue-composer-chrome.test.ts` 仍冻住「自定义字段（可选）」与「加载中...」；`utils/command-palette.ts` 的 `keywords` 不被本刀改写；`global-header/index.vue` 仍渲染 `●`；`FavoritesNav.vue` 的 `typeHint` 仍在未知类型时回退 `FAVORITE_TYPE_LABEL`。`en-us.ts` 无汉字。
- 四门对照当次干净 `09413d29` 基线。tsc/eslint 基线非 0 则保持 added 0 / removed 0，不得写成全绿，不得借用 PR15–PR18 或第 6 刀的 95/551、✖ 868 等失败行号当终值。不能写 dual Grok Approve。
- 不要求本刀截图作为验收门。若实施时拿得到，只作为附证。
- 证据包必须含每一笔提交相对其第一父提交的 name-only、diffstat 与完整 diff，以及相对精确 base 的 `final.diff`。不得只用 `final.diff`。第一笔（docs）的分笔 diff 须恰好是两份 docs。若后来多出修订笔，每一笔同样要有这三份，不要 amend 前序提交来补证据。

## 7. 限制（写入验收说明）

- 第一次在仓库根提交若再出现 `Script not found "sa"`，必须 STOP 并记入限制；plan 已收入第 4 刀已接受的根 hook 拷贝与 gitignore 相对软链步骤，避免再踩同一坑，但那不是改 hook 正文。
- commit hook EXIT 0 不是路径证明，需要 strace 显示只读打开克隆根 `.git/COMMIT_EDITMSG`。若 hook 读到 `frontend/.git/COMMIT_EDITMSG` 或同类 ENOENT，STOP，保留原件，不要二次重试，不要改 verifier。
- `.env.prod` 不得入库、不得把正文写入证据包。prod build 只允许使用 sha256 仍为 `b686d37a6c470d295b5cf4165eea1c3a6ca3a43fcc08d0155b5a27634d2d2ce7`（1896 字节）的已核 `.env.prod` 副本；哈希不符或缺失则该门记 EXIT STOP（与 PR17/PR18 相同限制，不是本刀开写或必修复项），不用 `.env.example` 顶替，也不把 `.env.example` 拷成 `.env.prod`（即使它碰巧同哈希）。缺失已核 `.env.prod` 不得挡住 clone / TDD / 其它门禁，也不因此中断这些步骤。
- prod build 若弄脏 `frontend/src/typings/components.d.ts` 或 elegant-router 生成文件，必须从仓库根 `git checkout --` 再跑 tsc/eslint，打包还原前后 porcelain，不提交这些文件。
- 创建页「自定义字段（可选）」、编辑页「加载中...」、列表布尔格「是/否」，以及英文列表自定义字段列上的中文「是/否」，本刀不译，直到另有授权。
