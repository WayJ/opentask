# E87 Acceptance：Tag Group CLI mid · CLI 1.71.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E87-S1`  
基线：`efd94ba`（全文 `efd94ba9589d565642f0785df4762a3f7c487030`；含 E87 design；E86 tip `a353f82` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e87-tag-group-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e87-tag-group-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ⏳ | Q1a 无新路由；复用 `/api/tag-groups` + tags `group_id` |
| B FE | ⏳ | 零产品 FE；build + f+r |
| C CLI 1.71.0 | ⏳ | `label group list\|create\|update\|delete` + list/create `--group-id` + update `--group-id` str |
| D 安全/邻面/no-emit | ⏳ | 不重开 E86 set/multi（除 group-id 类型）/ E85–E79；无新表/webhook/路由；formula no-emit |
| E 门禁 | ⏳ | 待跑 |

## Tip

- 分支：`sprint/E87-S1`
- tip short：_pending_
- tip full：_pending_
- **未 push / 未开 PR / 未开 E88**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E87 BE | _pending_ |
| Full BE `pytest tests` | _pending_ |
| CLI suite | _pending_ |
| FE vitest | _pending_ |
| FE production build | _pending_ |
| VERSION | _pending_ → **1.71.0** |

## Q1a–Q6a 落地

- Q1a 不新增 BE 路由；复用 `/api/tag-groups` + tags `group_id`
- Q2a CLI `label group list|create|update|delete`
- Q3a `label update --group-id` → str UUID；保留 `--clear-group`
- Q4a `label list --group-id` + `label create --group-id`
- Q5a pins **1.71.0**
- Q6a 零产品 FE

## superpowers

`superpowers: design/plan/TDD/verify/acceptance = pending`

## 禁区

未触碰：E86 set/multi 主语义（仅 group-id 类型对齐）/ E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead；无新表/alembic/webhook/BE 路由；formula no-emit；无 Activity Push / 无门户 / 无甘特；未 push / 未开 PR / 未自开 E88。
