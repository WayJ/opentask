# E12 设计：成员邀请 · KEY-N 单号 · 去 PGE 内化

日期：2026-11-04  
Epic：E12  
状态：designed（Phase 1；**无**产品实现）  
基线：`sprint/E8-S3` @ `9fef926`；worktree `/workspace/opentask-worktrees/E12-S1`（分支 `sprint/E12-S1`）  
北星：OpenTask Linear PRD §E12（Way 2026-11-04）  
Alembic head：`a7b8c9d0e1f3`（`favorites`）

## 1. 目标

对齐 Linear 的协作入场与 Issue 标识，并退役产品主轴上的 PGE 内化：

1. **S1** `Workspace.issue_key` + 单调 `issue_counter` → 新 Issue `KEY-N`；存量回填 + `legacy_issue_code` 双解析；FE 列表/看板/详情/⌘K/`by_code` URL；工作区设置可改 key（仅新单）
2. **S2** `workspace_invites` CRUD/revoke/accept；注册绑 `inviteToken`；成员管理 UI（列表/改角色/移除/离开）；保留 `add_member(userId)`；viewer 只读；仅 owner 邀请
3. **S3** 主导航/默认 home/⌘K/Agent·CodingWorker 去 PGE 强制；PGE API deprecated 标记；打磨 + Epic local-complete

不做：SSO 大改、强制 SMTP、Team 硬切、物理删 PGE/Requirement 表、远程推送、E9+。

## 2. 探索事实（Phase 1 inventory）

### 2.1 Issue 单号

| 资产 | 路径 | 现状 |
|---|---|---|
| 生成 | `services/issue_service.py::_generate_issue_code` | **全局** `ISSUE{year}-{max+1}`；应用侧解析防字典序；**无** workspace 作用域 |
| 并发 | `api/tasks/service.py::create_issue` | IntegrityError 撞 `issues.issue_code` 唯一索引时重试 |
| 列 | `models/issue/model.py` | `issue_code` String(50) **unique=True**；`workspace_id` 可空 FK |
| 查询 | `get_issue(..., by_code=True)` | **仅** `Issue.issue_code ==`；**未**按 workspace 过滤 |
| Jira | `api/jira/keys.py` | `ISSUE2026-N` ↔ `OPENTASK-{年*1e9+序}`；绑死年号形状 |
| CLI | `opentask-cli/.../helpers.py::validate_issue_code` | **仅** `^ISSUE\d+-\d+` |
| FE 识别 | `utils/command-palette-entities.ts` | `looksLikeIssueCode` = `/^[A-Za-z][A-Za-z0-9]*-\d+$/` → **已**匹配 `WAY-42` 与 `ISSUE2026-32` |
| FE 跳转 | palette / detail | 多用 `id` query；`fetchIssue` 支持 `by_code` |
| 集合创建 | `issue_collection_service` | 亦调 `_generate_issue_code` |

结论：S1 必须改分配器 + 收紧 by_code 租户过滤 + 回填；CLI/Jira 双读；FE 正则基本可留。

### 2.2 Workspace / 成员

| 资产 | 现状 |
|---|---|
| `Workspace` | `name/slug/description` + Cycles 四列；**无** `issue_key` / counter |
| `WorkspaceMember` | `owner\|member\|viewer`；`uq(workspace_id,user_id)` |
| API | `GET/POST /api/workspaces`；`PATCH`（owner）；`GET/POST/DELETE …/members` |
| `add_member` | body `{ userId, role }`；**仅 owner**；已存在 → **409**（非幂等） |
| `remove_member` | owner；禁删最后 owner；**无** self-leave；**无** PATCH role |
| FE | `service/api/workspace.ts` **无** members 客户端；**无**成员管理页（仅 cycles/labels 设置页） |
| 测试 | 多处 `_add_member` 助手依赖现 API |

### 2.3 注册 / 用户标识

| 资产 | 现状 |
|---|---|
| `POST /api/auth/register` | `userName` + `password` + 可选 `name` → 用户 + **默认个人 Workspace** + token |
| `UserModel` | `username` 唯一；**无 email 列** |
| FE register | 三字段；成功后写 `workspaceId` 并 login |
| SMTP | 全仓 **零** `smtp`/`send_email` 实现 |

结论：邀请 email 为可选自由文本；accept 靠 token + 登录态；注册扩展 `inviteToken`。

### 2.4 PGE / 需求主路径

