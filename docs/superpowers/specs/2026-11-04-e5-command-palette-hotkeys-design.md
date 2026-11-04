# E5 设计：⌘K 命令面板 · 全站搜索跳转 · 核心快捷键

日期：2026-11-04  
Epic：E5  
状态：active（S2 closed；S3 待做；未推远程）  
基线：`sprint/E5-S1` @ `3075de2` → `sprint/E5-S2`；worktree `/workspace/opentask-worktrees/E5-S2`

## 1. 目标

对齐 Linear 手感，交付：

1. **S1** 命令面板壳 + ⌘K/Ctrl+K + 页面/动作跳转（含菜单路由）
2. **S2** 实体搜索分组：Issues / Projects / Saved Views（应用）
3. **S3** 列表/看板焦点 + 热键 C/A/S/P/I + status/assignee/priority pickers + assign-to-me；看板详情 URL 修正

不做：Cycles（E6）、Labels L、G-then-X、模态创建器、共享 Views 打磨、第三方 cmdk/hotkeys-js、远程推送。

## 2. 架构总览

```
BaseLayout (always mounted when authenticated shell)
├── CommandPaletteHost          # 独立于 theme.globalSearch.visible
│   ├── useCommandPalette()     # open/close, query, grouped results, run action
│   └── CommandPaletteModal     # NModal（可由升级后的 search-modal 演进）
└── useAppHotkeys()             # ⌘K + C/A/S/P/I；ignoreWhenEditable
        │
        ├── useIssueFocus()     # focusedIssueId；list/board/detail 写入
        └── issueApi / users / saved-views / projects
```

**挂载策略（锁定）**

- Header 内现有 `<GlobalSearch v-if="themeStore.header.globalSearch.visible" />`：**保留图标按钮**，但**打开同一 palette 状态**（共享 `useCommandPalette`），避免双实例。
- 另在 `base-layout`（或 `global-header` 外始终渲染的宿主）挂载 **palette modal + hotkeys**，使 `visible=false` 时仍可 ⌘K。
- 实现可选路径：
  - **Preferred**：把 `show` 状态上提至 `useCommandPalette`（module singleton / pinia-lite composable），`GlobalSearch` 按钮只 `open()`；modal 单例挂在 base-layout。
  - Acceptable：扩展 `global-search/index.vue` 拆出 modal，并在 base-layout 无条件 import modal+hotkeys。

## 3. Composables

### 3.1 `useCommandPalette`

建议路径：`frontend/src/composables/use-command-palette.ts`（或 `features/command-palette/`）

| API | 说明 |
|---|---|
| `isOpen` | Ref\<boolean\> |
| `query` | Ref\<string\> |
| `groups` | Computed：`{ id, label, items: PaletteItem[] }[]` |
| `activeIndex` / `activeItem` | 键盘导航 |
| `open()` / `close()` / `toggle()` | |
| `setQuery(q)` | 触发防抖搜索（S2） |
| `runActive()` / `run(item)` | 执行 action 或导航 |

`PaletteItem`：

```ts
type PaletteItemKind =
  | 'action'      // 导航 / 命令
  | 'issue'
  | 'project'
  | 'saved_view'
  | 'menu';      // 现有 routeStore.searchMenus

interface PaletteItem {
  id: string;
  kind: PaletteItemKind;
  title: string;
  subtitle?: string;
  keywords?: string[];
  icon?: string;
  /** 执行：路由或副作用 */
  run: () => void | Promise<void>;
}
```

S1 静态 **Actions**（query 空或匹配 keywords 时展示）：

| id | title | run |
|---|---|---|
| `nav.issues` | Issues / Issue 列表 | `router.push('/issue/list')` |
| `nav.create_issue` | Create Issue | `router.push('/issue/create')` |
| `nav.projects` | Projects | `router.push('/workflow/projects')` |
| `nav.inbox` | Inbox | `router.push('/inbox')` |
| （可选）菜单项 | 来自 `routeStore.searchMenus` | `router.push(routePath)` |

### 3.2 `useAppHotkeys`

建议路径：`frontend/src/composables/use-app-hotkeys.ts`

| 快捷键 | 行为 | Sprint |
|---|---|---|
| `Meta+K` / `Ctrl+K` | `useCommandPalette().toggle()` | S1 |
| `Escape` | 关闭面板（modal 内已有；全局可兜底） | S1 |
| `C` | 若面板未开 → `/issue/create`；若面板开则交给面板输入（单键不抢） | S3（可 S1 先做 C） |
| `S` / `A` / `P` / `I` | 需 `focusedIssueId`；打开对应 picker 或执行 I | S3 |

**`ignoreWhenEditable(event)`**

- `true`（忽略单键热键）当 `event.target` 是：
  - `HTMLInputElement` / `HTMLTextAreaElement` / `select`
  - `[contenteditable="true"]` 祖先
  - Naive 可编辑控件（`.n-input`, `.n-base-selection-input` 等）内
