---
epic: E5
status: local-complete
date: 2026-11-04
---

# OpenTask Linear 进阶：⌘K 命令面板 · 全站搜索跳转 · 核心快捷键

产品参考 Linear；在 E4（Saved Views / 列表分组 / 子 Issue）之上补齐「⌘K 命令面板 + 实体搜索跳转 + C/A/S/P/I 热键 + 列表/看板焦点选择」。本 Epic 为整包一个 Roadmap。Cycles（E6）/ Labels 打磨 / 模态创建器 / G-then-X 导航和弦明确排除。

## Deliverables

| deliverable | note |
|---|---|
| ⌘K / Ctrl+K 命令面板 | 升级 soybean `layouts/modules/global-search` 为 Linear 风格 **Command Palette**（动作 + 实体）；`NModal` + `@vueuse/core`；不引入 cmdk / hotkeys-js / mousetrap |
| 核心快捷键 C / A / S / P / I | **C** 创建 Issue（跳 `/issue/create`）；聚焦 Issue 时 **A** 指派、**S** 改状态、**P** 改优先级、**I** 指派给我 |
| 全站搜索 / 跳转 | Issue（title `search` + `by_code`）、Project、Inbox、Saved Views（应用筛选）、导航动作（Issue 列表 / Create / Projects / Inbox）；保留菜单路由搜索 |
| 列表 / 看板焦点选择 | 焦点模型供 A/S/P/I 在详情页外可用；输入框 / contenteditable 内忽略热键 |
| ⌘B / Ctrl+B Board↔List | 在 `/issue/list` 与现有 list/board 按钮共享 `useIssueListViewMode` 单例 |
| 看板详情 URL 修正 | 触及跳转路径时，将 `IssueBoard` 的 `/issue/detail/${id}` 改为 `?id=` query（与列表/详情一致） |

## Definition of Done

- [x] Epic 下全部 Sprint（S1–S3）已 acceptance 且 state=closed；合并证据本地台账（merged-commit 仍 null / 未推远程）
- [x] `cd backend && uv run pytest tests/ -v` 全绿（E5 若无新后端表则回归不破；若补 by_code 客户端则无后端强制变更）
- [x] `cd frontend && npm run lint && npm run build` 通过（0 errors）
- [x] ⌘K / Ctrl+K 在登录后的 app shell 任意页可开面板；主题「隐藏 GlobalSearch 按钮」**不**禁用快捷键
- [x] 面板可跳转 Issue / Project / Inbox / Saved Views（应用）/ 核心导航动作；键盘 ↑↓ Enter Esc 可用
- [x] 列表或看板有焦点 Issue 时，A/S/P/I 生效；详情页当前 Issue 作焦点；C 始终可跳创建页
- [x] 输入 / textarea / contenteditable / 可编辑组件内单键热键不触发
- [x] DESIGN.md / Naive UI / soybean 令牌被前端改动遵守；无 Cycles / 模态创建器 / 第三方快捷键库交付

## Sprint Breakdown

| sprint | state | note |
|---|---|---|
| S1 | closed | **Palette 壳 + ⌘K/Ctrl+K + 页面/动作跳转**；acceptance: `docs/superpowers/acceptances/2026-11-04-E5-S1-acceptance.md`；tip `0063b58` |
| S2 | closed | **实体搜索分组**：Issues（title + by_code）、Projects、Saved Views→应用筛选；防抖查询 + 分组结果。acceptance: `docs/superpowers/acceptances/2026-11-04-E5-S2-acceptance.md`；tip `9dc0e9e` |
| S3 | closed | **焦点选择 + C/A/S/P/I + pickers**；**⌘B/Ctrl+B** Board↔List；详情 focus；`ignoreWhenEditable`；看板 URL `?id=`；Epic local-complete。acceptance: `docs/superpowers/acceptances/2026-11-04-E5-S3-acceptance.md`；tip `a04c200` |

推荐顺序理由：先固化全局挂载与打开契约（S1），再叠实体检索（S2），最后绑定焦点与变更热键（S3）——变更热键依赖焦点与既有 updateStatus/Assignee/Priority API，避免 S1 过重。

## Decisions (ADR)

