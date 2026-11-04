---
epic: E9
status: active
date: 2026-11-04
---

# OpenTask Linear 进阶：Triage · Templates · Inbox snooze（厚）

产品参考 Linear [Triage](https://linear.app/docs/triage)、Issue templates、Inbox snooze。在 **E12 local-complete**（邀请 / KEY-N / 去 PGE）之上交付：工作区入站 **Triage 队列**（accept / decline / duplicate）、**Issue 模板**（字段预填 + ⌘K/创建流可选）、**Inbox 通知 snooze**（延后再现）。本 Epic 为整包一个 Roadmap。邮件 Inbox、外发 IM、计费、SSO 大改、Initiative（E10）、Git/PR（E11）明确排除。

北星：[OpenTask · Linear 对齐完整 PRD](https://cursor.com/canvas/store-adddb90c-33cd-496c-a6c4-08755560f586/656f4217-cbf0-48a3-9edb-168b4a36cbee) §E9。

基线 tip：`sprint/E12-S3` @ `77990b4`；worktree `/workspace/opentask-worktrees/E9-S1` · 分支 `sprint/E9-S1`。本地不推远程。E9 整包后接 **E10**（不插队未完成 Epic）。

## Deliverables

| deliverable | note |
|---|---|
| **Triage 队列** | 工作区入站队列（与个人 Inbox 通知分离）；Issue 可进入 `needs_triage`；member+ 可 **accept**（进常规 backlog/`open`）、**decline**（`rejected`）、**duplicate**（建/挂 `duplicates` Relation 并离开 triage）；列表/侧栏入口；跨 WS 隔离 |
| **Issue 模板** | 工作区级模板 CRUD（title/description/type/priority/labels 预填等）；创建 Issue / ⌘K「从模板创建」可选；内置种子（Bug/Feature…）可从现有 FE 常量导入；viewer 只读 |
| **Inbox snooze** | 通知 `snoozed_until`；snooze 后默认 Inbox 列表隐藏；到期自动再现（懒加载即可，不强制独立 worker）；保留已读/未读 |
| **打磨** | 空状态文案；权限（viewer 只读 triage/模板写）；DESIGN.md / Naive UI |

## Definition of Done

- [x] Epic 下全部 Sprint（S1–S3）已 acceptance 且 state=closed；merged-commit 仍 null / 未推远程
- [x] `cd backend && uv run pytest tests/ -v` 全绿（含 triage ACL/跨租户、templates CRUD、snooze 过滤与到期再现）— **751 passed**；3 预存 protocol_rules 失败另记
- [x] FE eslint touched 0 errors；`pnpm run build` 通过
- [x] Triage：accept / decline / duplicate 行为符合设计；非成员 403；跨 WS 404
- [x] 模板：可创建并应用到新建 Issue；⌘K 或创建面板可选
- [x] Inbox：snooze 后列表消失；到期后重现；已读逻辑不被 snooze 破坏
- [x] 无邮件 Inbox / 强制 SMTP；不删通知历史
- [x] 整 Epic 一次回执 Yuri/Way（tip 见 S3 acceptance）

## Sprint Breakdown

| sprint | state | note |
|---|---|---|
| S1 | **closed**（local） | Triage；acceptance `2026-11-04-E9-S1-acceptance.md`；未推远程 |
| S2 | closed | Issue 模板表/API + 创建流/⌘K 接线；种子自 FE `ISSUE_TEMPLATES` |
| S3 | **closed**（local） | Inbox snooze + 打磨 + Epic local-complete |

推荐顺序理由：Triage 是 E9 产品标题能力且无存量 DB 可挂，先立队列与状态机（S1）；模板已有 FE 常量但无租户持久化，第二波接到创建/⌘K（S2）；snooze 改动面最小（notifications 加列 + 列表过滤），放最后与整包验收同频（S3），避免 S1/S2 夹具被 Inbox 行为大改打断。

## Decisions (ADR)

| id | decision | rationale | date | evidence |
|---|---|---|---|---|
| D1 | Triage **不是**个人 Inbox；是工作区「入站 Issue 队列」 | PRD「Inbox 旁的入站队列」；Linear Triage ≠ notifications | 2026-11-04 | PRD §E9；探索 Inbox=notifications |
| D2 | Issue 增 `triage_status`：`null`（非 triage）\|`pending`\|（终态靠 status，离开队列清字段） | 避免与 `issue_status` 枚举硬塞 triage；accept 后 `status=open` 并 `triage_status=null` | 2026-11-04 | `Issue.status` 已固定 ENUM |
| D3 | **Accept** → `triage_status=null` + 保持/设 `open`；**Decline** → `rejected` + 清 triage；**Duplicate** → `RelationType` duplicates + decline 语义 | 对齐 Linear 三动作 | 2026-11-04 | PRD AC；既有 `IssueRelation` |
| D4 | 谁可 triage：默认 **member + owner**；viewer 只读队列 | 与 Workspace 角色一致；不另造权限码 | 2026-11-04 | E3/E12 角色模型 |
| D5 | 入队来源：API `POST …/triage` 或创建 Issue 时 `triage=true`；集成/外源后置 | 现无邮件/Slack 入站；先人工/API 入队 | 2026-11-04 | 探索无 integration ingress |
| D6 | 模板存表 `issue_templates`（workspace 作用域）；FE 硬编码常量作 **种子/fallback** | Linear 可编辑模板；现 FE 仅静态 | 2026-11-04 | `issueTemplates.ts` 已有 5 套 |
| D7 | 模板字段：至少 title 前缀/pattern、description body、type、priority；labels/project 可选 JSON | 够用；不做 Project 模板（PRD「可选」→ E9 不做） | 2026-11-04 | PRD「Issue 模板」为主 |
| D8 | snooze：`notifications.snoozed_until`；`list` 默认排除 `snoozed_until > now()`；到期自然可见 | 懒唤醒，免定时任务；E3 已读保留 | 2026-11-04 | `Notification` 仅 `read_at` |
| D9 | snooze 预设：1h / 3h / 明天 / 下周一（FE）；API 收任意 ISO datetime（上限 90d） | Linear 手感；防永久消失 | 2026-11-04 | Linear snooze UX |
| D10 | Alembic `down_revision = c9d0e1f2a3b5`（workspace_invites） | E12-S2 tip 迁移链 | 2026-11-04 | versions/ |
| D11 | 整 Epic 一次回执；Sprint 中间不逐个找 Yuri/Way | 厚 Epic 节奏 | 2026-11-04 | Yuri |
| D12 | 排除：邮件 Inbox、SMTP 强依赖、Project 模板、E10 Initiative、远程 push | 指派 / PRD | 2026-11-04 | 指派 |

### 方案比选（锁定 D2 / D6 / D8）

| 主题 | A（选定） | B（拒绝） | C（拒绝） |
|---|---|---|---|
| Triage 存储 | Issue.`triage_status` 列 | 独立 `triage_items` 表镜像 Issue | 复用 notifications 当 triage |
| 模板 | DB `issue_templates` + 种子 | 仅 FE 常量 | 每用户私有模板无 WS 共享 |
| snooze | 列 `snoozed_until` + 懒过滤 | 删通知再重建 | 独立 snooze 队列表 |

## Exclusions

- 邮件 / IM 外发 Inbox；强制 SMTP
- 公共表单 / 邮件→自动入 Triage（可后置集成 Epic）
- Project / Initiative 模板（E10）
- 计费、SSO 大改、mission-center 复活
- 远程 push / PR
- E10 / E11 范围

## Asset Disposition

| asset | disposition | note | date |
|---|---|---|---|
| `issues.triage_status` | **add** | S1 | 2026-11-04 |
| Triage API `/api/triage` 或 `/api/issues/triage` | **create** | S1 | 2026-11-04 |
| FE `/triage` 或 Inbox 旁入口 | **create** | S1 | 2026-11-04 |
| `issue_templates` 表 | **create** | S2 | 2026-11-04 |
| FE `ISSUE_TEMPLATES` 常量 | **keep + seed** | S2；不删 fallback | 2026-11-04 |
| ⌘K / 创建面板选模板 | **wire** | S2 | 2026-11-04 |
| `notifications.snoozed_until` | **add** | S3 | 2026-11-04 |
| Inbox FE snooze 动作 | **add** | S3 | 2026-11-04 |
| Alembic head | **extend** | S1 起自 `c9d0e1f2a3b5` | 2026-11-04 |

## Progress

| date | note |
|---|---|
| 2026-11-04 | Phase 1：explore + roadmap + design + S1 stub；worktree `E9-S1` @ `77990b4`；**无**产品实现、**无**推远程 |
| 2026-11-04 | E9-S1 local-complete：Triage API+FE；pytest 736；未开 S2；未推远程 |
| 2026-11-04 | E9-S2 local-complete：issue_templates CRUD+seed+FE；pytest 744（+8 templates）；未开 S3；未推远程 |
| 2026-11-04 | **E9 Epic local-complete**：S3 snooze + DoD；pytest 751；tip `75e3dedb3b2a31137c4530c8875460624e114b6c`；未开 E10；未推远程 |
