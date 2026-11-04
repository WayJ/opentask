# E8 设计：Projects 里程碑 · Health · Timeline · Favorites

日期：2026-11-04  
Epic：E8  
状态：designed（Phase 1；**无**产品实现）  
基线：`sprint/E7-S3` @ `68740f7`；worktree `/workspace/opentask-worktrees/E8-S1`（分支 `sprint/E8-S1`）  
北星：OpenTask Linear PRD §E8  
Alembic head：`d4e5f6a7b8c0`（`issue_display_prefs`）

## 1. 目标

对齐 Linear Projects，交付厚 Epic：

1. **S1** Milestones CRUD + `issues.milestone_id` + `projects.starts_at`/`target_date` + 项目详情里程碑/日期 UI + Issue 挂载
2. **S2** Health updates（枚举+文本）+ 历史 + 项目 header 最新态 + `project_watchers` + Inbox fanout + Timeline MVP（week/month + empty-state）
3. **S3** Sidebar Favorites（Project / Saved View / Issue）+ 打磨 + Epic local-complete

不做：Initiative 依赖图、Slack 同步、原生移动端、远程推送、E9+。

## 2. 探索事实（Phase 1 inventory）

### 2.1 Project 模型 / API / FE

| 资产 | 路径 | 现状 |
|---|---|---|
| `Project` | `backend/opentask/models/requirement/model.py` | `id/name/description/is_active/created_at/updated_at/dept_id/workspace_id`；**无** starts/target/health |
| 唯一 | `uq_projects_workspace_name` | 工作区 + name |
| Service | `services/project_service.py` | CRUD；update 仅 name/description |
| API | `api/project/router.py` 前缀 `/api/projects` | 含 nested repos；**无** milestones/health |
| FE API | `frontend/src/service/api/project.ts` | list/detail/create/update/delete + repos |
| FE 类型 | `typings/api/project.d.ts` | 同上字段；无日期/健康 |
| FE 页 | `views/workflow/projects` · `project-detail` | 列表 + 详情（名/描述/仓库）；路由 query `?id=` |
| 路由 | `/workflow/projects` · `/workflow/project-detail` | soybean elegant |

### 2.2 Issue 与日期

| 字段 | 现状 | E8 含义 |
|---|---|---|
| `project_id` | 可空 **无 FK**（仅索引） | 继续服务层校验；本 Epic 不加强制 FK |
| `due_date` | DateTime 可空 + 索引 | Timeline 可选 Issue 点 |
| `cycle_id` / `estimate_points` | E6 已有 | 无关里程碑 |
| `start_date` | **不存在** | 不新增（Q3） |
| `milestone_id` | **不存在** | S1 新增 |

Issue 活动「timeline」API（`/api/issues/{id}/timeline`）与 Requirement timeline = **活动/事件流**，与本 Epic 项目 Timeline **视图**同名异物 → **leave**。

### 2.3 Inbox / Notification

| 资产 | 现状 |
|---|---|
| 表 `notifications` | E3-S3；`type` 注释 `assigned\|commented\|mentioned`；`resource_type` 默认 issue |
| `NotificationService.create` | 通用；跳过 recipient==actor |
| 专用 | `notify_assigned` / `notify_comment` |
| API | `/api/inbox` list / read / read-all |
| Watcher/Follower | **不存在**（无 project_watchers） |

结论：S2 扩 type + `notify_project_health`；必须新建 watchers 表，避免全员轰炸。

### 2.4 Sidebar / Favorites 现状

| 资产 | 现状 |
|---|---|
| `global-sider/index.vue` | Logo + `#GLOBAL_SIDER_MENU_ID` 挂载点；**无**自定义收藏区 |
| 菜单 | `routeStore.menus` → soybean 垂直/混合菜单 |
| `issue_saved_views.is_favorite` | 个人星标；列表页 chips；**共享 View 强制 false**（E7）；注释写明侧栏 Favorites → E8 |
| 统一 Favorites 表 | **不存在** |

### 2.5 Display / 视图模式

`view_mode` ∈ `{list, board}` only（prefs + Saved View display_json）。Timeline **不是** Issue 列表第三模式，而是 **项目页**视图。

### 2.6 Alembic

当前 head：`d4e5f6a7b8c0`。E8-S1 新 revision：`down_revision = d4e5f6a7b8c0`。

## 3. 架构总览

