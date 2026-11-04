# E29 Plan：Outbound Webhooks

日期：2026-11-04  
基线 tip：`64c5371` · 分支 `sprint/E29-S1`

> **For agentic workers:** 本会话 inline 执行；TDD 优先；频繁 commit；禁止 push。

**Goal:** 工作区出站 Webhook CRUD + HMAC 投递 + FE 设置页 + CLI 1.13.0。

**Architecture:** `WorkspaceWebhook` / `WebhookDeliveryLog`；`WorkspaceWebhookService`（CRUD + deliver + fire）；写路径 after-commit `fire_webhooks`；FE `/settings/webhooks`；CLI `webhook` 组。

**Tech Stack:** FastAPI + SQLAlchemy + httpx；Vue3 + Naive UI；Click CLI；pytest/vitest。

## Global Constraints
- 本地 only；禁止 push/PR；不自开 E30；中文 docs。

---

### Task 1 — Docs
- [x] design + plan 入库
- [x] acceptance 骨架；收口补 tip/测试数

### Task 2 — BE 模型 + migration + service + API
- [x] models + alembic
- [x] service CRUD / deliver / fire_webhooks
- [x] router `/api/webhooks`
- [x] issue_service 挂钩
- [x] pytest（4P）

### Task 3 — FE
- [x] API + `/settings/webhooks` + 路由/i18n
- [x] helpers vitest（+3）

### Task 4 — CLI 1.13.0
- [x] `webhook list|create|update|delete|test`；version bump；测（3P）

### Task 5 — 门禁
- [x] BE/CLI/FE；acceptance tip；STOP
