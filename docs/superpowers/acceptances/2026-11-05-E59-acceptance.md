# E59 Acceptance：Insights 再厚 / 效能日报 mid · CLI 1.43.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E59-S1`  
基线：`e52ad34`（全文 `e52ad34dd8ffc25a8f44fc471c2f52a4cd81ed71`；含 E59 design；E58 实现 tip `0494871` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e59-insights-saved-reports-digest-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e59-insights-saved-reports-digest.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A 多 label OR | ✅ | Q1a 同传 400；重复+逗号；OR EXISTS；cycleSnapshot 收窄；单 labelId 别名 |
| B 我的报表 | ✅ | `insights_saved_reports` + alembic；personal-only；cap 20；isDefault≤1；Q4a 无专用 summary |
| C digest | ✅ | pref `insights_digest` 默认关；Inbox type；日账本 unique；`require_writer` tick；邮件钩 |
| D FE | ✅ | Label 多选 OR；我的报表；digest 开关；vitest normalize/OR/round-trip |
| E CLI 1.43.0 | ✅ | summary/export `--label-ids`；`reports list\|create\|delete`；`run-digest`；pins 全钉 |
| F no-emit / 不改 E57–E58 | ✅ | spy 无 fire_webhooks；无新 webhook 事件；不改假日包/告警主表面 |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：**1162 passed / 24 skipped / 1 failed**（已知 flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`，与 E59 无关）
- BE 定向 E59+E55+E24 insights：**20 passed**
- CLI：**549 passed / 89 skipped**（全钉 **1.43.0**）
- FE vitest：**351 passed**（46 files）；`pnpm run build`：**ok**

## Tip

- 分支：`sprint/E59-S1`
- tip：`0f24e65`（全文 `0f24e65ddc87c4bfa95e53f48c3d122e836dcf47`）
- **未 push / 未开 PR / 未开 E60**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`
