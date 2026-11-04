# E16 Plan：Estimate 点 + 孤儿 WS + 坏测 + PGE

日期：2026-11-04  
基线 tip：`386fc9b` · 分支 `sprint/E16-S1`

## Task 1 — Docs
- [x] design + plan（本文件）
- [x] acceptance 收口时补齐 tip/测试数

## Task 2 — Cycle 容量按点（TDD）
1. 改 `CycleService.capacity_hint`：样本累计 `completedPoints` / `completedIssueCount`（及 hours 可选）
2. `suggestedCapacity` 优先 points 均值；全 0 回退 issues；无历史 → members
3. 响应加 `unit`
4. 更新 `test_cycle_complete.py` 容量用例；新增带 points 的用例
5. FE：`CapacityHint.unit`；Cycles 页文案；可选当前 cycle 负载说明

## Task 3 — Issue 估点 UX
1. 详情右栏 `EditableField` 估点（Fibonacci + 清空）→ `updateIssue({ estimate_points })`
2. 列表加「估点」列
3. 看板/display-prefs：默认打开 `estimate_points` 字段（或保持开关但详情必显）
4. ⌘K：在 issue 详情上下文加「设置估点」轻量 action（可选）

## Task 4 — 孤儿 Default WS
1. Alembic `…_cleanup_orphan_default_workspace`：`down_revision = f6a7b8c9d0e1`
2. `WorkspaceService.cleanup_orphan_default_workspace` + `DEFAULT_WORKSPACE_ID` 常量
3. `list_for_user` 硬排除该 id
4. `tests/api/test_orphan_default_workspace.py`

## Task 5 — 3 坏测
1. `opentask/models/__init__.py` import `AccessToken`
2. 跑 `opentask/api/test/test_task_protocol_rules.py` 至绿
3. 全量 pytest 目标 0 fail

## Task 6 — PGE 快扫
1. 确认 requirements/agents/home hideInMenu + 默认 issue_list
2. 验收文档记录；无强制改码则 skip

## Task 7 — 验收 + 回执
- acceptance md；本地 commit；**不 push**；回执 Yuri tip SHA
