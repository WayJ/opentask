# E6 设计：Cycles（厚）· Workspace 冲刺 · 归属 · Rollover · 容量

日期：2026-11-04  
Epic：E6  
状态：active（S1 本地 closed：CRUD+设置 UI；S2/S3 待做）  
基线：`sprint/E5-S3` @ `da13c86`；worktree `/workspace/opentask-worktrees/E6-S1`（分支 `sprint/E6-S1`）  
北星：OpenTask Linear PRD §E6

## 1. 目标

对齐 Linear Cycles，交付：

1. **S1** Cycle CRUD API + Alembic + Workspace Cycles 设置列表 UI（启用、列表、创建 upcoming）
2. **S2** `Issue.cycle_id` + 列表/看板筛选 + 指派 + ⌘K Cycles 跳转/筛选；可选 `estimate_points` 钩子
3. **S3** complete/rollover + 容量 hint + 空状态打磨 + Epic local-complete

不做：多 Team 日历、Slack、精修 velocity 图、Initiatives、接通 Jira `sprint` JQL、远程推送。

## 2. 探索事实（Phase 1 inventory）

### 2.1 Issue 模型（无 Cycle）

路径：`backend/opentask/models/issue/model.py`

| 字段 | 现状 |
|---|---|
| `workspace_id` | 可空 FK → workspaces |
| `project_id` | 可空（无 FK 约束，仅索引） |
| `parent_issue_id` | E4-S3 FK → issues |
| `estimated_hours` / `actual_hours` | Numeric(5,2) 可空 |
| **`cycle_id`** | **不存在** |
| **`estimate_points`** | **不存在** |

`IssueQueryParams`（`schema.py`）：`type/status/priority/project_id/assignee_id/reporter_id/search` —— **无 cycle_id**。  
`IssueService.get_issues` 按上述字段 where；工作区隔离已有。

### 2.2 Alembic / API 样板

| 样板 | 路径 | 可抄点 |
|---|---|---|
| 新表 | `alembic/versions/2026_11_04_0100-d0e1f2a3b4c5_issue_saved_views.py` | inspect-if-exists；FK CASCADE；复合索引 |
| 加列 | `...0200-e1f2a3b4c5d6_issue_parent_issue_id.py` | inspect columns；可空 FK；索引 |
| 当前 head | `e1f2a3b4c5d6` | E6 新 revision `down_revision = e1f2a3b4c5d6` |
| 租户 API | `api/saved_views/router.py` + `api/workspace/deps.py` | `require_workspace_context` / `X-Workspace-Id` |
| 注册 | `opentask/app.py` | `include_router(saved_views_router)` 同级加 `cycles_router` |

### 2.3 Workspace

`Workspace` 现仅有 `id/name/slug/description/created_*` —— **无** `cycles_enabled` 等设置列。  
FE：`service/api/workspace.ts` + header `workspace-switcher.vue`；**无**独立 Workspace Settings 页 → S1 **新建** Cycles 设置视图（建议路由 `/workspace/cycles` 或 `/settings/cycles`）。

### 2.4 列表 / 看板筛选钩子

FE：`views/issue/list/index.vue`  
`filters = { status, priority, type, project_id, search }` —— 客户端再滤一遍；Saved View `filter_json` 对齐同一形状。  
Board：同页 `viewMode` + `IssueBoard.vue`，共用 `filteredIssues`。  
S2：`filters.cycle_id` + API query +（可选）`groupBy: 'cycle'` 后置，**本 Epic 筛选优先于 groupBy**。

### 2.5 ⌘K 扩展点（E5）

| 资产 | 扩展方式 |
|---|---|
| `PaletteItemKind` | 现 `'action'\|'menu'\|'issue'\|'project'\|'saved_view'` → 加 `'cycle'` |
| `useCommandPalette.setEntitySources` | 加 `cycles: PaletteItem[]`（或并行 `setCycleSources`） |
| `buildPaletteGroups` | 新组 `cycles`；label i18n |
| `command-palette-host.vue` | debounce 拉取 `fetchCycles`；run → 跳设置或 `/issue/list?cycle_id=` |
| Actions | 可选静态 `nav.cycles` → 设置页 |

### 2.6 Jira

`api/jira/jql.py`：`sprint*` 子句 **forced_empty**。E6 **不改**；产品 Cycle 与 Jira sprint 解耦。

## 3. 架构总览

