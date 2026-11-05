# E18 设计：Issue Watch / Subscribe · Search Doc 深链 · vitest pinia

日期：2026-11-04（Asia/Shanghai）  
Epic：E18  
基线：`sprint/E17-S1` @ `62bf578`  
worktree：`/workspace/opentask-worktrees/E11-S4` · 分支 `sprint/E18-S1`  
约束：**本地提交，禁止 push / 开 PR**；齐套后待命，**不自开 E19**。

## 1. 目标

### A. Issue Watch / Subscribe（Linear）
- 详情页一键关注 / 取消关注
- 被关注 Issue 的 **评论 / 状态变更 / 指派变更** 写入关注者 Inbox（跳过 actor 自己）
- 最小 API + FE + CLI；强制 workspace membership；跨租户负例

### B. 收口 E17 Gap：Search Doc 深链
- Doc 结果按 `parentType` 跳转：`issue` → Issue 详情、`initiative` → Initiative 详情、`project` → Project 详情
- 带 `doc=<id>` query；父页 EntityDocsPanel 自动打开该短文档
- 键盘 ↑↓/Enter 仍可用

### C. 清 FE 全量 vitest `@pinia/testing` 失败
- 根因：`@pinia/testing` 未装，且 auth store 单测与现实现脱节
- 优先修绿：补依赖 + 重写为可运行的最小套件（或在确属夹具不可解时 skip 并写清原因）

## 2. 探索事实

| 项 | 现状 |
|---|---|
| Project watchers | `project_watchers` + `/api/projects/{id}/watchers`；health fanout Inbox |
| Issue Inbox | `NotificationService.notify_assigned / notify_comment`；无 watcher fanout |
| Favorites | 侧栏 pin ≠ Watch（收藏不产生评论/状态 Inbox） |
| Search docs href | 一律 `/workflow/project-detail?id=parentId`；initiative/issue 错链 |
| EntityDocsPanel | 无 `doc` query 自动打开 |
| vitest | `auth/__tests__/index.test.ts` import `@pinia/testing` 解析失败（E17 记 2 既有失败） |

## 3. 决策

| ID | 决策 |
|----|------|
| D1 | 新表 `issue_watchers`（workspace_id, issue_id, user_id，uq issue+user）；镜像 project_watchers |
| D2 | API：`GET/POST/DELETE /api/issues/{id}/watchers`；需 `X-Workspace-Id` + membership；issue 必须属该 WS |
| D3 | 通知类型：评论复用 `commented`；状态用 `status_changed`；指派对 watcher 用 `subscribed_update`（非新 assignee 时）；Inbox UI 补标签 |
| D4 | FE 详情「关注」按钮旁侧栏收藏；list watchers 判当前用户 |
| D5 | CLI：`issue watch|unwatch|watchers`；`issue show` 附 `watching`；bump **1.3.0** |
| D6 | Search flatten：`docHref(parentType,parentId,docId)`；EntityDocsPanel 读 `route.query.doc` 打开编辑 |
| D7 | 中文 design/plan/acceptance；不 push；不改主题令牌；不自开 E19 |

## 4. 非目标
- 邮件 / IM 外发
- Watch 规则细粒度（仅评论 / 仅状态）
- 替换 Favorites
- Knowledge-base 全文进 Search

## 5. 验收摘要
- watch/unwatch 幂等；跨租户 403/404
- 关注者收到 comment/status/assignee Inbox；actor 自己不收
- Search Doc 深链可打开对应父实体 + 短文档；键盘跳转
- 全量 vitest 无 `@pinia/testing` 解析失败（优先绿）
- BE/CLI 相关测绿；本地 tip；**不 push**
