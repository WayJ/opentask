# E22 Plan：Customers · Requests · Issue 关联 · CLI 1.7.0

日期：2026-11-04  
基线 tip：`4450441` · 分支 `sprint/E22-S1`

> **For agentic workers:** 本会话 inline 执行；TDD 优先；频繁 commit；禁止 push。

**Goal:** Workspace 级 Customers + CustomerRequests + Issue M2M 链接；产品面与 CLI 1.7.0。

**Architecture:** 新表 customers / customer_requests / customer_request_issues；FastAPI 路由 + service；Vue 列表/详情；CLI 薄封装。

**Tech Stack:** FastAPI + SQLAlchemy + alembic；Vue3 + Naive；Click CLI。

## Global Constraints
- 本地 only；禁止 push/PR；不自开 E23；中文 docs。

---

### Task 1 — Docs
- [ ] design + plan 入库
- [ ] acceptance 骨架；收口补 tip/测试数

### Task 2 — Models + Migration
- [ ] Customer / CustomerRequest / CustomerRequestIssue
- [ ] alembic revision（revises `b2c3d4e5f6a0`）
- [ ] models `__init__` 注册

### Task 3 — Service + API（TDD）
- [ ] CustomerService / CustomerRequestService + require_writer
- [ ] routers 注册 app.py
- [ ] pytest：CRUD、viewer 403、跨租户 404、link/unlink、createAndLinkIssue、issue_id 过滤

### Task 4 — FE
- [ ] service/api customers + customer-requests
- [ ] views：customers / customers/detail / requests / requests/detail
- [ ] elegant 路由/imports/transform/typings
- [ ] 侧栏 CustomersNav
- [ ] Issue 详情「客户需求」区块

### Task 5 — CLI 1.7.0
- [ ] customer / request 命令 + api_client
- [ ] version bump 全处；测断言 1.7.0

### Task 6 — 门禁
- [ ] BE pytest；CLI pytest；FE lint/build/相关 vitest；acceptance tip；STOP
