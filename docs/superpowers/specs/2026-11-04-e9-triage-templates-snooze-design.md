# E9 设计：Triage · Templates · Inbox snooze

日期：2026-11-04  
Epic：E9  
状态：designed（Phase 1；**无**产品实现）  
基线：`sprint/E12-S3` @ `77990b4`；worktree `/workspace/opentask-worktrees/E9-S1`（分支 `sprint/E9-S1`）  
北星：OpenTask Linear PRD §E9  
Alembic head：`c9d0e1f2a3b5`（`workspace_invites`）

## 1. 目标

对齐 Linear 的入站处置、创建规范与通知延后：

1. **S1** 工作区 Triage 队列：`issues.triage_status`；list / accept / decline / duplicate；FE 侧栏入口与队列页
2. **S2** 工作区 Issue 模板 CRUD；创建 Issue / ⌘K 可选模板预填；以现有 FE `ISSUE_TEMPLATES` 为种子
3. **S3** Inbox 通知 `snoozed_until`；预设 snooze；到期懒再现；打磨 + Epic local-complete

不做：邮件 Inbox、强制 SMTP、Project 模板、外源自动入队、E10+、远程推送。

## 2. 探索事实（Phase 1 inventory）

### 2.1 Inbox / 通知

| 资产 | 路径 | 现状 |
|---|---|---|
| 模型 | `models/notification/model.py` | `notifications`：ws、recipient、actor、type、resource、title/body、`read_at`；**无** snooze 列 |
| 服务 | `services/notification/service.py` | create / notify_assigned / notify_comment / list / mark_read / mark_all_read |
| API | `api/inbox/router.py` | `GET /api/inbox`、`POST …/read`、`POST …/read-all`；`unread_only` |
| FE | `views/inbox/index.vue` + `service/api/inbox.ts` | 列表、仅未读、全部已读；**无** snooze UI |
| 触发 | assigned / commented / mentioned / project_health | 与 Triage **无关** |

结论：Inbox = 个人通知流。Snooze 加列即可。Triage **不得**复用 notifications。

### 2.2 Issue 模板

| 资产 | 现状 |
|---|---|
| FE 常量 | `frontend/src/constants/issueTemplates.ts`：5 套（bug_report / feature_request / …）含字段 schema |
| 组件 | `IssueTemplateSelector.vue` + `IssueTemplateForm.vue`；已挂 `views/issue/create/index.vue` |
| 测试 | `frontend/src/tests/issue/index.test.ts` 覆盖 Selector |
| 集合创建 | `views/issue/collection-create` 另有 markdown 快捷模板（非 Issue 模板） |
| BE | **无** `issue_templates` 表/API；`prompt_generator` 的 feature/bugfix 是 **PGE 任务提示词**，勿混用 |
| ⌘K | `command-palette` 有 createIssue 导航动作；**未**「选模板创建」 |

结论：S2 持久化 WS 模板并让 Selector 优先读 API；常量作 seed/offline fallback。

### 2.3 Triage / 入站

| 资产 | 现状 |
|---|---|
| `Issue.status` | ENUM open/in_progress/feedback/resolved/closed/rejected；**无** triage |
| `IssueRelation` | 含 duplicates 等；duplicate 动作可复用 |
| 侧栏 | 无 Triage 路由；Inbox 是通知页 |
| 外源 ingress | 无邮件/Slack→Issue；无公共表单 |

结论：S1 用 Issue 列 + API 入队；集成入队后置。

### 2.4 Alembic

当前 head：`c9d0e1f2a3b5`（workspace_invites）。E9-S1 新 revision：`down_revision = c9d0e1f2a3b5`。

## 3. 架构总览

```
Workspace
  └── Issue[]
        + triage_status: null | pending
        （accept → null + open；decline → rejected + null；
          duplicate → Relation(duplicates) + decline 语义）
  └── IssueTemplate[]     [S2]
        name, description, payload(JSON), sort_order, is_builtin_seed?

User Inbox (notifications)
  + snoozed_until           [S3]
  list: exclude snoozed_until > now()

FE
  /triage 队列页 + 侧栏          [S1]
  创建 / ⌘K 选模板              [S2]
  Inbox 行菜单 Snooze            [S3]
```

## 4. 数据模型

### 4.1 `issues.triage_status`（S1）

- 类型：`String(16)` nullable，索引 `(workspace_id, triage_status)` 部分可用
- 值：`pending` = 在队列；`NULL` = 不在队列
- 不引入 accepted/declined 枚举值（终态用 `status`）

### 4.2 `issue_templates`（S2）