```
Workspace
  └── Project[]  (+ starts_at, target_date, health_* cache)
        ├── Milestone[]
        │      ↑ milestone_id
        │    Issue[]  (due_date 可选绘入 Timeline)
        ├── ProjectHealthUpdate[]
        └── ProjectWatcher[]

User + Workspace
  └── Favorite[]  (target_type: project | saved_view | issue)

API
  /api/projects/{id}/milestones ── MilestoneService          [S1]
  /api/projects/{id} PATCH dates ── ProjectService           [S1]
  Issue PATCH milestone_id ── IssueService                   [S1]
  /api/projects/{id}/health ── HealthService + Inbox         [S2]
  /api/projects/{id}/timeline ── 聚合 DTO（只读）            [S2]
  /api/projects/{id}/watchers ── WatcherService              [S2]
  /api/favorites ── FavoriteService                          [S3]

FE
  project-detail：日期 + 里程碑面板                          [S1]
  project-detail：Health 控件 + Timeline tab                 [S2]
  global-sider：FavoritesNav                                 [S3]
  issue detail/list：milestone 字段                          [S1]
```

## 4. Schema 草图

### 4.1 `milestones`（S1）

```text
milestones
  id             String(36) PK
  workspace_id   String(36) FK workspaces.id ON DELETE CASCADE NOT NULL
  project_id     String(36) FK projects.id ON DELETE CASCADE NOT NULL
  name           String(255) NOT NULL
  description    Text NULL
  target_date    DateTime NULL
  status         String(20) NOT NULL DEFAULT 'planned'   # planned | done
  position       Integer NOT NULL DEFAULT 0
  created_at     DateTime NOT NULL
  updated_at     DateTime NOT NULL

Indexes:
  ix_milestones_project_id
  ix_milestones_workspace_id
  ix_milestones_project_position (project_id, position)
```

### 4.2 `issues.milestone_id`（S1）

```text
issues
  milestone_id   String(36) NULL FK milestones.id ON DELETE SET NULL

Indexes:
  idx_issues_milestone (milestone_id)
```

服务层：若设置 milestone_id，则 milestone.project_id 必须等于 issue.project_id（issue 无 project 时拒绝挂载）。

### 4.3 `projects` 日期（S1）+ health 缓存（S2）

```text
projects
  starts_at           DateTime NULL          # S1
  target_date         DateTime NULL          # S1
  health_status       String(20) NULL        # S2: on_track|at_risk|off_track
  health_note         Text NULL             # S2
  health_updated_at   DateTime NULL          # S2
  health_updated_by   String(36) NULL        # S2 user id
```

### 4.4 `project_health_updates`（S2）

```text
project_health_updates
  id              String(36) PK
  workspace_id    String(36) FK workspaces.id ON DELETE CASCADE NOT NULL
  project_id      String(36) FK projects.id ON DELETE CASCADE NOT NULL
  status          String(20) NOT NULL
  note            Text NULL
  actor_user_id   String(36) NOT NULL
  created_at      DateTime NOT NULL

Indexes:
  ix_phu_project_created (project_id, created_at)
```

### 4.5 `project_watchers`（S2）

```text
project_watchers
  id              String(36) PK
  workspace_id    String(36) FK workspaces.id ON DELETE CASCADE NOT NULL
  project_id      String(36) FK projects.id ON DELETE CASCADE NOT NULL
  user_id         String(36) NOT NULL
  created_at      DateTime NOT NULL

Constraints:
  uq_project_watchers_project_user (project_id, user_id)
```

### 4.6 `favorites`（S3）

```text
favorites
  id              String(36) PK
  workspace_id    String(36) FK workspaces.id ON DELETE CASCADE NOT NULL
  user_id         String(36) NOT NULL
  target_type     String(20) NOT NULL   # project | saved_view | issue
  target_id       String(36) NOT NULL
  position        Integer NOT NULL DEFAULT 0
  created_at      DateTime NOT NULL

Constraints:
  uq_favorites_user_target (workspace_id, user_id, target_type, target_id)
Indexes:
  ix_favorites_user_ws_pos (user_id, workspace_id, position)
```

## 5. API 草图

### S1

| Method | Path | Note |
|---|---|---|
| GET/POST | `/api/projects/{project_id}/milestones` | list / create；强制 WS |
| GET/PATCH/DELETE | `/api/projects/{project_id}/milestones/{id}` | 同项目校验 |
| PATCH | `/api/projects/{id}` | 扩 `starts_at`/`target_date` |
| PATCH | `/api/issues/{id}` | 扩 `milestone_id`；list query 可选 `milestone_id` |

