# E77 Acceptance：Issue 回收站 mid — trash/restore · CLI 1.61.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E77-S1`  
基线：`b1754a5`（全文 `b1754a58e1faefd28ceb308c659af5a1c36e09cf`；含 E77 design；E76 tip `d7c718c` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e77-issue-trash-restore-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e77-issue-trash-restore-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ⏳ | trash list + restore；复用 `is_deleted`；timeline `restored`；无新表 |
| B FE | ⏳ | 回收站页 + 恢复；vitest+build；`f`+`r` |
| C CLI 1.61.0 | ⏳ | `issue trash` / `issue restore`；delete 仍拒；全钉 1.61.0 |
| D 安全/邻面/no-emit | ⏳ | viewer restore 403；不级联；无 hard-delete；无新 webhook；formula no-emit |
| E 门禁 | ⏳ | 见下 |

## ADR

D1–D6 / Q1a–Q6a 按 design 落地。

## 门禁

（verify 后填写）

## Tip

（verify 后填写）

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E78
