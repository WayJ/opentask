# E81 Acceptance：Project milestones CLI mid · CLI 1.65.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E81-S1`  
基线：`4a9a1fa`（全文 `4a9a1fa728fc13d912c39bfd60fd183ce3a3c281`；含 E81 design；E80 tip `f929dc8` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e81-project-milestones-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e81-project-milestones-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ⏳ | issue_count + status filter；删靠 FK SET NULL |
| B FE | ⏳ | 占用列 + formatMilestoneIssueCount |
| C CLI 1.65.0 | ⏳ | project milestone * + issue create/list --milestone |
| D 安全/邻面/no-emit | ⏳ | 不改 E80 helper；无新 webhook；formula no-emit |
| E 门禁 | ⏳ | 见下 |

## Tip

- 分支：`sprint/E81-S1`
- tip short：_pending_
- tip full：_pending_
- **未 push / 未开 PR / 未开 E82**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E81 BE | _pending_ |
| Full BE `pytest tests` | _pending_ |
| CLI suite | _pending_ |
| FE vitest | _pending_ |
| FE production build | _pending_ |
| VERSION | _pending_ |

## Q1a–Q6a 落地

- Q1a serialize 均带 issue_count
- Q2a list `?status=planned|done`
- Q3a 删靠 FK SET NULL；无新 timeline/webhook
- Q4a CLI 允许 milestone delete
- Q5a `project milestone …` 子组
- Q6a issue create/list `--milestone` + pins 1.65.0

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E82
