# E88 Acceptance：Favorite Reorder CLI mid · CLI 1.72.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E88-S1`  
基线：`34f151a`（全文 `34f151afee076a67644d368e92bb746c87448595`；含 E88 design；E87 tip `c82bc63` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e88-favorite-reorder-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e88-favorite-reorder-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | Q1a **无新路由**；复用 `PUT /api/favorites/reorder`；既有 favorites smoke 绿（含 `test_favorites_reorder_by_ordered_ids`）；邻面 spy 绿；**未改** E87 tag-group / E86 set/multi / project-health / cycle / project-watchers / issue-template / milestone / `issue_project_move` / E79 roster |
| B FE | ✅ | **零产品 FE**；vitest smoke；production build ok；elegant-router `/f/:token`+`/r/:token` 保留（build 曾冲掉 elegant imports/typings，已 checkout 恢复） |
| C CLI 1.72.0 | ✅ | `favorite reorder --ids …`（+位置参数兼容）；`favorite list` 露 `position`；api_client `reorder_favorites` → **PUT** `/api/favorites/reorder`；pins：`VERSION` + pyproject + setup + `__init__` + `opentask_cli.VERSION` = **1.72.0**；历史 epic 断言级联；**未改** add/remove 默认行为 |
| D 安全/邻面/no-emit | ✅ | 未改 E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 integrity / E79 roster；无新表 / 无 alembic / 无新 webhook / **无新 BE 路由**；formula no-emit；无 Activity Push / 无门户 / 无甘特 |
| E 门禁 | ✅ | 见下 |

## Tip

- 分支：`sprint/E88-S1`
- tip short：955f213
- tip full：955f213bf91615ae595a8649d337a658128cff20
- **未 push / 未开 PR / 未开 E89**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E88 BE `tests/api/test_e88_favorite_reorder_cli_mid.py` + `test_favorites.py` | **13 passed**（E88 spy 4 + favorites smoke 9） |
| Full BE `pytest tests` | **1409 passed**, 27 skipped, **1 failed**（known flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` — order pollution；不阻塞） |
| CLI suite | **704 passed**, 89 skipped（含 directed E88 **9 passed**） |
| FE vitest | **427 passed**（63 files） |
| FE production build | **ok**（elegant-router `f`+`r` 在位；build 曾冲掉 elegant imports/typings，已 checkout 恢复；build 仅 warn 目录名 `f`/`r`） |
| VERSION | `agent-harness/opentask-cli/VERSION` = **1.72.0** |

## Q1a–Q6a 落地

- Q1a 不新增 BE 路由；复用 `PUT /api/favorites/reorder`（非 POST）
- Q2a CLI `favorite reorder`
- Q3a `--ids ID1,ID2,...` 为主；可兼位置参数
- Q4a `favorite list` human/json 露 `position`
- Q5a pins **1.72.0**（VERSION + pyproject + setup + `__init__` + `opentask_cli.VERSION`；历史 epic 断言级联）
- Q6a 零产品 FE

## superpowers

`superpowers: design/plan/TDD/verify/acceptance = ok`

## 禁区

未触碰：E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead；无新表/alembic/webhook/BE 路由；formula no-emit；无 Activity Push / 无门户 / 无甘特；未 push / 未开 PR / 未自开 E89。

## 未做 / flake

- 未做：Activity Push / 门户 / 甘特 / bulk project_id / `project list --watching` / custom-fields reorder / E89
- flake：`test_user_search`（已知，不阻塞）
