# E88 Acceptance：Favorite Reorder CLI mid · CLI 1.72.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E88-S1`  
基线：`34f151a`（全文 `34f151afee076a67644d368e92bb746c87448595`；含 E88 design；E87 tip `c82bc63` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e88-favorite-reorder-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e88-favorite-reorder-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ⏳ | Q1a **无新路由**；复用 `PUT /api/favorites/reorder`；既有 favorites smoke；邻面 spy |
| B FE | ⏳ | **零产品 FE**；vitest smoke；production build；`f`+`r` |
| C CLI 1.72.0 | ⏳ | `favorite reorder --ids …`（+位置参数）；list 露 position；api_client `reorder_favorites` → PUT；pins 1.72.0 |
| D 安全/邻面/no-emit | ⏳ | 未改 E87–E79 邻面；无新表/alembic/webhook/BE 路由；formula no-emit |
| E 门禁 | ⏳ | 见下 |

## Tip

- 分支：`sprint/E88-S1`
- tip short：_pending_
- tip full：_pending_
- **未 push / 未开 PR / 未开 E89**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E88 BE | _pending_ |
| Full BE `pytest tests` | _pending_ |
| CLI suite | _pending_ |
| FE vitest | _pending_ |
| FE production build | _pending_ |
| VERSION | _pending_ |

## Q1a–Q6a 落地

- Q1a 不新增 BE 路由；复用 `PUT /api/favorites/reorder`
- Q2a CLI `favorite reorder`
- Q3a `--ids` 为主；可兼位置参数
- Q4a `favorite list` 露 `position`
- Q5a pins **1.72.0**
- Q6a 零产品 FE

## superpowers

`superpowers: design/plan/TDD/verify/acceptance = pending`

## 禁区

未触碰：E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead；无新表/alembic/webhook/BE 路由；formula no-emit；无 Activity Push / 无门户 / 无甘特；未 push / 未开 PR / 未自开 E89。

## 未做 / flake

- 未做：Activity Push / 门户 / 甘特 / bulk project_id / `project list --watching` / custom-fields reorder / E89
- flake：_pending_
