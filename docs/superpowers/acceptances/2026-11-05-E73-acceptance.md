# E73 Acceptance：Issue start_date mid — 计划开始日 · CLI 1.57.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E73-S1`  
基线：`be2a150`（全文 `be2a150b212cc76379423405584947c86cc0e7ee`；含 E73 design；E72 实现 tip `6911e71` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e73-issue-start-date-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e73-issue-start-date-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A 数据/BE | ⏳ | alembic `start_date`；CRUD；校验；filters；sort；audit；`started_at` 不动 |
| B Timeline/FE | ⏳ | 详情可编；双端 bar；vitest+build；`f`+`r` |
| C CLI 1.57.0 | ⏳ | `--start-date` + show + list filters；全钉 VERSION |
| D 安全/邻面/no-emit | ⏳ | 无新 webhook 名；formula no-emit；reminders 不因 start；不改 E63–E72 主表面 |
| E 租户隔离 | ⏳ | 跨租户 404 不变 |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：_pending_
- CLI：_pending_
- FE：_pending_

## Tip

- 分支：`sprint/E73-S1`
- tip：_pending_
- **未 push / 未开 PR / 未开 E74**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = pending`

**STOP** — 未 push / 未开 PR / 未开 E74
