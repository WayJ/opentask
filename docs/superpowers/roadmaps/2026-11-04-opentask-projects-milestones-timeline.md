---
epic: E8
status: active
date: 2026-11-04
---

# OpenTask Linear 进阶：Projects 里程碑 · 健康 · Timeline · Favorites（厚）

产品参考 Linear Projects（Milestones / Health / Timeline）与侧栏 Favorites。在 E7（Labels / 共享 Views / Display）之上补齐「项目里程碑 + Issue 挂里程碑 + 健康更新（Inbox）+ Timeline 周/月缩放 + 侧栏 Favorites（Project / Saved View / Issue）」。本 Epic 为整包一个 Roadmap。Initiative 依赖图、Slack 同步、原生移动端明确排除。

北星：[OpenTask · Linear 对齐完整 PRD](https://cursor.com/canvas/store-adddb90c-33cd-496c-a6c4-08755560f586/656f4217-cbf0-48a3-9edb-168b4a36cbee) §E8。

基线 tip：`sprint/E7-S3` @ `68740f7`；worktree `/workspace/opentask-worktrees/E8-S1` · 分支 `sprint/E8-S1`。本地不推远程。

## Deliverables

| deliverable | note |
|---|---|
| Project **milestones** | 新表 `milestones`（挂 `project_id` + `workspace_id`）；CRUD API；项目详情可管理；`issues.milestone_id` 可空 FK |
| Project **health** | 枚举 `on_track` / `at_risk` / `off_track` + 说明文本；历史表；最新态展示在项目 header；可写 Inbox 给 watchers（**无** Slack） |
| **Timeline** 视图 | 按项目 `starts_at` / `target_date` + milestones（+ 可选 Issue `due_date`）渲染；缩放 week / month；空状态引导补日期/里程碑 |
| Sidebar **Favorites** | 新表 `favorites`：pin Project / Saved View / Issue；**独立于** `issue_saved_views.is_favorite` 星标 |
| 项目日期字段 | `projects.starts_at` / `projects.target_date`（Timeline 所需；S1 与里程碑同迁） |

## Definition of Done

- [ ] Epic 下全部 Sprint（S1–S3）已 acceptance 且 state=closed；合并证据本地台账（merged-commit 仍 null / 未推远程）
- [ ] `cd backend && uv run pytest tests/ -v` 全绿（含 milestones CRUD / 跨租户 / health+Inbox / favorites ACL）
- [ ] `cd frontend && npm run lint && npm run build` 通过（0 errors）
- [ ] 可为项目建/改/删里程碑；Issue 可挂/换/清空里程碑；项目 UI 可见里程碑列表
- [ ] 可发健康更新；项目 header 显示最新状态；watchers 收到 Inbox（type=`project_health`）
- [ ] 项目 Timeline 可 week/month 缩放；无日期时空状态有引导
- [ ] 侧栏 Favorites 可 pin/unpin Project、Saved View、Issue 并跳转；与 View 星标语义分离
- [ ] DESIGN.md / Naive UI / soybean 令牌被前端改动遵守；无 Initiative 依赖图 / Slack / 原生移动端
- [ ] 整 Epic 一次回执 Yuri/Way（路径、分支 tip、门禁、acceptance）

## Sprint Breakdown

| sprint | state | note |
|---|---|---|
| S1 | **closed** | Milestones + `issue.milestone_id` + 项目日期 + 项目 UI。acceptance: `docs/superpowers/acceptances/2026-11-04-E8-S1-acceptance.md`；impl `56c886e` |
| S2 | **active** | **Health updates + Inbox fanout + Timeline MVP**（week/month + empty-state）。plan: `docs/superpowers/sprints/2026-11-04-E8-S2-plan.md` |
| S3 | planned | **Sidebar Favorites** + 打磨（⌘K 可选跳转、空状态、header）+ Epic local-complete |

推荐顺序理由：先固化里程碑与项目时间盒真相源（S1，解锁 Issue 归属与 Timeline 数据），再做健康广播与 Timeline 呈现（S2，依赖日期/里程碑），最后侧栏 Favorites 与整包打磨（S3，Favorites 可兼作 health watcher 补源）。

## Decisions (ADR)

| id | decision | rationale | date | evidence |
|---|---|---|---|---|
| D1 | 新建 `milestones` 表；挂 `project_id` + 冗余 `workspace_id` | 租户过滤与项目级联；对齐 cycles 模式 | 2026-11-04 | 探索；PRD §E8 |
| D2 | `issues.milestone_id` 可空 FK → milestones ON DELETE SET NULL | 删里程碑不删 Issue；与 `cycle_id` 一致 | 2026-11-04 | E6 先例 |
| D3 | 项目加 `starts_at` / `target_date`（可空 DateTime） | Timeline 需要项目条；现状 Project **无**任何日期列 | 2026-11-04 | 探索 `models/requirement/model.py` |
| D4 | Health：历史表 `project_health_updates` + 项目上缓存最新四列（status/note/updated_at/by） | header 零 join；历史可审计 | 2026-11-04 | Linear 手感 |
| D5 | Health 枚举字符串：`on_track` \| `at_risk` \| `off_track` | PRD；存 String(20) | 2026-11-04 | PRD |
| D6 | Inbox：扩展 `Notification.type=project_health`，`resource_type=project`；**不**接 Slack/邮件 | 现有 NotificationService.create 已通用；类型注释放宽 | 2026-11-04 | `services/notification/service.py` |
| D7 | Watchers：新表 `project_watchers`；创建项目时 actor 自动 watch；健康更新 fanout 给 watchers（≠ actor）；S3 Favorites pin Project 时可 upsert watcher | 现状无 watcher/follower；不能静默 spam 全 WS | 2026-11-04 | 探索缺口 |
| D8 | Timeline **项目作用域**路由（扩展 project-detail 或 `/workflow/projects/:id/timeline`）；**不**把 `display.view_mode` 扩成 timeline | Issue 列表仍 list\|board；Timeline 是项目甘特/泳道时间轴 | 2026-11-04 | `display-prefs.ts` |
| D9 | Timeline 元素：项目条（starts→target）+ milestone 竖线/标志 + 可选带 `due_date` 的 Issue 点/条；缩放 `week` \| `month` | PRD；Issue 无 start_date → 仅 due 或挂在里程碑下展示 | 2026-11-04 | 探索 |
| D10 | Favorites 新表；`target_type ∈ {project,saved_view,issue}`；**不**复用/改写 `issue_saved_views.is_favorite` | E7 已声明侧栏 Favorites ≠ View 星标 | 2026-11-04 | E7 design / saved_view service 注释 |
| D11 | Favorites 个人作用域（workspace_id + user_id）；侧栏插在 Logo 与 `GLOBAL_SIDER_MENU_ID` 菜单之间 | sider 现为菜单挂载点；需自定义块 | 2026-11-04 | `global-sider/index.vue` |
| D12 | `issues.project_id` **本 Epic 不强制加 FK**（基线仅索引）；`milestone_id` 新加真 FK；校验同 project 在服务层 | 存量脏数据风险；里程碑归属可服务层 assert | 2026-11-04 | Alembic baseline |
| D13 | 整 Epic 一次回执；Sprint 中间不逐个找 Yuri/Way 验收 | 与 E5–E7 节奏一致 | 2026-11-04 | Yuri |
| D14 | 排除：Initiative 依赖图、Slack 同步、原生移动端、远程 push、E9+ Triage/Templates | PRD / 指派 | 2026-11-04 | 指派 |

### 方案比选（锁定 D4 / D7 / D10）

| 主题 | A（选定） | B（拒绝） | C（拒绝） |
|---|---|---|---|
| Health 存储 | 历史表 + 项目缓存列 | 仅项目三列无历史 | 仅通知无项目列 |
| Watchers | `project_watchers` + 创建者自动 | 通知全 workspace members | 仅 Favorites（S3 才有，S2 无源） |
| Favorites | 独立 `favorites` 表 | 扩展 View.is_favorite 多态 | localStorage only |

## Exclusions

- Initiative 依赖图 / 路线图滚轮（E10）
- Slack / 邮件 / 外部 IM 同步健康更新
- 原生移动端 App
- Issue `start_date` 一等字段（可用 due_date；不强制本 Epic 加 start）
- 强制 `issues.project_id` → `projects.id` FK 回填大迁移
- 改写 Requirement「timeline」事件流或 Issue 活动 timeline API 语义
- 远程 push / PR（本批仅本地 worktree）
- mission-center 复活、计费、SSO 大改、E9 Triage

## Asset Disposition

| asset | disposition | note | date |
|---|---|---|---|
| `milestones` | **create** | S1；Alembic `down_revision = d4e5f6a7b8c0` | 2026-11-04 |
| `issues.milestone_id` | **add** | S1（可与 milestones 同 revision） | 2026-11-04 |
| `projects.starts_at` / `target_date` | **add** | S1 | 2026-11-04 |
| `projects.health_*` 缓存列 | **add** | S2 | 2026-11-04 |
| `project_health_updates` | **create** | S2 | 2026-11-04 |
| `project_watchers` | **create** | S2（S1 可不建） | 2026-11-04 |
| `favorites` | **create** | S3 | 2026-11-04 |
| `issue_saved_views.is_favorite` | **keep** | 列表星标语义不变；不驱动侧栏 | 2026-11-04 |
| `/api/projects` | **extend** | S1 日期字段；S1 nested milestones 或 `/api/milestones`；S2 health | 2026-11-04 |
| `/api/inbox` + NotificationService | **extend** | S2 新 type；序列化兼容 | 2026-11-04 |
| FE `workflow/project-detail` | **extend** | S1 里程碑+日期；S2 header health + Timeline tab | 2026-11-04 |
| FE `global-sider` | **extend** | S3 Favorites 块 | 2026-11-04 |
| Issue 详情/列表 | **extend** | S1 milestone 字段；筛选可选 | 2026-11-04 |
| ⌘K | **optional extend** | S3 可搜 Favorites / 跳 Timeline；非 S1 门禁 | 2026-11-04 |
| Issue/Requirement「timeline」API | **leave** | 活动流 ≠ 本 Epic Timeline 视图 | 2026-11-04 |

## Open Questions

| id | question | status | resolution |
|---|---|---|---|
| Q1 | milestones API 嵌套 `/api/projects/{id}/milestones` 还是顶层 `/api/milestones`？ | closed | **嵌套为主** + 可选 `GET /api/milestones?project_id=` 列表便利；写走嵌套（D 风格对齐 repos） |
| Q2 | Health watcher 在 Favorites 落地前如何取收件人？ | closed | S2 建 `project_watchers`；创建项目自动加入 actor；UI 提供 Watch/Unwatch；S3 pin Project → upsert watcher（D7） |
| Q3 | Timeline 是否展示无 due_date 的 Issue？ | closed | **默认不展示**横条；可在里程碑分组列表里看到；空状态引导补 due 或挂里程碑 |
| Q4 | Favorites 与 View.is_favorite 是否双向同步？ | closed | **不同步**（D10）；产品文案区分「星标视图」vs「侧栏收藏」 |
| Q5 | 里程碑是否需要 status（planned/done）？ | closed | S1 加可选 `status` String 默认 `planned`；完成可标 `done`（非门禁精修） |

## Next

1. ~~Phase 1 文档 / S1 实现~~ → S1 closed
2. 实现 E8-S2（Health + Timeline）；再 S3 Favorites → Epic local-complete
3. 整 Epic E8 本地收口后一次回执；controller 接 **E12**（invites + KEY-N + de-PGE），**不**接 E9