| 列 | 说明 |
|---|---|
| id | uuid PK |
| workspace_id | FK CASCADE |
| name | 展示名 |
| description | 短说明 |
| icon | 可选字符串 |
| payload | JSON：`{ title?, description?, type?, priority?, labelIds?, projectId? }` |
| sort_order | int |
| created_by / created_at / updated_at | 审计 |
| uq | `(workspace_id, name)` 建议唯一 |

种子：工作区首次打开模板设置或迁移钩子，自 `ISSUE_TEMPLATES` 写入（可标 `source=seed`）。

### 4.3 `notifications.snoozed_until`（S3）

- `DateTime` nullable
- `list_for_user`：`(snoozed_until IS NULL OR snoozed_until <= now())`
- 可选 query `include_snoozed=true` 调试；默认 false
- 上限：API 拒 > now+90d；取消 snooze = 置 NULL

## 5. API 草图

### 5.1 Triage（S1）

| method | path | 行为 |
|---|---|---|
| GET | `/api/triage` | 当前 WS `triage_status=pending` Issue 列表（分页） |
| POST | `/api/triage` | body `{ issueId }` 或 `{ title,… }` 创建并入队；member+ |
| POST | `/api/triage/{issueId}/accept` | 清 triage；status→open（若已 rejected 则 open） |
| POST | `/api/triage/{issueId}/decline` | status→rejected；清 triage |
| POST | `/api/triage/{issueId}/duplicate` | body `{ duplicateOfIssueId }`；建 duplicates Relation；decline 语义 |

ACL：`require_workspace_context`；写操作 member/owner；viewer GET only。跨 WS issue → 404。

### 5.2 Templates（S2）

| method | path | 行为 |
|---|---|---|
| GET | `/api/issue-templates` | 列表（WS） |
| POST | `/api/issue-templates` | 创建；member+ |
| PATCH | `/api/issue-templates/{id}` | 更新 |
| DELETE | `/api/issue-templates/{id}` | 删除 |
| POST | `/api/issues`（既有） | 可选 `templateId`：服务端合并 payload 再创建 |

### 5.3 Inbox snooze（S3）

| method | path | 行为 |
|---|---|---|
| POST | `/api/inbox/{id}/snooze` | body `{ until: ISO }`；仅本人 |
| POST | `/api/inbox/{id}/unsnooze` | 清 `snoozed_until` |
| GET | `/api/inbox` | 默认过滤 snoozed |

## 6. FE

- **S1**：路由 `triage`（elegant-router）；侧栏 Inbox 附近；行操作 Accept / Decline / Mark duplicate（选目标 Issue）
- **S2**：`IssueTemplateSelector` 改读 API；设置页可 CRUD；⌘K 增「从模板创建」或创建页保留选择器
- **S3**：Inbox 行「延后」菜单（1h/3h/明天/下周一）；snoozed 角标可选

遵守 DESIGN.md / Naive / soybean 令牌；中文 UI 文案与现 Inbox 一致。

## 7. 测试要点

- Triage：入队、三动作、viewer 403 写、跨 WS 404、duplicate 建 Relation
- Templates：CRUD ACL、`templateId` 预填字段、种子幂等
- Snooze：隐藏 / 到期再现 / 已读并存 / 非本人 404
- 回归：E3 Inbox 已读、E12 KEY-N、创建 Issue 无 template 仍通

## 8. Sprint 切分与依赖

| Sprint | 范围 | 依赖 |
|---|---|---|
| S1 | triage_status + API + FE 队列 | E12 tip；Alembic on invites head |
| S2 | issue_templates + 创建/⌘K | S1 合并进同 worktree 或继续 tip |
| S3 | snooze + 打磨 + Epic DoD | S2 |

## 9. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 用户把 Inbox 当 Triage | 文案/侧栏明确「入站队列」vs「通知」 |
| FE 模板与 DB 双源冲突 | API 优先；常量仅 seed/fallback；单测固定 |
| snooze 永久丢消息 | 90d 上限 + unsnooze + include_snoozed |
| duplicate 目标跨 WS | 校验同 workspace |

## 10. 排除

邮件 Inbox、SMTP、Project 模板、自动 ingress、SSO、远程 push、E10 Initiative / E11 Git。

## 11. Phase 1 产出清单

- [x] explore inventory（本文 §2）
- [x] roadmap `docs/superpowers/roadmaps/2026-11-04-opentask-triage-templates-snooze.md`
- [x] 本 design
- [x] S1 stub `docs/superpowers/sprints/2026-11-04-E9-S1-plan.md`
- [ ] **产品实现** → 待后续 Phase（TDD plan + impl）；本 Phase **停止**
