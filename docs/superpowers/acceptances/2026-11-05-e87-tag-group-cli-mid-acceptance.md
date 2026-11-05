# E87 Acceptance：Tag Group CLI mid · CLI 1.71.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E87-S1`  
基线：`efd94ba`（全文 `efd94ba9589d565642f0785df4762a3f7c487030`；含 E87 design；E86 tip `a353f82` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e87-tag-group-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e87-tag-group-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | Q1a **无新路由**；复用 `GET/POST /api/tag-groups` + `PATCH/DELETE /api/tag-groups/{id}` + tags `group_id`；既有 tags smoke 绿；邻面 spy 绿；**未改** E86 set/multi 主语义以外 / project-health / cycle / project-watchers / issue-template / milestone / `issue_project_move` / E79 roster |
| B FE | ✅ | **零产品 FE**；vitest smoke；production build ok；elegant-router `/f/:token`+`/r/:token` 保留（build 曾冲掉 elegant imports/typings，已 checkout 恢复） |
| C CLI 1.71.0 | ✅ | `label group list|create|update|delete`；`label list --group-id` / `label create --group-id`；`label update --group-id` → **str UUID**（修 E86 int）；保留 `--clear-group`；api_client `list/create/update/delete_tag_group(s)`；pins：`VERSION` + pyproject + setup + `__init__` + `opentask_cli.VERSION` = **1.71.0**；历史 epic 断言级联；**未改** set/attach/detach/issue/delete 默认行为（除 group-id 类型） |
| D 安全/邻面/no-emit | ✅ | 未改 E86 set/multi 主语义（仅 group-id 类型）/ E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 integrity / E79 roster；无新表 / 无 alembic / 无新 webhook / **无新 BE 路由**；formula no-emit；无 Activity Push / 无门户 / 无甘特 |
| E 门禁 | ✅ | 见下 |

## Tip

- 分支：`sprint/E87-S1`
- tip short：150415f
- tip full：150415f362d8dc4bd804966d54022a0fa5899214
- **未 push / 未开 PR / 未开 E88**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E87 BE `tests/api/test_e87_tag_group_cli_mid.py` + `test_tags.py` | **15 passed**（E87 spy 4 + tags smoke 11） |
| Full BE `pytest tests` | **1405 passed**, 27 skipped, **1 failed**（known flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` — order pollution；不阻塞） |
| CLI suite | **695 passed**, 89 skipped（含 directed E87 **14 passed**） |
| FE vitest | **427 passed**（63 files） |
| FE production build | **ok**（elegant-router `f`+`r` 在位；build 曾冲掉 elegant imports/typings，已 checkout 恢复；build 仅 warn 目录名 `f`/`r`） |
| VERSION | `agent-harness/opentask-cli/VERSION` = **1.71.0** |

## Q1a–Q6a 落地

- Q1a 不新增 BE 路由；复用 `/api/tag-groups` + tags `group_id`
- Q2a CLI `label group list|create|update|delete`
- Q3a `label update --group-id` → str UUID；保留 `--clear-group`
- Q4a `label list --group-id` + `label create --group-id`
- Q5a pins **1.71.0**（VERSION + pyproject + setup + `__init__` + `opentask_cli.VERSION`；历史 epic 断言级联）
- Q6a 零产品 FE

## superpowers

`superpowers: design/plan/TDD/verify/acceptance = ok`

## 禁区

未触碰：E86 set/multi 主语义（仅 `--group-id` 类型对齐 str UUID）/ E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead；无新表/alembic/webhook/BE 路由；formula no-emit；无 Activity Push / 无门户 / 无甘特；未 push / 未开 PR / 未自开 E88。

## 未做 / flake

- 未做：Activity Push / 门户 / 甘特 / bulk project_id / `project list --watching` / Initiative health / E88
- flake：`test_user_search`（已知，不阻塞）
