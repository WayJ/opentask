# E61 Acceptance：Insights 共享报表 mid · CLI 1.45.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E61-S1`  
基线：`36dfb75`（全文 `36dfb7566d991e02cc31af405c39a9488faa85b5`；含 E61 design；E60 实现 tip `950256e` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e61-insights-shared-reports-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e61-insights-shared-reports.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A visibility 列 + 回填 personal | ✅ | alembic `t6c7d8e9f0a4`；model + conftest ALTER；默认 personal |
| B list mine∪shared / ACL / fork / caps | ✅ | canEdit；member+ share；非 owner 写 404；fork personal；cap 20/50 |
| C digest 仍 owner-default；无 Inbox 广播 | ✅ | E59 语义保留；share 不 fire_webhooks / 不广播 |
| D FE 我的/团队 + share/fork；vitest；build | ✅ | partitionReports；分享开关；另存为我的 |
| E CLI 1.45.0 + list/set-visibility/fork | ✅ | `--mine/--shared/--all`；`--visibility`；pins 全钉 |
| F 跨租户；no-emit；不改 E57–E58/E60 主表面 | ✅ | 跨租户 404；spy；仅 CLI version pins |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：**1182 passed / 24 skipped / 1 failed**（已知 flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`，与 E61 无关）
- BE 定向 E61+E59+E55 insights：**24 passed**（E61 10 + E59 7 + E55 7）
- CLI：**553 passed / 89 skipped**（全钉 **1.45.0**）
- FE vitest：**355 passed**（46 files）；`pnpm run build`：**ok**

## Tip

- 分支：`sprint/E61-S1`
- tip：`9150b3a`（全文 `9150b3a3c94bf7751aeba06e38602657a98e93c4`）— 本 acceptance tip commit 后以 HEAD 为准
- **未 push / 未开 PR / 未开 E62**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`