- **⌘K / Ctrl+K**：即使在输入框内也允许打开面板（Linear 常见）；打开后面板自有 input 接管。
- 面板已打开时：单键 C/A/S/P/I **不**触发全局命令（避免与查询输入冲突）。

注册：在 base-layout `onMounted` 调用一次 `useAppHotkeys()`（或内部 `useEventListener(window, 'keydown', …)`）。

### 3.3 `useIssueFocus`

建议路径：`frontend/src/composables/use-issue-focus.ts`

| API | 说明 |
|---|---|
| `focusedIssueId` | Ref\<string \| null\> |
| `focusedIssue` | 可选缓存摘要 `{ id, title, status, priority, assigneeId }` |
| `setFocus(id, summary?)` | 列表行 click / 键盘 ↑↓ / 看板卡 click |
| `clearFocus()` | 离开列表/看板或失焦策略 |
| `ensureDetailFocus(id)` | 详情页 `onMounted` / `watch route.query.id` |

规则：

- 列表：点击行或键盘移动高亮 → `setFocus`
- 看板：点击卡（未拖拽）→ `setFocus`；双击或「打开」→ 跳转详情（`?id=`）
- 详情：路由 id 即为焦点
- 无焦点时 A/S/P/I：no-op 或轻提示（`window.$message.info`）；不报错砸栈

## 4. UI

### 4.1 Command Palette Modal

- 基于现有 `search-modal.vue`（`NModal` card、`NInput`、↑↓ Enter Esc、footer 快捷键提示）。
- 结果区改为 **分组列表**：`NThing` / 自定义 row；组标题小字（Actions / Issues / Projects / Views / Menus）。
- 空 query：展示 Actions（+ 可选最近，E5 不做 recent 持久化）。
- 有 query：过滤 Actions/Menus +（S2）异步实体组。
- 宽度延续 ~630px；移动端全屏沿用现逻辑。
- i18n：新增 `common.commandPalette` 等键；中英最少集。

### 4.2 Pickers（S3）

轻量 `NDropdown` / `NModal` / `NPopselect`，挂在 list/board/detail 公共层或 teleported：

| 热键 | UI | API |
|---|---|---|
| S | 状态下拉：open / in_progress / …（与现 Issue 状态枚举一致） | `issueApi.updateStatus(id, status)` |
| A | 成员搜索选择（复用 `/api/users` keyword 或工作区成员列表若已有） | `issueApi.updateAssignee(id, userId?)` |
| P | 优先级枚举 | `issueApi.updatePriority(id, priority)` |
| I | 无 UI：`updateAssignee(id, currentUser.id)` | `fetchGetUserInfo` / auth store |

成功后刷新当前列表行或详情；失败 `message.error`。

### 4.3 焦点视觉

- 列表行：`outline` / `bg` token（DESIGN.md / soybean 表面色）；`aria-selected`
- 看板卡：同类高亮；**不**与拖拽 ghost 冲突（mousedown vs click 区分可沿用现板逻辑）

## 5. 数据流与 API（复用，无新表）

| 用途 | API | 说明 |
|---|---|---|
| Issue 标题搜 | `GET /api/issues?search=&page_size=` | ilike；S2 debounce 300ms |
| Issue code | `GET /api/issues/{code}?by_code=true` | 后端已有；**FE `getIssue` 需扩 params** |
| Projects | `fetchProjectList()` | 客户端 filter by name；或已有 search 则用之 |
| Saved Views | `fetchSavedViews()` | 客户端 filter by name；run → 跳 list + apply |
| Inbox 跳转 | 路由 `/inbox` | 面板不强制调 inbox API |
| Users（指派） | `GET /api/users?keyword=` | S3 A picker |
| 状态/指派/优先级 | `PUT .../status\|assignee\|priority` | 已有 FE wrappers |

**Saved View apply（S2）**

1. `router.push({ path: '/issue/list', query: { view: id } })` **或**
2. 直接 `router.push('/issue/list')` + 通过 session/pinia/`provide` 把 view payload 交给 list（E4 列表已有 apply 函数）

推荐：list 支持 `?view=<savedViewId>` 查询参数（S2 小改 list）：mount 时 GET 该 view（或已有 list 缓存）→ 写 filters。若不想改后端，用前端 `fetchSavedViews` 找 id 应用。

**Board URL fix（S3，触及跳转即做）**

```ts
// IssueBoard.vue 现状（错误）
router.push(`/issue/detail/${issue.id}`);
// 目标
router.push({ path: '/issue/detail', query: { id: issue.id } });
```

同步检查其它 path 段写法。

## 6. 焦点模型（详）

```
focusedIssueId
    ↑ setFocus          ↑ ensureDetailFocus
 list row / board card    /issue/detail?id=
    ↓ read
 useAppHotkeys → S/A/P/I pickers → issueApi.update*
```