```
Workspace (cycles_enabled, duration, rollover_policy, capacity_lookback_n)
    └── Cycle[] (upcoming | active | completed)
            ↑ cycle_id
         Issue[]

API /api/cycles ── CycleService ── cycles table
Issue PATCH/list ── IssueService (+ cycle_id filter)
FE Settings /workspace/cycles ── list + enable + create
FE Issue list/board ── filters.cycle_id + assign control
⌘K ── kind=cycle group
S3 ── POST /cycles/{id}/complete → rollover + capacity GET
```

## 4. Schema 草图

### 4.1 `cycles`

```text
cycles
  id                String(36) PK
  workspace_id      String(36) FK workspaces.id ON DELETE CASCADE NOT NULL
  name              String(128) NOT NULL          # 如 "Cycle 12" 或自定义
  number            Integer NULL                 # 工作区内自增序号（可选展示）
  status            String(20) NOT NULL           # upcoming | active | completed
  starts_at         DateTime NOT NULL
  ends_at           DateTime NOT NULL
  completed_at      DateTime NULL
  created_at        DateTime NOT NULL
  updated_at        DateTime NOT NULL

Indexes:
  ix_cycles_workspace_id
  idx_cycles_ws_status (workspace_id, status)
  idx_cycles_ws_starts (workspace_id, starts_at)
```

约束（服务层，非 DB 唯一强制也可）：

- 同一 `workspace_id` 至多一条 `status='active'`
- `ends_at > starts_at`
- `completed` 必须有 `completed_at`

### 4.2 Workspace 设置列（S1 migration 同批或紧随）

```text
workspaces
  + cycles_enabled       Boolean NOT NULL DEFAULT false
  + cycle_duration_days  Integer NOT NULL DEFAULT 14
  + cycle_rollover_policy String(32) NOT NULL DEFAULT 'into_next'
       # into_next | leave_unassigned
  + cycle_capacity_lookback Integer NOT NULL DEFAULT 3
```

### 4.3 Issue 扩展（S2）

```text
issues
  + cycle_id         String(36) NULL FK cycles.id ON DELETE SET NULL, index
  + estimate_points  Numeric(8,2) NULL   # 可选钩子；与 estimated_hours 并存
```

`IssueBase` / `IssueUpdate` / `IssueResponse` / `IssueQueryParams` 同步加字段。

## 5. API 契约

前缀：`/api/cycles`；依赖：登录 + `X-Workspace-Id` + member。

| Method | Path | 角色 | Sprint | 说明 |
|---|---|---|---|---|
| GET | `/api/cycles` | viewer+ | S1 | query: `status?`；本 workspace |
| POST | `/api/cycles` | member+ | S1 | body: name?, starts_at, ends_at；默认 status=upcoming |
| GET | `/api/cycles/{id}` | viewer+ | S1 | |
| PATCH | `/api/cycles/{id}` | member+ | S1 | name / dates；限制 completed 不可改区间（可放宽为仅 name） |
| DELETE | `/api/cycles/{id}` | member+ | S1 | 仅 upcoming（或无 issue 时）；active/completed 拒删或需 force（S1：upcoming only） |
| POST | `/api/cycles/{id}/activate` | member+ | S1/S3 | upcoming→active；若已有 active → 400 或自动 complete 旧（**锁定 S3：须先 complete**） |
| POST | `/api/cycles/{id}/complete` | member+ | S3 | active→completed；按 rollover_policy 迁移未完成 Issue |
| GET | `/api/cycles/capacity-hint` | viewer+ | S3 | query: `cycle_id?`；返回 suggested_capacity + basis |
| POST | `/api/cycles/generate-upcoming` | member+ | S3（UI 可 S1 调简化版） | 按 duration 从 last ends_at 或 now 生成下一条 |

Issue 侧（S2）：

| Method | 变更 |
|---|---|
| GET `/api/issues` | `cycle_id` query |
| POST/PATCH Issue | 可写 `cycle_id` / `estimate_points` |
| PUT `/api/issues/{id}/cycle` | 可选专用端点（与 assignee 模式一致，推荐） |

Workspace PATCH（S1）：扩展既有 `PATCH /api/workspaces/{id}` 允许 owner 写 `cycles_enabled` 等（或专用 `PATCH .../cycle-settings`）。

### 5.1 Rollover 语义（S3）

对 `complete(cycle_id)`：

1. 校验 status=active、workspace 匹配
2. 找「下一」Cycle：同 workspace、`status=upcoming`、`starts_at` 最小且 ≥ 当前 `ends_at`（若无则按 `starts_at` 升序第一条 upcoming）
3. 未完成 = `status NOT IN ('resolved','closed')` 且 `cycle_id = current`
4. `into_next`：若存在下一 → 批量 `cycle_id = next.id`；若无下一 → 可自动 `generate-upcoming` 再滚（**锁定：自动生成一条再滚**）或 `leave_unassigned` 若策略为 leave
5. `leave_unassigned`：未完成 `cycle_id = NULL`
6. 当前 → `completed`，`completed_at=now`
7. **不**自动 activate 下一（用户显式 activate；设置页可提供「结束并开始下一」组合按钮，内部 complete + activate）

