# E23 Plan：Workspace 实时通道

日期：2026-11-04  
基线 tip：`82795db` · 分支 `sprint/E23-S1`

> **For agentic workers:** 本会话 inline 执行；TDD 优先；频繁 commit；禁止 push。

**Goal:** Workspace 业务 WS 事件 + FE 订阅刷新；不拆 Agent hub；CLI 保持 1.7.0。

**Architecture:** 独立 `WorkspaceRealtimeHub` + `/ws/workspace`；Issue/Notification service best-effort publish；Vue composable 单例。

**Tech Stack:** FastAPI WebSocket + SQLAlchemy；Vue3 composable；vitest/pytest。

## Global Constraints
- 本地 only；禁止 push/PR；不自开 E24；中文 docs。

---

### Task 1 — Docs
- [ ] design + plan 入库
- [ ] acceptance 骨架；收口补 tip/测试数

### Task 2 — Hub + 路由（TDD）
- [ ] `services/workspace_realtime/`：hub / events / publish
- [ ] `/ws/workspace` 鉴权 + 成员校验
- [ ] pytest：hub 广播/跳过 actor；WS 坏 token/非成员；成员收 issue 事件

### Task 3 — 写路径 hooks
- [ ] IssueService create/update/delete → issue.*
- [ ] NotificationService.create → inbox.created
- [ ] IssueService.add_comment → comment.created

### Task 4 — FE
- [ ] `useWorkspaceRealtime` + vitest（解析/防抖逻辑可测部分）
- [ ] GlobalHeader 挂载；InboxBell / Inbox 页刷新
- [ ] Issue 列表防抖 refetch；详情同 id refetch；极简断线提示

### Task 5 — CLI
- [ ] ADR：保持 1.7.0；README 一句说明不接 WS

### Task 6 — 门禁
- [ ] BE pytest；CLI pytest；FE lint/build/相关 vitest；acceptance tip；STOP
