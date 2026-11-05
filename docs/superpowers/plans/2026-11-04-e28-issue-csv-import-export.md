# E28 Plan：Issue CSV Import / Export

日期：2026-11-04  
基线 tip：`be27e7d` · 分支 `sprint/E28-S1`

> **For agentic workers:** 本会话 inline 执行；TDD 优先；频繁 commit；禁止 push。

**Goal:** Issue CSV 导出/导入（过滤对齐 list、upsert by code、权限）+ FE 列表入口 + CLI 1.12.0。

**Architecture:** `IssueCsvService`（export 流式 / import 逐行）；路由挂在 `/api/issues` 静态路径（先于 `/{issue_id}`）；FE list 头按钮；CLI `issue export|import`。

**Tech Stack:** FastAPI + SQLAlchemy；csv 标准库；Vue3 + Naive UI；Click CLI；pytest/vitest。

## Global Constraints
- 本地 only；禁止 push/PR；不自开 E29；中文 docs。

---

### Task 1 — Docs
- [x] design + plan 入库
- [x] acceptance 骨架；收口补 tip/测试数

### Task 2 — BE CSV service + routes
- [x] `services/issue_csv/service.py`：columns、export_rows、import_csv、template
- [x] `GET /api/issues/export.csv`、`GET /api/issues/import/template.csv`、`POST /api/issues/import`
- [x] pytest：导出列、导入创建/更新/错误行、viewer 403、缺头 400、跨租户 assignee

### Task 3 — FE
- [x] API：export blob / import multipart / template
- [x] 列表 Export + Import 对话框；helpers vitest

### Task 4 — CLI 1.12.0
- [x] `issue export|import`；version bump；测

### Task 5 — 门禁
- [x] BE/CLI/FE；acceptance tip；STOP
