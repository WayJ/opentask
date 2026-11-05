# E91 Acceptance：Issue Board Move CLI mid · CLI 1.75.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E91-S1`  
基线：`651e3d8`（全文 `651e3d83e4fccfca96e1c79b4cbf0874faa47719`；含 E91 design；E90 tip `4b7f34d` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e91-issue-board-move-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e91-issue-board-move-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | Q1a **无新路由**；复用既有 **POST** `/api/issues/board/move` body **snake_case** `issue_id`/`status`/`position`/`ordered_ids?`；既有 `test_issue_board` smoke 绿（status+position / ordered_ids 重排 / 跨 WS 403）；邻面 spy 绿；**无**新 initiative `/health`；**未改** E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / project-health / cycle / project-watchers / issue-template / milestone / `issue_project_move` / E79 roster |
| B FE | ✅ | **零产品 FE**；vitest smoke；production build ok；elegant-router `/f/:token`+`/r/:token` 保留（build 曾冲掉 elegant imports/typings/components.d.ts，已 checkout 恢复） |
| C CLI 1.75.0 | ✅ | `issue board-move <issue_id> --status … --position N [--ordered-ids …]`；api_client `move_issue_on_board` → **POST** + **snake_case** body（禁 camelCase `issueId`/`orderedIds`）；`issue show` 人类表薄补 **Position**；**未**给 `issue update` 加 `--position`；pins：`VERSION` + pyproject + setup + `__init__` + `opentask_cli.VERSION` = **1.75.0**；历史 epic 断言级联；**未改** create/update/delete/bulk-update 默认行为 |
| D 安全/邻面/no-emit | ✅ | 未改 E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 integrity / E79 roster；无新表 / 无 alembic / 无新 webhook / **无新 BE 路由**；formula no-emit；无 Activity Push / 无门户 / 无甘特；**未做** Initiative health CLI / 甘特 / Saved View 全写 |
| E 门禁 | ✅ | 见下 |

## Tip

- 分支：`sprint/E91-S1`
- tip short：65d14f3
- tip full：65d14f3c2033249ff18953ffc4d8ec830998dccc
- **未 push / 未开 PR / 未开 E92**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E91 BE `tests/api/test_e91_issue_board_move_cli_mid.py` + `test_issue_board.py` | **11 passed**（E91 spy 6 + issue_board smoke 5） |
| Full BE `pytest tests` | **1425 passed**, 27 skipped, **1 failed**（known flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` — order pollution；不阻塞） |
| CLI suite | **737 passed**, 89 skipped（含 directed E91 **11 passed**） |
| FE vitest | **427 passed**（63 files） |
| FE production build | **ok**（elegant-router `f`+`r` 在位；build 曾冲掉 elegant imports/typings/components.d.ts，已 checkout 恢复；build 仅 warn 目录名 `f`/`r`） |
| VERSION | `agent-harness/opentask-cli/VERSION` = **1.75.0** |

## Q1a–Q6a 落地

- Q1a 不新增 BE 路由；复用 **POST** `/api/issues/board/move`
- Q2a CLI `issue board-move`（单命令，贴 `bulk-update`）
- Q3a api_client 发 **snake_case** `issue_id`/`status`/`position`/`ordered_ids`（非 camelCase `issueId`/`orderedIds`）
- Q4a **不**给 `issue update` 加 `--position`；`issue show` 人类表薄补 Position
- Q5a pins **1.75.0**（VERSION + pyproject + setup + `__init__` + `opentask_cli.VERSION`；历史 epic 断言级联）
- Q6a 零产品 FE

## superpowers

`superpowers: design/plan/TDD/verify/acceptance = ok`

## 禁区

未触碰：E90 initiative-projects / E89 CF reorder / E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead；无新表/alembic/webhook/BE 路由；formula no-emit；无 Activity Push / 无门户 / 无甘特；**未做** Initiative health CLI / 甘特 / Saved View 全写；**未**给 `issue update` 加 `--position`；未 push / 未开 PR / 未自开 E92。

## 未做 / flake

- 未做：Activity Push / 门户 / 甘特 / Initiative health CLI / Saved View 全写 / bulk project_id / `project list --watching` / E92
- flake：`test_user_search`（已知，不阻塞）
