# E18 Plan：Issue Watch · Doc 深链 · pinia vitest

日期：2026-11-04  
基线 tip：`62bf578` · 分支 `sprint/E18-S1`

## Task 1 — Docs
- [ ] design + plan（本文件）
- [ ] acceptance 收口时补 tip/测试数

## Task 2 — BE Issue Watchers（TDD）
1. migration `issue_watchers`（revises `a1b2c3d4e5f9`）
2. model + `IssueWatcherService`（list/watch/unwatch/user_ids + serialize）
3. router nested under `/api/issues/{id}/watchers`
4. `NotificationService`：评论收件人并入 watchers；status/assignee 变更 fanout
5. pytest：幂等 watch、跨租户拒绝、comment/status/assign fanout 跳过 actor

## Task 3 — FE Watch + Inbox 标签
1. `service/api/issue-watchers.ts`（或并入 issue.ts）
2. Issue 详情关注按钮
3. Inbox `typeLabel` 补 `status_changed` / `subscribed_update`

## Task 4 — Search Doc 深链
1. `global-search.ts` docHref by parentType + `doc` query
2. 更新 vitest
3. EntityDocsPanel：`route.query.doc` → 自动 openEdit

## Task 5 — CLI
1. api_client watch/unwatch/list_watchers
2. `issue watch|unwatch|watchers`；show 展示 Watching
3. 单测 + version **1.3.0** + README

## Task 6 — vitest @pinia/testing
1. 安装 `@pinia/testing`（对齐 pinia 3）
2. 重写 auth store 最小可运行套件；若仍因 router 注入不可解则 skip 并写清原因（优先绿）

## Task 7 — 验收
- acceptance md；本地 commit；**不 push**；回执 tip SHA；STOP
