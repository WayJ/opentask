# E34 Plan：CSV × Custom Fields

日期：2026-11-04  
基线 tip：`c1764e2` · 分支 `sprint/E34-S1`

> **For agentic workers:** 本会话 inline 执行；TDD 优先；频繁 commit；禁止 push。

**Goal:** Issue CSV 导入/导出带 `cf.<key>`；FE 说明/模板；CLI 1.18.0。

**Architecture:** 扩展 `IssueCsvService`；复用 `CustomFieldService.list` / `values_for_issues` / `upsert_issue_values` + `validate_value`；无新表。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3；Click CLI；pytest/vitest。

## Global Constraints
- 本地 only；禁止 push/PR；不自开 E35；中文 docs。

---

### Task 1 — Docs
- [x] design + plan 入库
- [x] acceptance 骨架；收口补 tip/测试数

### Task 2 — BE Export / Import / Template（TDD）
- [x] export 追加未归档 `cf.<key>`；空值空单元格
- [x] template 动态列头
- [x] import 解析 `cf.*`；类型转换；未知/校验失败 partial + errors[]
- [x] pytest：导出列、导入写入、未知 key、boolean/multi

### Task 3 — FE
- [x] Import 文案提 `cf.*`；必要时 helper 测

### Task 4 — CLI 1.18.0
- [x] version bump；export/import help 提 `cf.<key>`；全仓断言

### Task 5 — 门禁
- [x] BE/CLI pytest；FE vitest/build；acceptance tip；STOP
