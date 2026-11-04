# E15 设计：租户 IDOR 硬化（直读 UUID 必须验成员）

日期：2026-11-04（Asia/Shanghai）  
基线：`sprint/E14-S1` @ `0f64111` · 分支 `sprint/E15-S1`  
worktree：`/workspace/opentask-worktrees/E11-S4`  
约束：**本地提交，禁止 push / 禁止 PR**；少问多做；齐套后待命，不自开更远 Epic。

## 问题（验收 FAIL）

来源：`/workspace/opentask-smoke/multi-ws/ACCEPTANCE.md`（38P/4F）

| FAIL | 现象 |
|------|------|
| `GET /api/projects/{id}` | 任意已登录用户凭 UUID 可读他租户项目（含 Demo Project） |
| `PUT /api/projects/{id}`（及 DELETE） | 同上，可改他租户描述 |
| `GET /api/issues/{id}` 按 UUID | `get_issue` 仅在 `by_code=true` 时滤 workspace；按 id 可读跨 WS Issue |

对照：**列表** `GET /api/projects` + 外域 `X-Workspace-Id` 已正确 403；**直读路由**只叠了全局 `authenticate`，未校验实体 `workspace_id` 的成员资格。

同类洞（扫面）：Issue 子资源 `comments` / `relations` / `attachments` 多数只按 `issue_id` 读写，无成员校验；`PUT/DELETE /comments/{id}` 同。

## 根因

1. `project/router.py` 的 `get_project` / `update_project` / `delete_project`：加载后直接返回，无 `WorkspaceService.require_member(project.workspace_id, user)`。
2. `issue/router.py` 的 `get_issue`：`workspace_id` 仅在 `by_code` 时传入；按 UUID 路径完全不滤。
3. `update_issue` / `delete_issue` 与子路由：无实体级 membership。

## 决策

| # | 决策 |
|---|------|
| D1 | 新增 `ensure_entity_workspace_access(session, user_id, workspace_id)`：`workspace_id` 非空 → `require_member`（403「无权访问该工作区」）；`None`（遗留孤儿）→ 放行（已要求 authenticate；与列表「成员 ∪ NULL」一致） |
| D2 | **以实体自身 `workspace_id` 为准**，不要求请求头与实体 WS 一致；头仍只服务 list/create 作用域。外域头在 `get_optional_workspace_context` 上继续 403 |
| D3 | Project：`GET/PUT/DELETE /{id}` 加载后 `ensure_*`；本租户成员仍 200 |
| D4 | Issue：`GET`（含 by_code 加载后二次校验，防无头 by_code 漏）、`PUT`/`DELETE` 同；`by_code` 现有 header 精确滤**不回退** |
| D5 | 子资源至少：`/{issue_id}/comments|relations|attachments` 的读写，以及 `comments/{comment_id}` 的改删：先解析所属 Issue，再 `ensure_*` |
| D6 | 测试优先（TDD）：双用户跨 WS 拒绝 + 本租户仍通 + 列表错头仍 403；冒烟关键 IDOR 断言复跑 |
| D7 | 不改 FE；不 push；CLI 7 坏测有带宽再快修，不挡主线 |

## 非目标

- 不重做 RBAC 角色细粒度（owner/member/viewer 写权限另议；本 Epic 只堵跨租户读/写）
- 不强制所有遗留 NULL `workspace_id` 迁移
- 不改公开附件下载 `/api/attachments/{id}/download`（另票；本波先堵带认证的 issue 附件列表/上传）

## 验收条

- 用户 A `GET/PUT` 用户 B 租户 Project / Issue UUID → 403（或 404，统一用 403 成员失败语义）
- 本租户仍通；`GET /api/projects` + 错 `X-Workspace-Id` 仍 403
- pytest 覆盖跨用户/跨 WS；关键 live IDOR 复跑 PASS
