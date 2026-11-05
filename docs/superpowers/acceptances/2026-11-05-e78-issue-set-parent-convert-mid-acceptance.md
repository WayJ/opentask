# E78 Acceptance：Issue 父子转换 mid — set-parent / convert · CLI 1.62.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E78-S1`  
基线：`d2e30be`（全文 `d2e30bea3bf5a1aef9c2339419b2be7086a5a527`；含 E78 design；E77 tip `04d5118` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e78-issue-set-parent-convert-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e78-issue-set-parent-convert-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ⏳ | Q1a PUT parent_issue_id；Q2a null 清父；Q3a 软删父 400；timeline `parent_changed`；无新表；无新 webhook 名；不改 childProgress |
| B FE | ⏳ | 设为子项 / 更换父 / 提升为根；vitest+build；`f`+`r` |
| C CLI 1.62.0 | ⏳ | `issue parent set\|clear`；全钉 1.62.0 |
| D 安全/邻面/no-emit | ⏳ | 跨租户；viewer 403；不重开 E63–E77；formula no-emit |
| E 门禁 | ⏳ | 见下 |

## ADR

D1–D6 / Q1a–Q6a 按 design 落地。

## 门禁

（verify 后填写）

## Tip

（verify 后填写）

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`（verify 后确认）

**STOP** — 未 push / 未开 PR / 未开 E79
