# E25 Plan：Issue Custom Fields

日期：2026-11-04  
基线 tip：`29ecfe5` · 分支 `sprint/E25-S1`

> **For agentic workers:** 本会话 inline 执行；TDD 优先；频繁 commit；禁止 push。

**Goal:** Workspace 自定义字段定义 + Issue 取值 + FE 设置/详情 + CLI 1.9.0。

**Architecture:** `CustomField` / `IssueCustomFieldValue` 模型；`CustomFieldService`；`/api/custom-fields` + `PATCH /api/issues/{id}/custom-fields`；详情默认附带；列表 opt-in。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic；Vue3 + Naive UI；Click CLI；pytest/vitest。

## Global Constraints
- 本地 only；禁止 push/PR；不自开 E26；中文 docs。

---

### Task 1 — Docs
- [x] design + plan 入库
- [x] acceptance 骨架；收口补 tip/测试数

### Task 2 — BE 模型 + 迁移
- [x] `models/custom_field/`：CustomField + IssueCustomFieldValue
- [x] alembic 迁移；models `__init__` 注册

### Task 3 — BE API（TDD）
- [x] `services/custom_field/service.py`（slug、校验、归档）
- [x] `api/custom_fields/router.py`
- [x] Issue GET 附带；list `?include=custom_fields`；`PATCH .../custom-fields`
- [x] pytest：类型校验、租户、viewer、归档/硬删、详情/列表 include

### Task 4 — FE
- [x] API client + `/workspace/custom-fields` 页 + 路由/i18n
- [x] Issue 详情可编辑区；创建可选填
- [x] 基本 vitest（API/常量）

### Task 5 — CLI 1.9.0
- [x] `custom-field list|create`；`issue set-field`；version bump；测

### Task 6 — 门禁
- [x] BE pytest；CLI pytest；FE lint/build/相关 vitest；acceptance tip；STOP
