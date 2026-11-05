# E85 Acceptance：Project Health CLI mid · CLI 1.69.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E85-S1`  
基线：`3a0add2`（全文 `3a0add215d27463e8f8be34f3fa751c8ce59ba1f`；含 E85 design；E84 tip `dde41b1` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e85-project-health-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e85-project-health-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ⏳ | Q1a 无新路由；复用 GET/POST health + timeline |
| B FE | ⏳ | 零产品 FE；build + f+r |
| C CLI 1.69.0 | ⏳ | nested health get\|set + timeline + show 附 health |
| D 安全/邻面/no-emit | ⏳ | |
| E 门禁 | ⏳ | |

## Tip

- 分支：`sprint/E85-S1`
- tip short：_pending_
- tip full：_pending_
- **未 push / 未开 PR / 未开 E86**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E85 BE | _pending_ |
| Full BE `pytest tests` | _pending_ |
| CLI suite | _pending_ |
| FE vitest | _pending_ |
| FE production build | _pending_ |
| VERSION | _pending_ |

## Q1a–Q6a 落地

- Q1a 不新增 BE 路由；复用既有 GET/POST health + timeline
- Q2a nested `project health get|set` + `project timeline`
- Q3a `project show` 附 latest health / health_status（失败降级）
- Q4a timeline 本轮纳入
- Q5a pins **1.69.0**
- Q6a 零产品 FE

## 禁区

- 未 push / 未开 PR / 未自开 E86
- 未重开 E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead-members 主表面
- 无新表 / 无 alembic / 无新 webhook / 无新 BE 路由 / 无 Activity Push / 无门户 / 无甘特
- formula no-emit；E63 `f`+`r`

## 未做 / flake

- _pending_

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = pending`

**STOP** — 未 push / 未开 PR / 未开 E86
