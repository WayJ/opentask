# E31 Plan：Public Issue Forms

日期：2026-11-04  
基线 tip：`06885b5` · 分支 `sprint/E31-S1`

> **For agentic workers:** 本会话 inline 执行；TDD 优先；频繁 commit；禁止 push。

**Goal:** 公开 Issue 表单（CRUD + 无鉴权提交）+ FE 设置/公开页 + CLI 1.15.0。

**Architecture:** `issue_forms` 表；`IssueFormService`（CRUD + submit 建 Issue/可选 Request）；管理路由 `/api/forms`；公开路由 `/api/public/forms`；FE settings + `/f/:token`；CLI `form`。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3 + Naive UI；Click CLI；pytest/vitest。

## Global Constraints
- 本地 only；禁止 push/PR；不自开 E32；中文 docs。

---

### Task 1 — Docs
- [x] design + plan 入库
- [x] acceptance 骨架；收口补 tip/测试数

### Task 2 — BE
- [x] migration `issue_forms`
- [x] model + service（字段校验、submit、rate-limit、regenerate）
- [x] routers 管理 + 公开
- [x] pytest（CRUD、公开、权限、租户、校验、禁用 404）

### Task 3 — FE
- [x] `/settings/forms` + API client + vitest helpers
- [x] 公开页 `/f/:token`（blank）

### Task 4 — CLI 1.15.0
- [x] `form list|create|update|delete|url`；version bump；测

### Task 5 — 门禁
- [x] BE/CLI/FE；acceptance tip；STOP
