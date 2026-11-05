# E19 Plan：Home / My Issues · Due→Inbox · Watchers

日期：2026-11-04  
基线 tip：`46d562b` · 分支 `sprint/E19-S1`

## Task 1 — Docs
- [x] design + plan（本文件）
- [x] acceptance 收口时补 tip/测试数

## Task 2 — BE list 滤参（TDD）
1. `IssueQueryParams` + router：`watching`/`due_before`/`due_soon`；`me` 解析
2. `IssueService.get_issues` 实现滤参
3. pytest：me / watching / due_soon / 跨租户 header 仍隔离

## Task 3 — Due → Inbox + timeline
1. `NotificationService.notify_due_date_changed`
2. `update_issue` 检测 due_date 变更 → timeline + notify
3. Inbox FE `typeLabel.due_date_changed`
4. pytest fanout 跳过 actor

## Task 4 — Watchers 展示
1. list watchers 附 username/name
2. Issue 详情 Watchers 区（名列表 + 自己可取消）

## Task 5 — Home + list 深链
1. Home 四区：Assigned / Created / Watching / Due soon（计数 + 跳转）
2. Issue list 解析 `scope` query → API 滤参
3. 相关 vitest（若有）或最小单测

## Task 6 — CLI
1. api_client + `issue list --mine/--watching/--due-soon`
2. 单测；version **1.4.0**；README 一行

## Task 7 — 验收
- acceptance md；本地 commit；**不 push**；回执 tip；STOP
