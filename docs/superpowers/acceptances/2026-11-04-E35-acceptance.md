# E35 Acceptance：Recurring Issues

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E35-S1`  
基线：`sprint/E34-S1` @ `4014f92`（其上 `8b0abb1` docs gate）

## 范围对照

| 项 | 状态 | 说明 |
|----|------|------|
| A 模型 + CRUD | ✅ | `issue_recurrences`；`GET/POST /api/recurrences`；`GET/PATCH/DELETE /{id}`；member+ 写 / viewer 读；`X-Workspace-Id`；跨租户 404 |
| B run-due | ✅ | `POST /api/recurrences/run-due`；`{date}`/`{yyyy-mm-dd}`；一次 tick 每条最多 1 张；推进至 > now(UTC)；单条失败隔离 |
| C FE | ✅ | `/settings/recurrences` 列表/创建/启停/run-due；空状态 |
| D CLI 1.19.0 | ✅ | `recurrence list\|create\|update\|delete\|run-due`；version 1.19.0 |

## ADR 摘要
见 `docs/superpowers/specs/2026-11-04-e35-recurring-issues-design.md` D1–D11。

要点：UTC；无内置 cron；labels=tag name；CF partial attach；assignee/project 非法则该条失败。

## TDD
- 红：`expand_title` 临时 `NotImplementedError` → `test_expand_title_placeholders` FAIL（证据已跑）
- 绿：`tests/unit/test_recurrence_schedule.py` 5P + `tests/api/test_recurrences.py` 5P

## 测试
- BE pytest：**924 passed** / 24 skipped（全量一次跑中 `test_tasks_jira_wire::test_user_search` 1 条偶发失败，单跑复测绿；与 E35 无关）
- CLI：**461 passed** / 89 skipped
- FE vitest：**262 passed**；`pnpm/vite build` 成功

## tip
- SHA：以 `git rev-parse HEAD` 为准（本文件提交后 tip）
- 未 push / 未开 PR
- **不自开 E36**

`superpowers: design/plan/TDD/verify/acceptance = ok`