- 单选焦点，非 checkbox 多选（多选另 Epic）。
- 切换 workspace 时 `clearFocus()`。
- 面板打开不清除焦点（关闭后热键仍可用）。

## 7. 测试策略

### 7.1 后端

- E5 **默认无新模型/迁移**。全量 `uv run pytest tests/ -v` 回归。
- 若补测试：`by_code=true` 已有则不必新写；指派/状态 API 已覆盖。

### 7.2 前端

- 优先：**纯函数 / composable 单测**（若项目已有 vitest；若无则跳过并依赖 lint/build + 手动/浏览器场景）。
- 门禁硬：`npm run lint`（0 errors）+ `npm run build`。
- 浏览器 acceptance：roadmap R1–R9（整 Epic 收口时一次跑）。

### 7.3 建议单测点（若加 vitest）

- `ignoreWhenEditable` 真值表
- `groupPaletteItems` 空 query vs 有 query
- code 形状检测（如 `/^[A-Z]+-\d+$/i`）决定是否先打 by_code

## 8. 分 Sprint 范围

### E5-S1 — Palette 壳 + ⌘K + 动作跳转

- `useCommandPalette` + modal 升级（Actions + Menus）
- base-layout 全局挂载；header 按钮共享 open
- ⌘K / Ctrl+K；Esc；↑↓ Enter
- 主题开关不影响快捷键
- 文档：本 design + roadmap + S1 plan
- **不做**实体 API 搜索、焦点、A/S/P/I（C 可提前做为动作项，全局单键 C 可放到 S3 以免与输入冲突测试纠缠）

### E5-S2 — 实体搜索

- Issues：debounce `getIssues({ search })`；精确 code → `getIssue(code, { byCode: true })`
- Projects：list + filter
- Saved Views：list + filter → apply on `/issue/list`
- 分组 UI；加载中 / 空态
- FE：`issueApi.getIssue` 支持 `byCode` query

### E5-S3 — 焦点 + 热键 + pickers + URL + Epic 收口

- `useIssueFocus` + list/board 高亮
- `useAppHotkeys`：C/A/S/P/I + ignoreWhenEditable
- Pickers + assign-to-me
- Board `?id=` 修复
- Epic acceptance + roadmap status → local-complete（整包回执 Yuri）

## 9. Non-goals

- Cycles / 冲刺容量（E6）
- 命令面板「最近访问」持久化
- 全局多选批量改状态
- Slash 命令 DSL（`/status` 文本命令）
- 自定义用户快捷键重绑定
- 新 npm 依赖（cmdk、hotkeys-js、mousetrap、fuse 等）；客户端过滤用简单 `includes` 即可
- 登录页 / blank-layout 启用 ⌘K

## 10. 风险与约束

- **双挂载**：必须单例 modal，避免两个 NModal 抢焦点。
- **可编辑忽略**：富文本评论区必测，否则误触 C 跳走。
- **权限**：updateAssignee 等沿用现 API 403 处理。
- **DESIGN.md**：无新色板；用现有 primary / surface。
- 本地 worktree；**不推远程**。

## 11. 文件路径（预期）

| 层 | 路径 | Sprint |
|---|---|---|
| Composable | `frontend/src/composables/use-command-palette.ts` | S1 |
| Composable | `frontend/src/composables/use-app-hotkeys.ts` | S1/S3 |
| Composable | `frontend/src/composables/use-issue-focus.ts` | S3 |
| UI | `frontend/src/layouts/modules/global-search/**`（升级）或 `features/command-palette/**` | S1–S2 |
| Host | `frontend/src/layouts/base-layout/index.vue` | S1 |
| Header | `frontend/src/layouts/modules/global-header/index.vue` | S1（v-if 仅图标） |
| List | `frontend/src/views/issue/list/index.vue` | S2 apply query / S3 focus |
| Board | `frontend/src/views/issue/list/modules/IssueBoard.vue` | S3 focus + URL |
| Detail | `frontend/src/views/issue/detail/index.vue` | S3 focus |
| API | `frontend/src/service/api/issue.ts`（byCode） | S2 |
| i18n | `frontend/src/locales/langs/{zh-cn,en-us}.ts` | S1+ |
| Docs | `docs/superpowers/roadmaps/2026-11-04-opentask-command-palette-hotkeys.md` | S1 |
| Docs | `docs/superpowers/specs/2026-11-04-e5-command-palette-hotkeys-design.md` | S1 |
| Docs | `docs/superpowers/sprints/2026-11-04-E5-S1-plan.md` | S1 |

## 12. Spec self-review

- 无 TBD 阻塞项；Q1–Q4 已关闭。
- 与 roadmap Deliverables / DoD / R1–R9 对齐。
- S1/S2/S3 边界清晰；Cycles 显式 E6。
- FE byCode 缺口已写明，避免实现时遗漏。