| 资产 | 现状 |
|---|---|
| 路由 | `/workflow/requirements` · `/workflow/requirement-detail`（soybean elegant） |
| UI | `CreatePGETaskModal.vue`；需求详情强绑定 PGE |
| API | `api/task/routes.py` `POST /api/tasks` 创建 PGE 三子任务；preview prompt |
| 服务 | `services/task/pge_service.py` + `prompt_generator.py` |
| 文档 | 根目录 `CodingWorker.md` **强制 PGE 流程**；`docs/PGE_TASK_USER_GUIDE.md` 等 |
| 默认 home | `VITE_ROUTE_HOME=home`（非 requirements）；但 Agent/文档仍推 PGE |
| 权限菜单 seed | `permission_defs.py` **未**登记 workflow_requirements（业务路由默认放行） |
| 事件溯源 / CLI / Agent harness | 独立存在；应 **保留** 并与 PGE 解绑 |

### 2.5 Alembic

当前 head：`a7b8c9d0e1f3`。E12-S1 新 revision：`down_revision = a7b8c9d0e1f3`。

## 3. 架构总览

```
Workspace
  + issue_key (UQ) + issue_counter
  └── Issue[]  issue_code=KEY-N · legacy_issue_code?
  └── WorkspaceMember[]
  └── WorkspaceInvite[]     [S2]

Auth
  register(+inviteToken) → personal WS + join invite WS   [S2]
  GET/POST accept invite by token                         [S2]

Allocation [S1]
  next_code(ws) = f"{ws.issue_key}-{inc(ws.issue_counter)}"
  by_code: (code|legacy) AND workspace_id == ctx

FE
  settings: issue_key 编辑（owner）                        [S1]
  list/board/detail/⌘K: 展示 KEY-N；双解析跳转            [S1]
  members + invite landing + copy link                    [S2]
  hide requirements/PGE 主入口；home → issue list 可选     [S3]

Deprecation [S3]
  PGE API: Deprecated header / OpenAPI description
  CodingWorker.md: Issue/KEY-N 驱动，无强制 PGE
  表与历史数据: KEEP
```

## 4. Schema 草图

### 4.1 `workspaces` 扩展（S1）

```text
workspaces
  …existing…
  issue_key       String(6)  NOT NULL   # 2–6 [A-Z0-9]；创建时写入
  issue_counter   Integer    NOT NULL DEFAULT 0   # 已分配最大 N；下一单 = counter+1
  UNIQUE (issue_key)  name=uq_workspaces_issue_key
```

校验：`^[A-Z0-9]{2,6}$`（入库前 upper）。创建默认：从 `slug` 抽大写字母数字，截断/填充至 2–6；冲突则 `OT`/`OT2`/…。

`PATCH /api/workspaces/{id}` 增 `issueKey`（owner）；**不**重写存量 Issue。

### 4.2 `issues` 扩展（S1）

```text
issues
  …existing issue_code UNIQUE…
  legacy_issue_code  String(50) NULL  INDEX   # 回填前旧码；双解析用
```

回填算法（data migration，同 revision 或 follow-up）：

1. 每个 workspace 若无 `issue_key` → 按 D6 生成  
2. 按 `created_at, id` 排序该 WS 内未删 Issue  
3. `legacy_issue_code = issue_code`（若已是目标 KEY 形且前缀匹配则可跳过）  
4. `issue_code = f"{issue_key}-{i}"`；`issue_counter = max i`  
5. 无 `workspace_id` 的孤儿 Issue：挂到创建者默认 WS 或跳过并记日志（实现计划写清；测试覆盖挂 WS 路径）

### 4.3 `workspace_invites`（S2）

```text
workspace_invites
  id              String(36) PK
  workspace_id    String(36) FK workspaces.id ON DELETE CASCADE NOT NULL
  email           String(255) NULL          # 可选；非 FK
  role            String(20) NOT NULL DEFAULT 'member'  # member|viewer（不可邀 owner）
  token_hash      String(64) NOT NULL UNIQUE  # sha256(token)；明文只在创建响应/链接出现一次
  expires_at      DateTime NOT NULL
  status          String(20) NOT NULL DEFAULT 'pending'  # pending|accepted|revoked|expired
  invited_by      String(36) NOT NULL
  accepted_by     String(36) NULL
  accepted_at     DateTime NULL
  created_at      DateTime NOT NULL
  INDEX (workspace_id, status)
```

### 4.4 成员 API 扩展（S2）

```text
PATCH  /api/workspaces/{id}/members/{userId}   { role }     # owner；禁降最后 owner
POST   /api/workspaces/{id}/leave              {}           # 非最后 owner 可离开
POST   /api/workspaces/{id}/invites            { email?, role, expiresInDays? }
GET    /api/workspaces/{id}/invites            # pending+近期
DELETE /api/workspaces/{id}/invites/{inviteId} # revoke
GET    /api/invites/{token}                    # 落地预览（可匿名）：ws name/role/expiry
POST   /api/invites/{token}/accept             # 需登录；幂等
```

`POST /api/auth/register` body 增可选 `inviteToken`。

`add_member`：保持；可选改为已存在时幂等返回 200（**默认保持 409** 以免 silently 改测；S2 文档注明邀请 accept 路径幂等）。

