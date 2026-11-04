# E32 Plan：Custom Fields surfaces

日期：2026-11-04  
基线 tip：`6923085` · 分支 `sprint/E32-S1`

> **For agentic workers:** 本会话 inline 执行；TDD 优先；频繁 commit；禁止 push。

**Goal:** Issue list 按 CF 过滤 + SmartSearch `field:key:value` + Display 列 + CLI 1.16.0。

**Architecture:** 扩展 `get_issues` / list router 解析 `cf.*`；`CustomFieldService` 解析匹配 issue_id 子查询；FE parser/prefs/list；CLI `--cf`。

**Tech Stack:** FastAPI + SQLAlchemy/JSONB；Vue3；Click CLI；pytest/vitest。

## Global Constraints
- 本地 only；禁止 push/PR；不自开 E33；中文 docs。

---

### Task 1 — Docs
- [x] design + plan 入库
- [x] acceptance 骨架；收口补 tip/测试数

### Task 2 — BE
- [x] `parse_cf_query_filters` + service 匹配
- [x] list router 接入；pytest（类型、未知 key 空、跨租户）

### Task 3 — FE
- [x] issueSearchParser `field:`/`cf:`
- [x] display-prefs `custom_field_keys`
- [x] DisplayOptionsPanel + list 列 / include / cf params
- [x] vitest

### Task 4 — CLI 1.16.0
- [x] `--cf`；version；测

### Task 5 — 门禁
- [x] BE/CLI/FE；acceptance tip；STOP