| id | decision | rationale | date | evidence |
|---|---|---|---|---|
| D1 | **升级/替换** soybean `global-search` 为动作+实体 Command Palette；**不**保留并行第二面板 | Way 拍板；避免双 UX | 2026-11-04 | 本文档；Yuri 转达 |
| D2 | 热键层用 **`@vueuse/core`**（已有 14.1.0：`onKeyStroke` / `useMagicKeys` / `useEventListener`）；**禁止** hotkeys-js / mousetrap / cmdk | 零新依赖；与现 modal Esc/↑↓ 一致 | 2026-11-04 | 设计 spec |
| D3 | ⌘K / Ctrl+K 挂载在 **base-layout 全局**（或始终挂载的 palette 宿主）；`theme.header.globalSearch.visible` **仅**控制 header 搜索图标，**不**卸载热键与面板 | Linear：主题隐藏按钮仍可 ⌘K | 2026-11-04 | 设计 spec |
| D4 | 创建走现有 **`/issue/create` 页**；模态 composer 不做 | 复用现页；减范围 | 2026-11-04 | Way 范围 |
| D5 | Saved Views **无独立路由**：面板选中 → 跳 `/issue/list` 并应用 `filter`/`sort`/`display`（复用 E4 列表 apply 路径） | E4 已交付 apply；不必新页 | 2026-11-04 | E4 design |
| D6 | Issue 按 code 跳转：`GET /api/issues/{code}?by_code=true`（后端已有）；FE 补 `getIssue(id, { byCode })` 或等价 | 探索确认 tip `1e03724` | 2026-11-04 | issue router |
| D7 | 列表/看板引入 **issue focus selection**（非多选）；供 A/S/P/I；详情页 = 当前打开 Issue | Linear 焦点手感；详情外可改字段 | 2026-11-04 | 设计 spec |
| D8 | 看板详情跳转修正为 `router.push({ path: '/issue/detail', query: { id } })`（现状 `IssueBoard.vue` 用 path 段） | 与 list/detail 契约一致 | 2026-11-04 | IssueBoard.vue:59 |
| D9 | 排除 Cycles、共享 Views 打磨、Labels **L**、G-then-X 导航和弦、模态创建、远程推送 | Way 拍板；Cycles = E6 | 2026-11-04 | 指派纪要 |
| D10 | ⌘B/Ctrl+B 切换 list↔board，状态与列表页按钮共享单例 | PRD / Way 加厚 | 2026-11-04 | S3 |

### 方案比选（锁定 D1）

| 方案 | 描述 | 结论 |
|---|---|---|
| **A（选定）** | 升级 global-search → Command Palette + vueuse 热键层 | **锁定** |
| B | 另开 palette，保留菜单-only GlobalSearch | 拒绝：双入口重复 |
| C | 引入 cmdk / 第三方 palette | 拒绝：新依赖；Naive NModal + vueuse 足够 |

## Exclusions

- Cycles（**E6 only**）
- 工作区共享 Saved Views 打磨
- Labels 热键 **L** / Labels 打磨
- G-then-X 两段式导航和弦（可选延后另 Epic）
- 模态内嵌创建 Issue composer（先 `/issue/create`）
- 邮件 / IM 外发
- 远程 push / PR（本批仅本地 worktree）
- mission-center 前端复活、计费、SSO 大改、Orca/Jira 变更

## Asset Disposition

| asset | disposition | note | date |
|---|---|---|---|
| `layouts/modules/global-search/*` | **upgrade** | 菜单搜索保留为 Actions/Menus 分组；扩展实体与命令 | 2026-11-04 |
| `theme.header.globalSearch.visible` | **narrow** | 仅 header 图标；不控 ⌘K | 2026-11-04 |
| `@vueuse/core` 14.1.0 | reuse | onKeyStroke / debounce / editable 检测 | 2026-11-04 |
| `issueApi` updateStatus / updateAssignee / updatePriority | reuse | S3 pickers 直调 | 2026-11-04 |
| `GET /api/issues?search=` + `?by_code=true` | reuse | S2 实体检索 | 2026-11-04 |
| `fetchSavedViews` / 列表 apply | reuse | S2 Views 分组 | 2026-11-04 |
| `fetchProjectList` / project-detail | reuse | S2 Projects | 2026-11-04 |
| Inbox `/inbox` + inbox API | reuse | 跳转 Inbox；不在面板内标已读强制 | 2026-11-04 |
| Cycle 模型 | **absent** | E6 | 2026-11-04 |

## Open Questions

| id | question | status | resolution |
|---|---|---|---|
| Q1 | 独立 palette 还是升级 global-search？ | closed | 升级（D1）；拒 B/C |
| Q2 | 创建用页还是模态？ | closed | `/issue/create` 页（D4） |
| Q3 | 热键库？ | closed | 仅 vueuse（D2） |
| Q4 | 主题隐藏搜索是否禁 ⌘K？ | closed | 不禁用（D3） |

无阻塞 Open Questions。

## Cross-cutting

| concern | owning epic | note |
|---|---|---|
| 租户隔离 | E3/E5 | 面板 API 调用带既有 `X-Workspace-Id` |
| DESIGN.md 视觉令牌 | E5 | Naive / soybean / design-system.css；面板宽度可沿用 ~630px |
| 焦点与可编辑忽略 | E5 | 全站一致；S3 验收必测 |
| 门禁 | E5 | AGENTS.md；PG `opentask-pg-test`；本地不推远程 |
| 汇报节奏 | E5 | **整 Epic 一次回执**；Sprint 中间不逐个找 Yuri/Way 验收 |

## Overall Acceptance Scenarios

