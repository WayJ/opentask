---
epic: E12
status: local-complete
date: 2026-11-04
---

# OpenTask Linear 进阶：成员邀请 · KEY-N 单号 · 去 PGE 内化（厚 · 优先）

产品参考 Linear Invites / Issue identifiers（`TEAM-123`）与「不内化固定研发流程」。在 E8（里程碑 / 健康 / Timeline / Favorites）之上插队交付：Linear 式成员邀请与成员管理 UI、`Workspace.issue_key` + `KEY-N` 工作区作用域单号（迁出 `ISSUE2026-N`）、主导航/默认路径/Agent·CodingWorker 去 PGE 内化（API/表可 deprecated，**不**物理删表）。本 Epic 为整包一个 Roadmap。SSO/SAML 大改、强制 SMTP、Linear Team 硬切、物理删除 Requirement/PGE 表明确排除。

北星：[OpenTask · Linear 对齐完整 PRD](https://cursor.com/canvas/store-adddb90c-33cd-496c-a6c4-08755560f586/656f4217-cbf0-48a3-9edb-168b4a36cbee) §E12（Way 2026-11-04 方向修正）。

基线 tip：`sprint/E8-S3` @ `9fef926`；worktree `/workspace/opentask-worktrees/E12-S1` · 分支 `sprint/E12-S1`。本地不推远程。E12 整包后接 **E9** Triage（不接未完成的其他 Epic）。

## Deliverables

| deliverable | note |
|---|---|
| **KEY-N 单号** | `workspaces.issue_key`（2–6 大写字母数字，平台唯一）+ `issue_counter`；新 Issue `KEY-N`；改 key 只影响新单；存量回填 + 双解析过渡；API/FE/⌘K/URL 一等公民；跨 WS 不可借号读取 |
| **Invites** | 表 `workspace_invites`：email 可选、role、expiry、token；pending 列表；revoke；accept；复制链接为主（无 SMTP 亦可）；有 SMTP 时邮件可选 |
| **注册绑邀请** | 未注册：邀请落地 → 注册（可预填 email/username）→ 自动加入；已注册：accept → 加入；已是成员 → 幂等成功；开放注册 + 默认个人 WS 保留且与受邀加入互不冲突 |
| **成员管理 UI** | 列表、改角色、移除、离开；viewer 只读；仅 **owner** 默认可邀请；保留现有 `POST …/members`（`userId`）并扩展 |
| **去 PGE** | 主导航/默认 home/⌘K 页面动作不再主推需求·PGE；CodingWorker / Agent 文档不再要求每需求走 PGE；`/api/tasks` PGE 入口标 deprecated 或隐藏 UI；**不** DROP 表 |

## Definition of Done

- [x] Epic 下全部 Sprint（S1–S3）已 acceptance 且 state=closed；合并证据本地台账（merged-commit 仍 null / 未推远程）
- [ ] `cd backend && uv run pytest tests/ -v` 全绿（含 KEY-N 分配/双解析/跨租户、invites ACL、accept/register、成员改角色/离开、de-PGE 冒烟）
- [ ] `cd frontend && npm run lint && npm run build` 通过（0 errors）
- [ ] 新建 Issue 展示 `KEY-N`；列表/看板/⌘K/`by_code` 可解析新旧码；改 `issue_key` 不改写存量码
- [ ] Owner 可建/撤邀请并复制链接；受邀者可接受；未注册经邀请注册并加入；已成员幂等
- [ ] 成员页可改角色/移除/离开；viewer 不可写
- [x] 主路径无强制 PGE；CodingWorker 文档已改；PGE API 有 deprecated 标记；表仍在
- [ ] DESIGN.md / Naive UI / soybean 令牌被前端改动遵守；无 SSO 大改 / 强制 SMTP / 物理删 PGE 表
- [ ] 整 Epic 一次回执 Yuri/Way（路径、分支 tip、门禁、acceptance）

## Sprint Breakdown

| sprint | state | note |
|---|---|---|
| S1 | **closed**（local） | KEY-N + dual-parse + FE/CLI + alembic `b8c9d0e1f2a4`；acceptance `2026-11-04-E12-S1-acceptance.md`；未推远程 |
| S2 | local-complete | Invites API + accept/register 落地 + 成员管理 UI（改角色/移除/离开）+ 保留 `add_member(userId)` |
| S3 | local-complete | 去 PGE 导航/默认/deprecated 标记 + CodingWorker/Agent 文案 + 打磨 + Epic local-complete |

推荐顺序理由：单号是列表/⌘K/CLI/外链的展示真相源，先固化（S1）避免邀请/文案仍引用 `ISSUE2026-*`；邀请与成员 UI 依赖稳定工作区设置面（S2）；去 PGE 是横切入口清理，放最后与整包验收同频（S3），避免 S1/S2 测试夹具被导航大改打断。

## Decisions (ADR)

| id | decision | rationale | date | evidence |
|---|---|---|---|---|
| D1 | `workspaces.issue_key` **平台唯一**（2–6 `[A-Z0-9]`）；另存 `issue_counter`（下一序号） | PRD「全局唯一」+ 保留 `issues.issue_code` 全局唯一索引；碰撞规避简单 | 2026-11-04 | PRD §E12；探索 `Issue.issue_code` unique |
| D2 | 改 `issue_key` **只影响新 Issue**；存量 `issue_code` 不变（除非一次性回填脚本已改写） | PRD 明示；避免外链断裂 | 2026-11-04 | PRD |
| D3 | 存量：迁移写回 `KEY-N` + `legacy_issue_code` 保留旧码；`get_issue(by_code)` / ⌘K / CLI **双解析** | 过渡期兼容；Jira wire 可读 legacy | 2026-11-04 | 探索 `jira/keys.py` 绑 ISSUE 年号 |
| D4 | 分配：事务内 `counter = counter + 1` 返回 N；撞唯一索引仍可重试（沿用 create_issue 重试壳） | 优于全表 max+1；并发安全 | 2026-11-04 | `api/tasks/service.py` 重试先例 |
| D5 | `by_code` 查询必须落在 **当前 X-Workspace-Id**（或成员可见 WS）；跨 WS 同形码 404 | PRD 跨租户负例 | 2026-11-04 | `require_workspace_context` |
| D6 | 默认 `issue_key`：创建 WS 时从 slug 取 2–6 大写字母数字；非法则 `OT` + 去重后缀 | 无 UI 时也能建号 | 2026-11-04 | `slugify` 已有 |
| D7 | 邀请表 `workspace_invites`；token 高熵；默认 expiry 7d；状态 pending\|accepted\|revoked\|expired | Linear 手感；无 SMTP 依赖 | 2026-11-04 | 探索零 SMTP |
| D8 | 仅 **owner** 可邀请/撤邀请/改角色/移除；member 可 **离开**；viewer 只读成员列表 | PRD 默认；设置放开 member 邀请 → 后置 | 2026-11-04 | `require_owner` 已有 |
| D9 | 保留 `POST /api/workspaces/{id}/members`（userId）；新增 invites 与 `PATCH …/members/{userId}`、`POST …/leave` | 现有测试夹具大量 `_add_member`；不破 | 2026-11-04 | `test_workspace.py` |
| D10 | User **无 email 列**：invite.email 为自由文本（展示/预填）；匹配已注册用户靠登录态 accept，不靠 email FK | 探索 `UserModel` 仅 username | 2026-11-04 | `models/user/model.py` |
| D11 | 受邀注册：`POST /api/auth/register` 增可选 `inviteToken`；仍建默认个人 WS，并加入邀请 WS | PRD「互不冲突」 | 2026-11-04 | `auth.register` |
| D12 | 去 PGE：隐藏/降权 `workflow_requirements` 菜单与 CreatePGETaskModal 主入口；`VITE_ROUTE_HOME` 建议 `issue_list`（或保持 home 但不链 PGE）；CodingWorker.md 改写；API docstring/`Deprecated` 响应头；**不** alembic drop | Way：不强制物理删表 | 2026-11-04 | 探索 CodingWorker/PGE 资产 |
| D13 | 整 Epic 一次回执；Sprint 中间不逐个找 Yuri/Way | E5–E8 节奏 | 2026-11-04 | Yuri |
| D14 | 排除：SSO、强制 SMTP、Team 模型、物理删 PGE/Requirement 表、远程 push、E9+ | 指派 / PRD | 2026-11-04 | 指派 |

### 方案比选（锁定 D1 / D3 / D7）

| 主题 | A（选定） | B（拒绝） | C（拒绝） |
|---|---|---|---|
| issue_key 唯一域 | 平台唯一 → KEY-N 全局唯一 | 仅 WS 内唯一 + 改掉 issue_code 全局唯一索引 | 继续 ISSUE{年}-N |
| 存量迁移 | 回填 KEY-N + legacy 双读 | 只双读不改写展示 | 立即删旧码无过渡 |
| 邀请投递 | 复制链接为主；SMTP 可选钩子 | 强制 SMTP | 仅 userId 直加 |

## Exclusions

- SSO / SAML / OIDC 大改
- 强制配置 SMTP；邮件 Inbox
- Linear Team 模型硬切（Workspace 前缀即可）
- 物理 DROP `requirements` / PGE task 相关表或全量删数据
- 改写 Jira key 编解码为新 KEY-N 投影（S1 保 legacy 双读；深度对齐可后置）
- 远程 push / PR
- E9 Triage / Templates / snooze

## Asset Disposition

| asset | disposition | note | date |
|---|---|---|---|
| `workspaces.issue_key` / `issue_counter` | **add** | S1 | 2026-11-04 |
| `issues.legacy_issue_code` | **add** | S1；可空 | 2026-11-04 |
| `_generate_issue_code` | **replace** | S1 → KEY-N + counter | 2026-11-04 |
| `workspace_invites` | **create** | S2 | 2026-11-04 |
| `POST …/members` | **keep** | S2 并存 | 2026-11-04 |
| `PATCH …/members/{userId}` · `POST …/leave` | **add** | S2 | 2026-11-04 |
| FE members / settings / invite landing | **create** | S2 | 2026-11-04 |
| `workflow_requirements` 主入口 · CreatePGETaskModal | **hide/deprecate** | S3 | 2026-11-04 |
| `CodingWorker.md` / PGE 用户指南引用 | **rewrite** | S3 | 2026-11-04 |
| PGE API `/api/tasks` | **deprecate** | S3；不删 | 2026-11-04 |
| Alembic head | **extend** | S1 `down_revision = a7b8c9d0e1f3`（favorites） | 2026-11-04 |

## Progress

| date | note |
|---|---|
| 2026-11-04 | Phase 1：explore + roadmap + design + S1 stub；worktree `E12-S1` @ `9fef926`；**无**产品实现、**无**推远程 |
| 2026-11-04 | E12-S1 local-complete：plan+TDD+impl+acceptance；pytest 708；未开 S2；未推远程 |
| 2026-11-04 | E12-S2 local-complete：invites+members UI；pytest 721；未开 S3；未推远程 |
| 2026-11-04 | E12-S3 + Epic local-complete：de-PGE；CodingWorker Issue-first；未推远程；未开 E9 |
