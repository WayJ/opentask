# E89 Acceptance：Custom Fields Reorder CLI mid · CLI 1.73.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E89-S1`  
基线：`dc4779c`（全文 `dc4779c6de9d5dd892c25c76a9deea3466162888`；含 E89 design；E88 tip `d09142c` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e89-custom-fields-reorder-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e89-custom-fields-reorder-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | _pending_ | Q1a 无新路由；复用 POST `/api/custom-fields/reorder` body `orderedIds`；软更新语义 |
| B FE | _pending_ | 零产品 FE；vitest + build；`f`+`r` |
| C CLI 1.73.0 | _pending_ | `custom-field reorder`；api_client POST+`orderedIds`；pins 1.73.0 |
| D 安全/邻面/no-emit | _pending_ | 未改 E88–E79 邻面；无新表/路由/webhook；formula no-emit |
| E 门禁 | _pending_ | 见下 |

## Tip

- 分支：`sprint/E89-S1`
- tip short：_pending_
- tip full：_pending_
- **未 push / 未开 PR / 未开 E90**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E89 BE | _pending_ |
| Full BE `pytest tests` | _pending_ |
| CLI suite | _pending_ |
| FE vitest | _pending_ |
| FE production build | _pending_ |
| VERSION | _pending_ |

## Q1a–Q6a 落地

- Q1a 不新增 BE 路由；复用 `POST /api/custom-fields/reorder`（body `orderedIds`；非 PUT）
- Q2a CLI `custom-field reorder`
- Q3a `--ids ID1,ID2,...` 为主；可兼位置参数
- Q4a 不改 list（已有 Pos）
- Q5a pins **1.73.0**
- Q6a 零产品 FE

## superpowers

`superpowers: design/plan/TDD/verify/acceptance = _pending_`

## 禁区

未触碰：E88 favorite reorder / E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead；无新表/alembic/webhook/BE 路由；formula no-emit；无 Activity Push / 无门户 / 无甘特；未 push / 未开 PR / 未自开 E90。

## 未做 / flake

- 未做：Activity Push / 门户 / 甘特 / bulk project_id / `project list --watching` / E90
- flake：_pending_
