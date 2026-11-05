# E90 Acceptance：Initiative Projects CLI mid · CLI 1.74.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E90-S1`  
基线：`a4dd51e`（全文 `a4dd51ecd8e9cbeb979df0073ee32e94a4804dac`；含 E90 design；E89 tip `d8337ea` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e90-initiative-projects-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e90-initiative-projects-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | Q1a **无新路由**；复用 `PUT /api/initiatives/{id}/projects` body **`projectIds`**（全集替换；`[]` 清空；未知/跨 WS → **400**）+ `POST …/projects/{project_id}` attach（幂等）+ `DELETE …/projects/{project_id}` detach；既有 initiatives smoke 绿（含 m2m projects）；邻面 spy 绿；**无**新 `/health`；**未改** E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / project-health / cycle / project-watchers / issue-template / milestone / `issue_project_move` / E79 roster / **E65 relations** |
| B FE | ✅ | **零产品 FE**；vitest smoke；production build ok；elegant-router `/f/:token`+`/r/:token` 保留（build 曾冲掉 elegant imports/typings，已 checkout 恢复） |
| C CLI 1.74.0 | ✅ | `initiative projects set --ids …`（空=清空；+位置参数兼容）+ `initiative project attach|detach`；api_client `set_initiative_projects` → **PUT** + **`projectIds`**；`attach_initiative_project` → **POST**；`detach_initiative_project` → **DELETE**；`initiative show` 人类表薄补 **Projects**；pins：`VERSION` + pyproject + setup + `__init__` + `opentask_cli.VERSION` = **1.74.0**；历史 epic 断言级联；**未改** create/update/delete/relations/relation 默认行为 |
| D 安全/邻面/no-emit | ✅ | 未改 E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 integrity / E79 roster / **E65 relations 主语义**；无新表 / 无 alembic / 无新 webhook / **无新 BE 路由**；formula no-emit；无 Activity Push / 无门户 / 无甘特；**未做** Initiative health CLI / 甘特 |
| E 门禁 | ✅ | 见下 |

## Tip

- 分支：`sprint/E90-S1`
- tip short：426138d
- tip full：426138d49eccc7cf58d50a3124f7e1f79555b0ba
- **未 push / 未开 PR / 未开 E91**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E90 BE `tests/api/test_e90_initiative_projects_cli_mid.py` + `test_initiatives.py` | **12 passed**（E90 spy 5 + initiatives smoke 7） |
| Full BE `pytest tests` | **1419 passed**, 27 skipped, **1 failed**（known flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` — order pollution；不阻塞） |
| CLI suite | **726 passed**, 89 skipped（含 directed E90 **14 passed**） |
| FE vitest | **427 passed**（63 files） |
| FE production build | **ok**（elegant-router `f`+`r` 在位；build 曾冲掉 elegant imports/typings，已 checkout 恢复；build 仅 warn 目录名 `f`/`r`） |
| VERSION | `agent-harness/opentask-cli/VERSION` = **1.74.0** |

## Q1a–Q6a 落地

- Q1a 不新增 BE 路由；复用 `PUT/POST/DELETE /api/initiatives/{id}/projects…`（body `projectIds`；非 `project_ids`）
- Q2a CLI `initiative projects set` + `initiative project attach|detach`
- Q3a `--ids ID1,ID2,...`（允许空=清空）；可兼位置参数
- Q4a `initiative show` 人类表薄补 Projects（json 已有 projects，未改逻辑）
- Q5a pins **1.74.0**（VERSION + pyproject + setup + `__init__` + `opentask_cli.VERSION`；历史 epic 断言级联）
- Q6a 零产品 FE

## superpowers

`superpowers: design/plan/TDD/verify/acceptance = ok`

## 禁区

未触碰：E89 CF reorder / E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead / **E65 relations 主语义**；无新表/alembic/webhook/BE 路由；formula no-emit；无 Activity Push / 无门户 / 无甘特；**未做** Initiative health CLI / 甘特；未 push / 未开 PR / 未自开 E91。

## 未做 / flake

- 未做：Activity Push / 门户 / 甘特 / Initiative health CLI / bulk project_id / `project list --watching` / E91
- flake：`test_user_search`（已知，不阻塞）
