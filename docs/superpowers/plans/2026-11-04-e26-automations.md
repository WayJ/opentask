# E26 Plan：Automations lite

日期：2026-11-04  
基线 tip：`dfae2ae` · 分支 `sprint/E26-S1`

> **For agentic workers:** 本会话 inline 执行；TDD 优先；频繁 commit；禁止 push。

**Goal:** Workspace 自动化规则 CRUD + after-commit 执行器（防环）+ FE 管理页 + CLI 1.10.0。

**Architecture:** `AutomationRule` 模型；`AutomationService`（CRUD + match + execute）；写路径 hook；`/api/automations`；FE `/workspace/automations`。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic；Vue3 + Naive UI；Click CLI；pytest/vitest。

## Global Constraints
- 本地 only；禁止 push/PR；不自开 E27；中文 docs。

---

### Task 1 — Docs
- [x] design + plan 入库
- [x] acceptance 骨架；收口补 tip/测试数

### Task 2 — BE 模型 + 迁移
- [x] `models/automation/`：AutomationRule
- [x] alembic 迁移；models `__init__` 注册

### Task 3 — BE API + 执行器（TDD）
- [x] `services/automation/service.py`（CRUD、条件、执行、防环）
- [x] `api/automations/router.py`
- [x] hooks：issue create/update、tag attach/replace
- [x] pytest：触发→动作、防环、租户、viewer

### Task 4 — FE
- [x] API client + `/workspace/automations` + 路由/i18n
- [x] 基本 vitest

### Task 5 — CLI 1.10.0
- [x] `automation list|create|enable|disable`；version bump；测

### Task 6 — 门禁
- [x] BE pytest；CLI pytest；FE lint/build/相关 vitest；acceptance tip；STOP
