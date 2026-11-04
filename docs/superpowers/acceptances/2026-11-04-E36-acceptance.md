# E36 Acceptance：Automation `custom_field_changed`

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E36-S1`  
基线：`09c7bf0`（E35 tip + E36 design）

## 范围对照

| 项 | 状态 | 说明 |
|----|------|------|
| A trigger `custom_field_changed` | ✅ | `TRIGGER_TYPES`；upsert after-commit emit；field_key/id + from/to 过滤 |
| B 多 CF 条件 AND≤5 | ✅ | `customFields[]`；>5 → 400；单 `customField` 兼容 |
| C 防环 depth≤1 | ✅ | 自动化内 `set_custom_field` 不再二次触发 cf-changed |
| D FE | ✅ | 触发器选项 + 字段/from/to；第二 CF AND；summarize |
| E CLI 1.20.0 | ✅ | TRIGGERS + help；version 1.20.0 |

## ADR
见 design D1–D4：emit 于 upsert；depth 防环；AND max 5；CLI 1.20.0。

## TDD
- 红：非法 trigger / 无 max5 → 4 FAIL（已跑）
- 绿：`tests/api/test_e36_automation_cf_changed.py` **5P**

## 测试
- BE pytest：**929 passed** / 24 skipped（全量一次跑中 `test_tasks_jira_wire::test_user_search` 1 条偶发失败，单跑复测绿；与 E36 无关）
- CLI：**463 passed** / 89 skipped
- FE vitest：**266 passed**；`pnpm/vite build` 成功

## tip
- SHA：`58df60a`
- 未 push / 未开 PR
- **不自开 E37**

`superpowers: design/plan/TDD/verify/acceptance = ok`