权限：读 member+viewer；写 member+；跨租户 404。

### S2

| Method | Path | Note |
|---|---|---|
| POST | `/api/projects/{id}/health` | body `{status, note?}` → 写历史 + 更新缓存 + fanout Inbox |
| GET | `/api/projects/{id}/health` | 最新 + 可选 `?history=1` |
| GET/POST/DELETE | `/api/projects/{id}/watchers` | 列表 / 自己订阅 / 退订 |
| GET | `/api/projects/{id}/timeline` | `{project, milestones[], issues[]}` + 建议 `zoom` 由 FE 本地 |

Inbox 行：`type=project_health`，`resource_type=project`，`resource_id=project_id`，title 含状态文案。

### S3

| Method | Path | Note |
|---|---|---|
| GET | `/api/favorites` | 当前用户 + WS；含轻量 target 摘要（name/code） |
| POST | `/api/favorites` | `{target_type, target_id}`；幂等 |
| PATCH | `/api/favorites/{id}` | position 重排（可选） |
| DELETE | `/api/favorites/{id}` | 或 POST unpin by target |

Pin `project` 时：**upsert** `project_watchers`（D7）。Unpin 不自动退订 watcher（避免误伤；可另提供 Unwatch）。

## 6. 前端要点

### 6.1 S1 项目 UI

- `project-detail`：编辑 starts/target；里程碑列表（名、target_date、status、排序）；创建/编辑/删除
- Issue 详情侧栏：Milestone 选择（过滤当前 project 的里程碑）
- Issue 列表：可选 `milestone_id` 筛选（最小：详情可挂即可，列表筛选同 Sprint 若有余力）

### 6.2 S2 Timeline + Health

- Header：健康徽章（绿/黄/红）+ 最近 note 摘要 + 「Update health」对话框
- Timeline tab：CSS/SVG 或轻量库；zoom toggle week/month；里程碑菱形；项目条；有 due 的 Issue
- Empty-state：无 starts/target 且无 milestones → 引导「设置项目日期」/「添加里程碑」
- Inbox FE：识别 `project_health` 跳转 project-detail

### 6.3 S3 Favorites

- 组件 `FavoritesNav.vue` 插入 `global-sider`（Logo 与菜单 div 之间）；折叠态仅图标
- 各实体页：Pin/Unpin 按钮（项目 header、Saved View 菜单、Issue 详情）
- **不**自动改 `is_favorite`；文案：「收藏到侧栏」vs「星标」

## 7. 测试计划（摘要）

| 层 | S1 | S2 | S3 |
|---|---|---|---|
| Pytest | milestones CRUD、跨项目/跨 WS、issue.milestone 校验、项目日期 PATCH | health 写历史+缓存、Inbox 条数/跳过 actor、watchers ACL、timeline DTO | favorites CRUD、唯一约束、跨用户不可见、pin project → watcher |
| Vitest/FE | 里程碑列表工具函数（若抽） | timeline 布局/zoom 纯函数、empty-state 条件 | favorites 排序/分组 |
| 门禁 | pytest 全量 + lint/build | 同 | 同 + Epic acceptance |

## 8. Sprint 切片与依赖

```
E7-S3@68740f7
    └── E8-S1 milestones + dates + issue.milestone_id + project UI
            └── E8-S2 health + watchers + Inbox + Timeline MVP
                    └── E8-S3 Favorites + polish → Epic local-complete → E9
```

## 9. 风险与缓解

| risk | mitigation |
|---|---|
| `issues.project_id` 无 FK，脏数据挂错里程碑 | 服务层强校验 milestone.project_id == issue.project_id |
| Timeline 无第三方库时周/月缩放手感差 | S2 MVP 用纯布局 + 固定日宽；允许后续换库 |
| Health 无 watcher 时静默失败 | 创建项目强制 actor watch；UI 明示 Watch |
| Favorites 与 View 星标用户混淆 | 文案/图标区分；不同步（Q4） |
| sider 多布局模式 | Favorites 挂在 `global-sider` 公共壳，覆盖 vertical 主路径；其它 layout 同插槽 |

## 10. 非目标回顾

Initiative 依赖图、Slack、原生移动、Issue start_date、强制 project_id FK、改活动流 timeline API、远程 push。
