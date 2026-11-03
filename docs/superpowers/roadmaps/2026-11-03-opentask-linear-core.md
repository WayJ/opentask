---
epic: E3
status: active
date: 2026-11-03
---

# OpenTask Linear 核心：开放注册 · Workspace · 双视图 · Inbox

产品参考 Linear；在现有 Issue / Project / Requirement 能力之上补齐「自助注册 + 工作区租户边界 + Issue 看板/列表双视图 + Inbox 通知流」。本 Epic 为整包一个 Roadmap，不拆零散临时任务。⌘K 明确排除。

## Deliverables

| deliverable | note |
|---|---|
| 开放注册（自助 signup + 登录） | `POST /api/auth/register`；用户名/邮箱 + 密码；复用登录 RSA-OAEP 解密；注册后可立即登录或同事务签发 token |
| Workspace 租户根（创建 / 加入 / 切换） | Workspace + WorkspaceMember；角色 owner / member / viewer；`X-Workspace-Id` 上下文；注册时可创建个人默认工作区 |
| 工作区内管理 Project / Issue | Project、Issue 增加 `workspace_id` FK；列表/创建按当前工作区隔离；存量数据回填到系统默认工作区 |
| Issue 看板 + 列表双视图 | 复用现有 `status` / `assignee_id` / `position`；同一数据源两套呈现（S2） |
| Inbox 通知流 | 指派 / 评论 / @；通知记录模型（非邮件）（S3） |

## Definition of Done

- [ ] Epic 下全部 Sprint（S1–S3）已 acceptance 且 state=closed，合并证据写入各 sprint 台账
- [ ] `cd backend && uv run pytest tests/ -v` 全绿（含新增 register / workspace 隔离用例）
- [ ] `cd frontend && npm run lint && npm run build` 通过（0 errors）
- [ ] 开放注册：未登录可自助建号；弱密码 / 重名有明确错误；密码路径复用 login crypto
- [ ] Workspace：用户可创建、列出「我的」、切换；非成员无法读他区 Project/Issue
- [ ] Project/Issue 列表与创建强制 workspace 作用域；存量行已回填默认工作区
- [ ] 看板 + 列表双视图可用且与 status/assignee/position 一致（S2）
- [ ] Inbox 对指派/评论/@ 产生可读通知流（S3）
- [ ] DESIGN.md / Naive UI / soybean 令牌被前端改动遵守；无 ⌘K 相关交付

## Sprint Breakdown

| sprint | state | note |
|---|---|---|
| S1 | closed | **开放注册 + Workspace（创建/加入/切换）+ Project/Issue 挂 workspace_id 与隔离**。必须最先做：租户边界影响数据模型与后续视图/通知作用域。evidence: `docs/superpowers/sprints/2026-11-03-E3-S1-plan.md` |
| S2 | closed | Issue 看板 + 列表双视图；复用 status/assignee/position。evidence: `docs/superpowers/sprints/2026-11-04-E3-S2-plan.md` / `docs/superpowers/acceptances/2026-11-04-E3-S2-acceptance.md` |
| S3 | pending | Inbox 通知流（assign / comment / @）；通知为库内记录，不做邮件投递 |
| S4 | optional | 仅当 S1–S3 合并后仍需跨模块抛光/回归时启用；优先控制在 3 个 sprint |

推荐顺序理由：无 Workspace 则看板与 Inbox 的「可见范围」无法定义；开放注册与默认工作区同事务可降低空租户体验摩擦。

## Decisions (ADR)

| id | decision | rationale | date | evidence |
|---|---|---|---|---|
| D1 | 开放注册采用用户名（+可选显示名）+ 密码，不引入手机短信验证码 | 现有短信/验证码链路未接线；register.vue 手机验证码仅为 soybean 模板桩 | 2026-11-03 | 本文档；`frontend/.../register.vue` 桩 |
| D2 | 注册密码与登录一致：前端 RSA-OAEP 加密，后端 `_plain_password` / `decrypt_login_payload` 解密后 bcrypt 入库 | 与现网 login crypto 同路径，避免双套口令传输 | 2026-11-03 | `api/auth/router.py`；`utils/login_crypto.py` |
| D3 | Workspace 为租户根；成员角色 owner / member / viewer | Linear 式多租户最小集；owner 可管成员与工作区元数据 | 2026-11-03 | 本文档 |
| D4 | 工作区上下文用请求头 `X-Workspace-Id`（非 query） | 列表/创建多端点共用，避免每个 API 重复 query；未带或无权限 → 403/400 | 2026-11-03 | S1 计划 ADR |
| D5 | Project、Issue 增加可空→回填后非空的 `workspace_id`；迁移创建 `Default Workspace` 系统区并 backfill 存量行 | 保证旧测试与旧数据不因 NOT NULL 立刻炸裂；回填后应用层按工作区过滤 | 2026-11-03 | alembic 迁移 |
| D6 | Project 名称唯一性改为 `(workspace_id, name)` | 跨工作区允许同名；租户内仍唯一 | 2026-11-03 | 迁移 + 模型 |
| D7 | 注册成功默认：创建个人默认 Workspace（slug 派生）并写 owner 成员；同事务签发登录 token 对 | 注册后即可进入产品，无需管理员二次开户 | 2026-11-03 | AuthService / register |
| D8 | 双视图（S2）不改 status 枚举，只加呈现层 | 现有看板字段已具备 | 2026-11-03 | Issue 模型 |
| D9 | Inbox（S3）为通知记录表 + API，不做邮件/IM 外发 | 先闭环产品内通知；外发另开 Epic | 2026-11-03 | 本文档 |
| D10 | 排除 ⌘K、mission-center 前端复活、计费、SSO 大改、Orca/Jira 变更 | Way 拍板范围；E2 已覆盖 Orca | 2026-11-03 | 指派纪要 |

