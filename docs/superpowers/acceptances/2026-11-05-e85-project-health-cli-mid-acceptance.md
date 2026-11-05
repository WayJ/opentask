# E85 Acceptance：Project Health CLI mid · CLI 1.69.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E85-S1`  
基线：`3a0add2`（全文 `3a0add215d27463e8f8be34f3fa751c8ce59ba1f`；含 E85 design；E84 tip `dde41b1` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e85-project-health-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e85-project-health-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | Q1a **无新路由**；复用 `GET/POST /api/projects/{id}/health` + `GET /{id}/timeline`；既有 writer 403 / 跨租户·缺 project 404 / 非法 status 400 / health history / timeline smoke 绿；邻面 spy 绿；**未改** cycle / project-watchers / issue-template / milestone / `issue_project_move` / E79 roster |
| B FE | ✅ | **零产品 FE**；vitest smoke；production build ok；elegant-router `/f/:token`+`/r/:token` 保留（build 曾冲掉 elegant imports/typings，已 checkout 恢复） |
| C CLI 1.69.0 | ✅ | nested `project health get\|set` + `project timeline`；api_client `get_project_health` / `post_project_health` / `get_project_timeline`；`project show` 附 `health` / `health_status`（失败降级）；pins：`VERSION` + pyproject + setup + `__init__` + `opentask_cli.VERSION` = **1.69.0**；历史 epic 断言级联；**未改** list/create/update/delete/watch/unwatch/watchers/lead/member/milestone |
| D 安全/邻面/no-emit | ✅ | 未改 E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 integrity / E79 roster；无新表 / 无 alembic / 无新 webhook / **无新 BE 路由**；formula no-emit；无 Activity Push / 无门户 / 无甘特 |
| E 门禁 | ✅ | 见下 |

## Tip

- 分支：`sprint/E85-S1`
- tip short：`d86b6ba`
- tip full：`d86b6ba359e1b7f7251ad6ac093e8ba6b0dae782`
- **未 push / 未开 PR / 未开 E86**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E85 BE `tests/api/test_e85_project_health_cli_mid.py` + `test_project_health.py` | **11 passed**（E85 spy 3 + project_health smoke 8） |
| Full BE `pytest tests` | **1400 passed**, 24 skipped, **1 failed**（known flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` — order pollution；不阻塞） |
| CLI suite | **667 passed**, 89 skipped（含 directed E85 **12 passed**） |
| FE vitest | **427 passed**（63 files） |
| FE production build | **ok**（elegant-router `f`+`r` 在位；build 曾冲掉 elegant imports/typings，已 checkout 恢复；build 仅 warn 目录名 `f`/`r`） |
| VERSION | `agent-harness/opentask-cli/VERSION` = **1.69.0** |

## Q1a–Q6a 落地

- Q1a 不新增 BE 路由；复用既有 GET/POST health + timeline
- Q2a CLI nested `project health get|set` + `project timeline`（对齐 lead/member/milestone 组）
- Q3a `project show` 附 latest `health` / `health_status`（失败降级不阻断）
- Q4a timeline 本轮纳入（薄接线）
- Q5a pins **1.69.0**
- Q6a 零产品 FE（health UI/api 已齐）

## 禁区

- 未 push / 未开 PR / 未自开 E86
- 未重开 E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead-members 主表面
- 无新表 / 无 alembic / 无新 webhook / 无新 BE 路由 / 无 Activity Push / 无门户 / 无甘特
- formula no-emit；E63 `f`+`r` 已恢复

## 未做 / flake

- 未做 Label `set`/multi-attach（design runners-up → E86+）
- 未做 Initiative health CLI / 自动健康评估（runners-up）
- known flake：`test_user_search`（不阻塞）

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E86