### 5.2 容量 hint（S3）

```text
basis = "history" | "members"
suggested_capacity: number   # Issue 完成数均值，或成员数
lookback_n: int
samples: [{ cycle_id, name, completed_issue_count, completed_points? }]
```

- 历史：近 N 个 `completed` Cycle，计数 `status in (resolved,closed)` 且当时归属该 Cycle 的 Issue。  
  **简化（锁定）**：用 **当前仍挂在该 Cycle 上** 且已完成的 Issue 数（rollover 后未完成已离开，完成留存 → 近似「该 Cycle 完成数」）。
- 若有任意 `estimate_points` 非空：可额外返回 `suggested_points` 均值；主 hint 仍给 Issue 计数以免空点误导。
- 无 completed 历史：`basis=members`，`suggested_capacity = member_count`。

## 6. 前端

### 6.1 S1 设置页

- 路由：建议 `elegant-router` 增加 `/workspace/cycles`（中文「冲刺 / Cycles」）
- 内容：
  - Switch：`cycles_enabled`（owner；member 可见只读）
  - 展示 duration / rollover / lookback（S1 可只读默认 + 简单表单）
  - Cycle 表格：name、status tag、起止、操作（编辑 upcoming、删除 upcoming）
  - 「创建 Cycle」：默认 starts=今天或上一段 ends+1，ends=starts+duration
- `cycles_enabled=false`：主区空状态 + CTA「启用 Cycles」

### 6.2 S2 列表 / 看板 / 指派

- 工具栏 `NSelect`：Cycle（含「全部」「无 Cycle」）
- Issue 行/详情：Cycle 选择器；创建表单可选
- `?cycle_id=` query 与 Saved View `filter_json.cycle_id` 互通
- Board 共用同一 `filters.cycle_id`

### 6.3 S2 ⌘K

- `kind: 'cycle'`
- run：`router.push({ path: '/issue/list', query: { cycle_id } })` 或打开设置
- 空 query 可不展示；有 query 时搜 name

### 6.4 S3 UI

- Active Cycle 头：进度（完成/总数）、容量 hint 文案
- 「结束 Cycle」确认框：预览将 rollover 的数量
- 「生成下一 Cycle」按钮（无 upcoming 空状态）

## 7. 权限

| 动作 | viewer | member | owner |
|---|---|---|---|
| 读 Cycles / capacity | ✓ | ✓ | ✓ |
| CRUD Cycle / 指派 Issue.cycle | | ✓ | ✓ |
| 改 cycles_enabled 等设置 | | | ✓ |
| complete / activate / generate | | ✓ | ✓ |

## 8. 测试策略

| 层 | 覆盖 |
|---|---|
| API pytest | CRUD；跨 workspace 403/404；至多一 active；complete+rollover 两种策略；capacity 有/无历史；viewer 只读 |
| FE unit | palette cycle group；filter 应用；可选 composable |
| 回归 | 全量 pytest；lint/build |
| 浏览器 | Epic R 场景；可 optional blocked |

## 9. Sprint 边界（再确认）

| Sprint | 含 | 不含（留给后续 Sprint） |
|---|---|---|
| S1 | `cycles` 表、workspace 设置列、`/api/cycles` CRUD、设置列表 UI、启用开关 | `Issue.cycle_id`、rollover、capacity、⌘K |
| S2 | `cycle_id`+points、Issue API/FE 筛选指派、⌘K | complete 自动化 |
| S3 | activate/complete/rollover、capacity、generate-upcoming 打磨、Epic 收口 | E7+ |

## 10. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 完成数在 rollover 后难追溯 | 锁定「完成 Issue 留在原 Cycle」；未完成才搬 |
| S1 无 cycle_id 时设置页偏「空壳」 | S1 DoD 明确：可建 upcoming/列表/启用；挂 Issue 属 S2 |
| 与 Jira sprint 混淆 | 文档 + 不改 JQL；命名统一 Cycle |
| Epic 过厚 | 三 Sprint 内切；整包验收 |

## 11. Self-review

- 无 TBD 阻塞；Q1–Q4 已关
- 与 PRD AC 对齐：模型/归属/筛选/⌘K/rollover/容量/空状态/排除项均有落点
- `estimate_points` 标 optional，不阻塞 S1
