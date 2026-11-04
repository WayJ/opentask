# E67 Acceptance：Workspace 时区进 due/recurrence mid — 本地日历日 · CLI 1.51.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E67-S1`  
基线：`1fa4a85`（全文 `1fa4a8575e695520783b652a24a39352b407353f`；含 E67 design；E66 实现 tip `ea96ebd` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e67-workspace-timezone-due-recurrence-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e67-workspace-timezone-due-recurrence-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A resolve_workspace_tz / local_today | ⏳ | Q3a 空/非法→UTC |
| B due reminders 本地日 | ⏳ | Q1a soon/overdue/bucket_date |
| C recurrence title 本地日 | ⏳ | Q2a 不改 advance；无 alembic |
| D FE 文案 + vitest | ⏳ | Q4a 不新开时区页 |
| E CLI 1.51.0 | ⏳ | Q6a pins + help |
| F 安全 / no-emit / 邻面不动 | ⏳ | Q5a 无新 webhook |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：_pending_
- BE 定向：_pending_
- CLI：_pending_
- FE vitest：_pending_；`pnpm run build`：_pending_

## Tip

- 分支：`sprint/E67-S1`
- tip：_pending_
- **未 push / 未开 PR / 未开 E68**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = pending`

**STOP** — 未 push / 未开 PR / 未开 E68