## 5. 行为与权限

| 动作 | owner | member | viewer | 匿名 |
|---|---|---|---|---|
| 改 issue_key | ✓ | ✗ | ✗ | ✗ |
| 建/撤邀请 | ✓ | ✗ | ✗ | ✗ |
| 预览邀请 | — | — | — | ✓（token） |
| 接受邀请 | ✓ | ✓ | ✓ | ✗（须登录/注册） |
| 改他人角色 / 移除 | ✓ | ✗ | ✗ | ✗ |
| 离开 | ✓* | ✓ | ✓ | ✗ |
| 直加 userId | ✓ | ✗ | ✗ | ✗ |
| 列表成员 | ✓ | ✓ | ✓ | ✗ |

\*离开：若为唯一 owner → 400，须先转让。

## 6. FE 要点

### S1

- Workspace 设置（新建页或 cycles 旁）：`issueKey` 输入 + 预览 `KEY-1`
- Issue 列/卡片/详情头：继续绑 `issue_code`（值已是 KEY-N）
- ⌘K：`looksLikeIssueCode` 已够；`fetchByCode` 走当前 WS
- 可选：`/issue/detail?code=WAY-42` 与 `?id=` 并存（若改动面小）；否则保持 id，code 仅 API

### S2

- `/workspace/members`（或 settings tab）：成员表 + 邀请表 +「复制链接」
- `/invite/:token` 落地：未登录 → 注册/登录带回跳；已登录 → Accept
- register 读 query `invite`
- viewer：隐藏写按钮

### S3

- 侧栏/⌘K 页面动作：Requirements/PGE 降为「Legacy」或移除默认
- `CreatePGETaskModal` 入口隐藏或标 Deprecated
- 默认登录落点：优先 `/issue/list`（改 env 或 routeHome）
- 空状态文案去「开始 PGE」

## 7. 去 PGE（S3）细则

| 层 | 动作 |
|---|---|
| Nav / 路由 meta | 菜单标题改「需求（遗留）」或从默认菜单剔除；路由保留深链以免书签 404 |
| Agent | `AgentPromptModal` / harness 示例改 Issue + KEY-N；不调 `create_pge_task` |
| CodingWorker.md | 重写为 Issue 驱动循环；删除「必须 PGE」条款；可链到可选遗留指南 |
| API | OpenAPI description + 可选 `Deprecation` / `Sunset` 头；测试仍可调用以保兼容 |
| DB | **无** drop；事件溯源表保留 |

## 8. 测试矩阵（Epic 级）

| 域 | 必测 |
|---|---|
| KEY-N | 创建递增；改 key 后新单用新前缀、旧单不变；并发不撞号；跨 WS 同 counter 因 key 不同；by_code 跨 WS 404 |
| 双解析 | legacy 与新码均可 `by_code`；⌘K 单测保持 |
| Invites | owner 建；member 403；过期/撤销不可 accept；accept 幂等；token 猜测失败 |
| Register+invite | 新用户进邀请 WS + 仍有个人 WS |
| Members | PATCH role；leave；禁删最后 owner；viewer 只读 API |
| De-PGE | 冒烟：主菜单快照或文档断言；PGE POST 仍 2xx 但带 deprecated（若实现头） |

## 9. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 回填打乱外链 / Jira key | 保留 `legacy_issue_code`；Jira 编解码过渡读 legacy；S1 不强制改 jira 投影公式 |
| 无 email 导致「按邮找回用户」不可用 | 产品以链接+登录态为准；email 仅文案 |
| 菜单权限模型不含 workflow_* | FE 静态隐藏即可；不必改 seed |
| CLI 仍只认 ISSUE* | S1/S3 扩 `validate_issue_code` 与 show 路径正则 |

## 10. Sprint 切片与文件触点（预告）

| Sprint | 主要路径 |
|---|---|
| S1 | alembic；`models/workspace`；`issue_service._generate_issue_code`；`get_issue`；workspace schema/router；FE workspace settings + palette 回归；CLI helpers；tests `test_issue_key*.py` |
| S2 | `models/workspace_invite`；invite service/router；auth register；FE members + invite landing；tests `test_invites*.py` |
| S3 | CodingWorker.md；FE nav/modal；task routes deprecation；acceptance + roadmap local-complete |

## 11. Self-review

- 无 TBD 阻塞实现；开放点已按 PRD 默认锁定（D1–D14）  
- 与 roadmap 切片一致：S1 单号 → S2 邀请/成员 → S3 去 PGE  
- 不扩 SSO/SMTP/删表  
- 与 E8 tip `a7b8c9d0e1f3` 迁移链衔接明确  

## 12. 非目标（再申明）

强制 SMTP、SSO 大改、Linear Team、物理删 PGE 表、远程 push、E9 Triage。
