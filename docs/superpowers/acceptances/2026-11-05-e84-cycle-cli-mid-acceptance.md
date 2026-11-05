# E84 Acceptance：Cycle CLI mid · CLI 1.68.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E84-S1`  
基线：`02cd994`（全文 `02cd994c08ef1e8f1b59cf871538bd4060c2a849`；含 E84 design；E83 tip `f066e88` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e84-cycle-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e84-cycle-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | Q1a **无新路由**；复用 `POST /generate-upcoming` / `PATCH /{id}` / `DELETE /{id}`；既有 writer 403 / 跨租户·缺 cycle 404 / update / delete / generate-upcoming smoke 绿；邻面 spy 绿；**未改** project-watchers / issue-template / milestone / `issue_project_move` / E79 roster |
| B FE | ✅ | **零产品 FE**；vitest smoke；production build ok；elegant-router `/f/:token`+`/r/:token` 保留（build 曾冲掉 elegant imports/typings，已 checkout 恢复） |
| C CLI 1.68.0 | ✅ | 扁平 `cycle generate-upcoming\|update\|delete`；api_client `generate_upcoming_cycle` / `update_cycle` / `delete_cycle`；update PATCH partial（仅显式字段）；delete **无** `--yes`；pins：`VERSION` + pyproject + setup + `__init__` + `opentask_cli.VERSION` = **1.68.0**；历史 epic 断言级联；**未改** list/show/create/activate/complete/capacity |
| D 安全/邻面/no-emit | ✅ | 未改 E83 project-watchers / E82 issue-templates / E81 milestones / E80 integrity / E79 roster；无新表 / 无 alembic / 无新 webhook / **无新 BE 路由**；formula no-emit；无 Activity Push / 无门户 / 无甘特 |
| E 门禁 | ✅ | 见下 |

## Tip

- 分支：`sprint/E84-S1`
- tip short：`c634110`
- tip full：`c634110bce1aa00bd54e072dc0e08f39a2484e49`
- **未 push / 未开 PR / 未开 E85**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E84 BE `tests/api/test_e84_cycle_cli_mid.py` + `test_cycles.py` + `test_cycle_complete.py` | **23 passed**（E84 spy 3 + cycles/complete smoke 20） |
| Full BE `pytest tests` | **1397 passed**, 24 skipped, **1 failed**（known flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` — order pollution；不阻塞） |
| CLI suite | **655 passed**, 89 skipped（含 directed E84 **9 passed**） |
| FE vitest | **427 passed**（63 files） |
| FE production build | **ok**（elegant-router `f`+`r` 在位；build 曾冲掉 elegant imports/typings，已 checkout 恢复；build 仅 warn 目录名 `f`/`r`） |
| VERSION | `agent-harness/opentask-cli/VERSION` = **1.68.0** |

## Q1a–Q6a 落地

- Q1a 不新增 BE 路由；复用既有三端点
- Q2a CLI 扁平 `cycle generate-upcoming\|update\|delete`（挂既有 cycle 组）
- Q3a delete **不**强制 `--yes`（对齐 label/initiative）
- Q4a update 仅发送显式传入字段（PATCH partial）
- Q5a pins **1.68.0**
- Q6a 零产品 FE（cycles UI/api 已齐）

## 禁区

- 未 push / 未开 PR / 未自开 E85
- 未重开 E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead-members 主表面
- 无新表 / 无 alembic / 无新 webhook / 无新 BE 路由 / 无 Activity Push / 无门户 / 无甘特
- formula no-emit；E63 `f`+`r` 已恢复

## 未做 / flake

- 未做 Project health CLI（design runners-up → E85）
- 未做 Label `set`/multi-attach（runners-up）
- known flake：`test_user_search`（不阻塞）

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E85