## Exclusions

- ⌘K / 命令面板
- mission-center 前端重新上线（后端可保留）
- 计费 / 席位 / 订阅
- SSO 协议重设计（现有钉钉 / 上游 SSO 路径保持；开放注册走本地账号）
- Orca / Jira 集成改动（属 E2）
- 手机短信验证码注册
- 邮件投递 Inbox
- 跨工作区全局 Issue 搜索（可后续）

## Asset Disposition

| asset | disposition | note | date |
|---|---|---|---|
| `frontend/.../register.vue` 手机验证码桩 | rewrite | 改为用户名+密码+确认密码，接真实 API | 2026-11-03 |
| `app.py` 注释掉的 `workspace_router` | revive | 落地真实 workspace API 后挂载 | 2026-11-03 |
| Conversation.`workspace_id` 文本字段 | leave | S1 不改会话模型语义；租户边界先落在 Project/Issue | 2026-11-03 |
| 管理端 `POST /api/users` | reuse | 管理员建号保留；开放注册是互补路径 | 2026-11-03 |

## Open Questions

| id | question | status | resolution |
|---|---|---|---|
| Q1 | 注册是否强制 email 唯一列？ | deferred | S1 先用 username 唯一；email 若加列为可选，不阻塞 |
| Q2 | viewer 是否只读 Issue？ | deferred | S1 成员读写策略：owner 管理成员；member 可读写业务；viewer 只读——API 层最小校验，细粒度 RBAC 可后补 |
| Q3 | 默认工作区 slug 冲突时如何消解？ | closed | username 归一化 + 短随机后缀 |

## Cross-cutting

| concern | owning epic | note |
|---|---|---|
| 租户隔离正确性 | E3 | 每个涉及 Project/Issue 的 sprint 须带跨工作区负例 |
| 登录加密一致性 | E3 / 既有 auth | register 不得引入明文专用旁路（测试明文兼容除外） |
| DESIGN.md 视觉令牌 | E3 | 前端改动走 Naive / soybean / design-system.css |
| 门禁 | E3 | AGENTS.md gates；PG 容器 `opentask-pg-test` |

## Overall Acceptance Scenarios

| id | scenario | how to verify | expected |
|---|---|---|---|
| R1 | 陌生人可开放注册并登录 | POST register → 持 token 调 getUserInfo | 200 + 用户信息 |
| R2 | 用户拥有默认工作区且可再创建/切换 | register 后 list workspaces；create；带 X-Workspace-Id 列项目 | 隔离正确 |
| R3 | 跨工作区不可读 | 用户 A 的 Issue 在用户 B 的工作区头下不可见 | 403 或空集且无泄漏 |
| R4 | 看板/列表同数据（S2） | 改 status/position 后两视图一致 | 一致 |
| R5 | Inbox 收到指派/评论/@（S3） | 触发事件后 inbox list | 有对应通知记录 |

```supervibe-acceptance-plan
{
  "schema": 1,
  "scope": "epic",
  "scenarios": [
    {
      "id": "R1",
      "goal": "开放注册并可登录",
      "steps": ["POST /api/auth/register", "GET /api/auth/getUserInfo with token"],
      "expected": "200 且返回用户信息",
      "required": true,
      "modality": "api",
      "environment": "real"
    },
    {
      "id": "R2",
      "goal": "默认工作区与创建/切换",
      "steps": ["register", "GET /api/workspaces", "POST /api/workspaces", "带 X-Workspace-Id 列 Project"],
      "expected": "列表含默认区；新区可切换；数据按区隔离",
      "required": true,
      "modality": "api",
      "environment": "real"
    },
    {
      "id": "R3",
      "goal": "跨工作区隔离",
      "steps": ["两用户两工作区", "用错误 X-Workspace-Id 读 Issue/Project"],
      "expected": "403 或不可见，无跨租户泄漏",
      "required": true,
      "modality": "api",
      "environment": "real"
    },
    {
      "id": "R4",
      "goal": "看板与列表双视图一致（S2）",
      "steps": ["同一 workspace 内切换 board/list", "变更 status/position"],
      "expected": "两视图数据一致",
      "required": true,
      "modality": "browser",
      "environment": "real"
    },
    {
      "id": "R5",
      "goal": "Inbox 通知（S3）",
      "steps": ["指派/评论/@", "GET inbox"],
      "expected": "出现对应通知记录",
      "required": true,
      "modality": "api",
      "environment": "real"
    }
  ]
}
```


## 进度注记

- 2026-11-04（UTC+8）：E3-S1 closed；acceptance `docs/superpowers/acceptances/2026-11-03-E3-S1-acceptance.md`；分支 `sprint/E3-S1` 未推远程。下一步 S2（看板+列表）。

- 2026-11-04（UTC+8）：E3-S2 started（分支 `sprint/E3-S2`，基于 S1 tip `9659718`）；实现看板+列表双视图。
- 2026-11-04（UTC+8）：E3-S2 closed；acceptance `docs/superpowers/acceptances/2026-11-04-E3-S2-acceptance.md`；分支 `sprint/E3-S2` 未推远程。下一步 S3（Inbox）。
