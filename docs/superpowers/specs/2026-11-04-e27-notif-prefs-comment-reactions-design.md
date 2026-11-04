# E27 设计：Notification preferences + 评论 Reactions

日期：2026-11-04（Asia/Shanghai）  
Epic：E27  
基线：`sprint/E26-S1` @ `9bf8464`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E27-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E28**。

## 1. 目标

### A · 通知偏好（人均每 WS）
- 表 `notification_preferences`：`user_id` + `workspace_id` 唯一；各类型 bool（默认全开）
- `GET/PUT /api/inbox/preferences`；仅本人；强制 `X-Workspace-Id`
- Inbox `create` 路径尊重偏好：关闭类型不落行（Watch 关系仍保留）
- 测：关 `issue_comment` 后评论不进 Inbox；跨用户互不影响

### B · FE 偏好 UI
- `/settings/notifications`：开关列表，保存即时 PUT

### C · 评论 Reactions
- 新表 `comment_reactions`（对齐 `issue_reactions`）
- `GET/POST/DELETE /api/issues/{id}/comments/{cid}/reactions`
- 详情评论区 emoji；跨租户负例；Issue 级 Reactions 不重做

### D · CLI
- `opentask notif prefs get|set`；version **1.11.0**

## 2. ADR

| ID | 决策 |
|----|------|
| D1 | 偏好键（API/CLI/FE）与 Inbox `type` 映射：`issue_assigned→assigned`、`issue_comment→commented`、`issue_mention→mentioned`、`issue_status→status_changed`、`due_date_changed→due_date_changed`、`issue_watch_event→subscribed_update`、`automation_comment→automation_comment` |
| D2 | 无偏好行 = 全开（懒默认）；GET 不自动建行；PUT upsert |
| D3 | `create()` 查偏好：映射键为 False 则跳过；**未知 type**（如 `project_health`）fail-open 仍创建 |
| D4 | automation / `comment_type=system` 或 `meta.source=automation` 的评论，assignee/reporter/watcher 通知 type=`automation_comment`；`@mention` 仍用 `mentioned` |
| D5 | 评论反应独立表 `comment_reactions`（非多态）；唯一 `(comment_id, emoji, user_id)` |
| D6 | 评论列表响应附加 `reactions: {emoji: userId[]}`；另提供独立 GET/POST/DELETE |
| D7 | FE 路由 `/settings/notifications`（顶层，侧栏 Workspace 同级「通知」也可；本期挂 Workspace 菜单旁独立入口）；Issue 详情评论行复用 `IssueReactions` |
| D8 | CLI 组 `notif` → 子组 `prefs` → `get` / `set --key --on/--off`；亦可 `set --json '{...}'`；version **1.11.0** |
| D9 | 不做邮件/Slack 外发、digest、字段级偏好；不 push；不自开 E28 |

## 3. 非目标

邮件/Slack 外发、digest 定时、字段级偏好、SmartSearch field、远程 push、E28。

## 4. 验收摘要

- 偏好 GET/PUT + create 尊重偏好 + 租户；评论 reactions CRUD + 跨租户
- FE 设置页 + 评论区；CLI 1.11.0
- BE/CLI 绿；FE 不恶化；本地 tip；**不 push**
