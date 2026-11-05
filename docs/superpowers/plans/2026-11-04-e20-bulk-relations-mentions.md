# E20 Plan：Bulk · Relations · Mentions

日期：2026-11-04  
基线 tip：`f78d5ff` · 分支 `sprint/E20-S1`

## Task 1 — Docs
- [x] design + plan（本文件）
- [x] acceptance 收口时补 tip/测试数

## Task 2 — BE Bulk 扩展（TDD）
1. `IssueBulkUpdate` + `cycle_id` / `tag_ids`
2. service：校验 cycle 同 WS；可选 replace tags；workspace 过滤 issue_ids
3. router：`require_workspace_context`
4. pytest：本租户更新 / 跨租户拒绝 / cycle+tags

## Task 3 — BE Relation 摘要
1. list（及可选 detail）附 `blocks_count` / `blocked_by_count`
2. 批量查 IssueRelation，避免 N+1
3. pytest 计数正确

## Task 4 — FE 多选 + Bulk 栏
1. `useIssueSelection` + hotkey X / Shift+X / Esc
2. `IssueBulkBar`：status/assignee/priority/cycle/labels
3. 接入 list + board

## Task 5 — FE Relations
1. 列表/看板徽章
2. 详情 Relations CRUD UI 打磨

## Task 6 — Mentions / IssueReference
1. 新建组件 + MarkdownRenderer 解析
2. 复活 vitest；去掉 describe.skip

## Task 7 — CLI
1. `issue bulk-update`；version **1.5.0**；测+README

## Task 8 — 验收
- acceptance md；本地 commit；**不 push**；回执 tip；STOP
