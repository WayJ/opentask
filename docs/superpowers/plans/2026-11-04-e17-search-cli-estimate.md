# E17 Plan：Search + CLI estimate/capacity + alembic

日期：2026-11-04  
基线 tip：`b4ec445` · 分支 `sprint/E17-S1`

## Task 1 — Docs
- [x] design + plan（本文件）
- [x] acceptance 收口时补 tip/测试数

## Task 2 — A1 alembic :7377
1. `cd backend && uv run alembic upgrade head`
2. 用 smoke 账号或 SQL 确认孤儿 Default WS 已删/不可列
3. 记录到 acceptance / smoke 笔记

## Task 3 — A2 CLI estimate_points + cycle capacity（TDD）
1. `api_client.create_issue/update_issue` 透传 `estimate_points`
2. `issue create/update --estimate-points`；show/list 展示
3. `api_client.get_cycle_capacity_hint`；`cycle capacity`；`cycle show` 附带 hint
4. 单测：estimate 透传、capacity 调用；README + version 1.2.0

## Task 4 — B Search API（TDD）
1. `opentask/api/search/` + `services/search/service.py`
2. `GET /api/search?q=&limit=`
3. pytest：同 WS 命中；缺头 400；跨租户 403；空 q → 空分组

## Task 5 — B FE Search 页 + ⌘K
1. `views/search/index.vue` + elegant routes/imports/transform/types
2. `service/api/search.ts`；i18n zh/en
3. ⌘K `nav.search` → `/search` 或 `/search?q=`
4. vitest：分组 flatten / keyboard index helpers；nav 断言 search 路由存在

## Task 6 — 验收
- acceptance md；本地 commit；**不 push**；回执 tip SHA
