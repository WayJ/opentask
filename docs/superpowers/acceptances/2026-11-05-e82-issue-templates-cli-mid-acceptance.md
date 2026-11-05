# E82 Acceptance：Issue Templates CLI mid · CLI 1.66.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E82-S1`  
基线：`9e76efc`（全文 `9e76efc9641559a726fa86053e58b2bdc14e7acb`；含 E82 design；E81 tip `69b2112` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e82-issue-templates-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e82-issue-templates-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ⏳ | GET by id；既有 list/seed/CRUD 不变；viewer 写 403；跨租户 404 |
| B FE | ⏳ | Seed 按钮 + api + vitest；不重做 CRUD；`f`+`r` |
| C CLI 1.66.0 | ⏳ | `issue-template *` + `issue create --template-id`；pins 1.66.0 |
| D 安全/邻面/no-emit | ⏳ | 未改 E81/E80/E79/E72 主表面；无新 webhook；formula no-emit |
| E 门禁 | ⏳ | 见下 |

## Tip

- 分支：`sprint/E82-S1`
- tip short：_pending_
- tip full：_pending_
- **未 push / 未开 PR / 未开 E83**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E82 BE | _pending_ |
| Full BE `pytest tests` | _pending_ |
| CLI suite | _pending_ |
| FE vitest | _pending_ |
| FE production build | _pending_ |
| VERSION | _pending_ |

## Q1a–Q6a 落地

- Q1a GET by id
- Q2a 顶层 `issue-template`
- Q3a delete 允许含 seed
- Q4a CLI seed + FE 按钮
- Q5a `issue create --template-id` + pins 1.66.0
- Q6a FE seed 薄刀 + 薄 vitest

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = pending`

**STOP** — 未 push / 未开 PR / 未开 E83