| id | scenario | how to verify | expected |
|---|---|---|---|
| R1 | ⌘K / Ctrl+K 打开面板 | 登录后任意 shell 页按快捷键 | 面板打开；Esc 关闭 |
| R2 | 主题隐藏搜索图标仍可 ⌘K | 关 `globalSearch.visible` 后再 ⌘K | 面板仍开；header 无图标可接受 |
| R3 | 动作跳转 | 面板选 Issue 列表 / Create / Projects / Inbox | 路由正确 |
| R4 | Issue 实体跳转 | 搜标题或精确 code | 进 `/issue/detail?id=` |
| R5 | Saved View 应用 | 面板选视图 | 到列表且筛选恢复 |
| R6 | 焦点 + S/A/P/I | 列表/看板聚焦一行后按键 | picker 或指派成功；详情页同理 |
| R7 | C 创建 | 任意处按 C（非输入态） | 进 `/issue/create` |
| R8 | 输入态忽略 | 在 input 中按 C/A/S… | 不触发命令（⌘K 是否放行：允许打开面板，与 Linear 接近；单键忽略） |
| R9 | 看板 URL | 看板点开 Issue | URL 为 `/issue/detail?id=…` 非 path 段 |
| R10 | ⌘B 切视图 | 在 `/issue/list` 按 ⌘B/Ctrl+B | list↔board 与按钮同步 |

```supervibe-acceptance-plan
{
  "schema": 1,
  "scope": "epic",
  "scenarios": [
    {
      "id": "R1",
      "goal": "⌘K/Ctrl+K 打开命令面板",
      "steps": ["登录进入 app shell", "按 Meta+K 或 Ctrl+K", "Esc 关闭"],
      "expected": "面板开关正常",
      "required": true,
      "modality": "browser",
      "environment": "real"
    },
    {
      "id": "R2",
      "goal": "主题隐藏搜索按钮不禁用 ⌘K",
      "steps": ["关闭 header globalSearch.visible", "按 ⌘K"],
      "expected": "面板仍可打开",
      "required": true,
      "modality": "browser",
      "environment": "real"
    },
    {
      "id": "R3",
      "goal": "动作跳转",
      "steps": ["打开面板", "选择 Issues / Create / Projects / Inbox"],
      "expected": "路由正确",
      "required": true,
      "modality": "browser",
      "environment": "real"
    },
    {
      "id": "R4",
      "goal": "Issue 实体搜索跳转",
      "steps": ["搜标题或 issue_code", "Enter"],
      "expected": "/issue/detail?id=",
      "required": true,
      "modality": "browser",
      "environment": "real"
    },
    {
      "id": "R5",
      "goal": "Saved View 从面板应用",
      "steps": ["面板选 Saved View"],
      "expected": "列表筛选与视图一致",
      "required": true,
      "modality": "browser",
      "environment": "real"
    },
    {
      "id": "R6",
      "goal": "焦点 Issue 上 A/S/P/I",
      "steps": ["列表或看板聚焦", "按 S/A/P/I"],
      "expected": "状态/指派/优先级变更或指派给我",
      "required": true,
      "modality": "browser",
      "environment": "real"
    },
    {
      "id": "R7",
      "goal": "C 创建",
      "steps": ["非输入态按 C"],
      "expected": "/issue/create",
      "required": true,
      "modality": "browser",
      "environment": "real"
    },
    {
      "id": "R8",
      "goal": "可编辑区域忽略单键热键",
      "steps": ["focus input", "按 C"],
      "expected": "不跳转创建页",
      "required": true,
      "modality": "browser",
      "environment": "real"
    },
    {
      "id": "R9",
      "goal": "看板详情 URL 使用 ?id=",
      "steps": ["看板打开 Issue"],
      "expected": "query id，非 /issue/detail/:id path",
      "required": true,
      "modality": "browser",
      "environment": "real"
    },
    {
      "id": "R10",
      "goal": "⌘B/Ctrl+B 切换 Board↔List",
      "steps": ["打开 /issue/list", "按 Meta+B 或 Ctrl+B"],
      "expected": "viewMode 与 UI 按钮同步翻转",
      "required": true,
      "modality": "browser",
      "environment": "real"
    }
  ]
}
```

## 进度注记

- 2026-11-04（UTC+8）：E5 启动；Way（经 Yuri）拍板加厚范围：⌘K + 全站跳转 + C/A/S/P/I + 焦点；方案 A 升级 global-search；分支 `sprint/E5-S1`（基 E4-S3 tip `1e03724`）；worktree `/workspace/opentask-worktrees/E5-S1`；整 Epic 一次回执；不推远程。

- 2026-11-04（UTC+8）：E5-S1 closed（本地 tip `0063b58`）；整 Epic 仍 active。北星补充：⌘B Board↔List 记入 S3，不回灌 S1。

- 2026-11-04（UTC+8）：E5-S2 closed（本地 tip `9dc0e9e`）；实体搜索 Issues/Projects/Views + `?view=` apply；Epic 仍 active → 待 E5-S3。

- 2026-11-04（UTC+8）：E5-S3 closed；焦点 + C/A/S/P/I + ⌘B + 看板 `?id=`；Epic **local-complete**（merged-commit null；未推远程）。tip 见 acceptance。
