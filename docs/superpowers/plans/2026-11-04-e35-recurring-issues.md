# E35 Plan：Recurring Issues

日期：2026-11-04（Asia/Shanghai）  
基线 tip：`4014f92`（其上另有 `8b0abb1` docs gate）· 分支 `sprint/E35-S1`  
Yuri 代审：design 对齐 E35 brief → 视为已代审，本会话直接 TDD/实现/verify。

> **For agentic workers:** inline 执行；TDD；频繁 commit；**禁止 push/PR**；**不自开 E36**。

**Goal:** 周期蓝本 CRUD + `run-due` 建 Issue；FE `/settings/recurrences`；CLI 1.19.0。

**Architecture:** `issue_recurrences` 表 + `IssueRecurrenceService`（UTC schedule + after-create labels/CF）；`POST /api/recurrences/run-due` 供外部调度；不内置 cron。

**Tech Stack:** FastAPI + SQLAlchemy + alembic；Vue3/Naive；Click CLI；pytest/vitest。

## Global Constraints
- 时区 UTC（ADR D1）；interval 仅 daily/weekly/monthly；本地 tip；禁止 push；不自开 E36。

---

### Task 1 — Docs
- [x] design（Yuri brief 代审）+ plan 入库
- [x] acceptance 收 tip/测数

### Task 2 — BE 模型/CRUD/run-due（TDD）
- [x] 红测：`tests/api/test_recurrences.py` + `tests/unit/test_recurrence_schedule.py`
- [x] 绿：model/migration/service/router；权限 member+ 写 / viewer 读；跨租户 404
- [x] run-due：建 KEY-N、占位符、推进 next_run_at、单条失败隔离

### Task 3 — FE
- [x] `/settings/recurrences` + api helper 测 + 路由/i18n

### Task 4 — CLI 1.19.0
- [x] `recurrence list|create|update|delete|run-due`；version bump 全仓

### Task 5 — 门禁
- [x] BE/CLI/FE 证据；acceptance；STOP
