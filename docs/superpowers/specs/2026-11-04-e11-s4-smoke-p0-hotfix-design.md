# E11-S4 设计：浏览器冒烟 P0 热修 + UX 收紧

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E11-S4` @ 基线 `sprint/E11-S3` `4ab29b3`  
worktree：`/workspace/opentask-worktrees/E11-S4`  
约束：不推远程；不改 DESIGN.md/Naive/soybean 全局主题色与字体栈；非整 Epic。

## 根因（已核实）

1. **附件 500**：live DB 无 `documents` 表（Alembic 从未建；pytest 靠 `create_all`）。`GET /api/issues/{id}/attachments` → ProgrammingError → 500；FE 全局 onError 弹 raw axios 文案。
2. **角色矛盾**：注册 `User.role=viewer` + 个人 WS `WorkspaceMember.role=owner`。Profile `/api/users/me` 只回平台 role/RBAC →「查看者」+ `*:view`；Members 显示 owner 且工作区 API 放行创建。
3. **Issue Key 改后序号**：E12-S1 故意「改 key 只影响新单、counter 单调」→ `SMOKE2-1` 后改 `SMK` 得 `SMK-2`。冒烟期望可预期；产品取舍：**改 key 时 reset `issue_counter=0`，下一单 `NEWKEY-1`**；创建 WS 可显式设 `issueKey`。
4. **假 Home**：`views/home` 仍为 Soybean 模板；`.env.example` 已 `VITE_ROUTE_HOME=issue_list` 但运行态仍可进 `/home`。

## 决策

| # | 决策 |
|---|---|
| P0-1 | Alembic 建 `documents`（+ enum）；空列表 200；FE 附件加载失败不刷屏 |
| P0-2 | 注册默认平台角色 `developer`（+ 可选 UserRole 挂接）；`/me`+`getUserInfo` 带 `workspaceRole`；Profile 优先展示工作区角色 |
| P0-3 | `WorkspaceCreate.issueKey`；PATCH 改 key → reset counter；UI 文案「更改后下一单从 1 起」 |
| P0-4 | 默认落地 `issue_list`；Home 换成工作区摘要迷你看板（Issue/Inbox/Cycle），去掉假流量/$/soybean 新闻 |
| UX | 同 sprint：冒烟页布局/间距/空状态/属性栏换行/i18n 裸 key/工作管理空白页降级；不换肤 |

## 非目标

新 Epic、远程 push、换主题 token、大改路由名、强制 SMTP、浏览器完整 E2E 门禁。
