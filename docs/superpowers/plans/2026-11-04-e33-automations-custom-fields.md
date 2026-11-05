# E33 Plan：Automations × Custom Fields

日期：2026-11-04  
基线 tip：`b5a7418` · 分支 `sprint/E33-S1`

> **For agentic workers:** 本会话 inline 执行；TDD 优先；频繁 commit；禁止 push。

**Goal:** 自动化条件/动作支持自定义字段；FE 编辑器；CLI 1.17.0。

**Architecture:** 扩展 `AutomationService._match_condition` / `_execute_action`；复用 `CustomFieldService`；无新表/迁移。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3 + Naive UI；Click CLI；pytest/vitest。

## Global Constraints
- 本地 only；禁止 push/PR；不自开 E34；中文 docs。

---

### Task 1 — Docs
- [x] design + plan 入库
- [x] acceptance 骨架；收口补 tip/测试数

### Task 2 — BE 条件 + 动作（TDD）
- [x] `ACTION_TYPES` += `set_custom_field`
- [x] `_match_condition` 解析 `customField` + ops
- [x] `_execute_action` → upsert；校验失败 log+rollback
- [x] pytest：eq/contains/is_set/未知 field；set 成功；校验失败不半写；防环

### Task 3 — FE
- [x] action 选项 + CF 条件下拉/op/值；列表摘要
- [x] helpers + vitest

### Task 4 — CLI 1.17.0
- [x] ACTIONS + update 命令；version bump；全仓断言

### Task 5 — 门禁
- [x] BE/CLI pytest；FE vitest/build；acceptance tip；STOP
