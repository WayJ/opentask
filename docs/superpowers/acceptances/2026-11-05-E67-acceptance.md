# E67 Acceptance：Workspace 时区进 due/recurrence mid — 本地日历日 · CLI 1.51.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E67-S1`  
基线：`1fa4a85`（全文 `1fa4a8575e695520783b652a24a39352b407353f`；含 E67 design；E66 实现 tip `ea96ebd` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e67-workspace-timezone-due-recurrence-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e67-workspace-timezone-due-recurrence-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A resolve_workspace_tz / local_today | ✅ | Q3a 空/非法→UTC；单测跨日 Asia/Shanghai |
| B due reminders 本地日 | ✅ | Q1a soon/overdue/bucket_date；`today=` 注入仍优先；`now_utc=` 可测 |
| C recurrence title 本地日 | ✅ | Q2a 仅 title；advance/`next_run_at` 仍 UTC naive；无 alembic |
| D FE 文案 + vitest | ✅ | Q4a 不新开时区页；`workspaceLocalToday` 纯函数；通知/周期文案对齐 |
| E CLI 1.51.0 | ✅ | Q6a 全钉 **1.51.0**；`notif run-due-reminders` / `recurrence run-due` help 注明 WS TZ |
| F 安全 / no-emit / 邻面不动 | ✅ | Q5a 无新 webhook（spy）；不改 E57–E66 邻面主表面；formula 未触；elegant-router `f`+`r` 守 E63（build 误删已还原） |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：**1237 passed / 24 skipped / 1 failed**（已知 flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`，与 E67 无关）
- BE 定向 E67+due+recurrence：**33 passed**（unit workspace_time 5 + api e67 6 + e39 + recurrences + recurrence_schedule）
- CLI：**569 passed / 89 skipped**（全钉 **1.51.0**）
- FE vitest：**371 passed**（51 files）；`pnpm run build`：**ok**（elegant-router 误删 f/r 已还原）

## Tip

- 分支：`sprint/E67-S1`
- tip：`d896a15`（全文 `d896a151e4cd2553672a9b1049fb886701e8ad1b`）
- **未 push / 未开 PR / 未开 E68**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E68
