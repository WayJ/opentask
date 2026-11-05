# E23 设计：Workspace 实时（Issue OS 手感）

日期：2026-11-04（Asia/Shanghai）  
Epic：E23  
基线：`sprint/E22-S1` @ `82795db`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E23-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E24**。

## 1. 目标

现有 `services/websocket` / `/ws/hub*` 偏 Agent/task hub；**不拆坏**。本期新增 **Workspace 业务事件通道**，让 Inbox / Issue 列表·看板·详情具备轻量实时刷新手感。

### A · 服务端事件
同 workspace 内广播（可跳过 actor 用户的连接）：
- `issue.created` / `issue.updated` / `issue.deleted`（payload：`id`、`issue_code`、变更字段摘要）
- `inbox.created`（新通知）
- 可选：`comment.created`

写路径 service 层 publish；失败不影响主请求（best-effort）。

### B · 前端订阅
- composable `useWorkspaceRealtime`：连接、心跳/重连、按 workspace 切换重订
- Inbox 铃铛/列表：`inbox.created` → 刷新未读
- Issue 列表/看板：`issue.*` → 防抖 refetch；详情同 id → refetch
- 断线提示极简；不做 OT/CRDT

### C · 安全
- 鉴权 = 登录用户（query `token`）+ `workspace_id` + **必须是成员**
- 非成员拒绝；事件不得跨租户泄漏；跨 WS 负例测

### D · CLI（薄）
- **不接 WS**；无用户可见 CLI 契约变更 → version **保持 1.7.0**（ADR）
- README 注明实时通道为 FE 专用

## 2. ADR

| ID | 决策 |
|----|------|
| D1 | 新路由 **`/ws/workspace`**，与 `/ws/hub*` 并存；独立 `WorkspaceRealtimeHub` 进程内单例，不改 Agent hub |
| D2 | 鉴权：query `token` + `workspace_id`（浏览器 WS 难设自定义头）；校验 JWT/AccessToken + `WorkspaceService.require_member`；失败 close `4401`/`4403`/`4400` |
| D3 | 事件 JSON：`{type, workspace_id, ts, actor_user_id?, payload}`；`issue.updated.payload.changed` 为字段名列表 |
| D4 | publish 默认 **跳过 actor_user_id 的连接**（减少自刷）；同用户其他设备仍会收到 |
| D5 | `inbox.created` 仍按 workspace 广播；FE 仅当 `recipient_user_id === me` 时刷新铃铛（防扰） |
| D6 | service 层 `try/except` 包裹 publish；永不 raise 到写路径 |
| D7 | FE：`useWorkspaceRealtime` 单例；GlobalHeader 挂载；列表防抖 400ms |
| D8 | CLI **保持 1.7.0**；不做 `ws ping`；文档说明 |
| D9 | 不做 Insights/Slack/自定义字段/自动化/Customer 深化/评论 Reactions/Agent hub 重写；不 push；不自开 E24 |

## 3. 非目标

Insights、Slack、自定义字段、自动化、Customer 深化、评论 Reactions、Agent hub 重写、远程 push、OT/CRDT、跨进程 Redis pub/sub（单实例进程内即可）。

## 4. 验收摘要

- `/ws/workspace` 成员可连、非成员/坏 token 拒绝
- Issue CRUD / 通知创建触发对应事件；跨租户不串
- FE Inbox + Issue 列表/详情可刷新；相关 vitest 不恶化
- BE pytest 绿；CLI 保持 1.7.0；本地 tip；**不 push**
