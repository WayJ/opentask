# E81 Acceptance：Project milestones CLI mid · CLI 1.65.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E81-S1`  
基线：`4a9a1fa`（全文 `4a9a1fa728fc13d912c39bfd60fd183ce3a3c281`；含 E81 design；E80 tip `f929dc8` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e81-project-milestones-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e81-project-milestones-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | `serialize_milestone(..., issue_count=)` + `count_issues_by_milestone`；list 可选 `?status=planned|done`；删靠 FK `ON DELETE SET NULL`；跨项目 404；viewer 写 403；跨租户 404；**未改** E80 `issue_project_move.py` |
| B FE | ✅ | 项目详情里程碑表 **占用**列；`formatMilestoneIssueCount` + `milestoneDeleteConfirmText`（count>0 提示清空 N 个 Issue）；vitest；elegant-router `/f/:token`+`/r/:token` 保留；未重做 CRUD 页 |
| C CLI 1.65.0 | ✅ | `project milestone list|create|show|update|delete`（Q4a 允许删）；`issue create --milestone` + `issue list --milestone`/`__none__`；api_client CRUD helpers；pins：`agent-harness/opentask-cli/VERSION` + pyproject + setup + `__init__` + `opentask_cli.VERSION` = **1.65.0** |
| D 安全/邻面/no-emit | ✅ | 未改 E79 lead/members / E78 parent / E77 trash / E80 integrity 主表面；无新 webhook / 无新 timeline enum；formula no-emit；无 Activity Push / 无门户 / 无甘特 |
| E 门禁 | ✅ | 见下 |

## Tip

- 分支：`sprint/E81-S1`
- tip short：`d0fa3a6`
- tip full：`d0fa3a6d8be7fc8b0bd478245fb8c18526320fce`
- **未 push / 未开 PR / 未开 E82**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E81 BE `tests/api/test_e81_project_milestones.py` | **7 passed** |
| Full BE `pytest tests` | **1383 passed**, 24 skipped, **1 failed**（known flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` — order pollution；不阻塞） |
| CLI suite | **631 passed**, 89 skipped（含 directed E81 **6 passed**） |
| FE vitest | **424 passed** |
| FE production build | **ok**（elegant-router `f`+`r` 在位；build 仅 warn 目录名） |
| VERSION | `agent-harness/opentask-cli/VERSION` = **1.65.0** |

## Q1a–Q6a 落地

- Q1a serialize/list/get/create/update 均带 `issue_count`（同 project+workspace、非软删）
- Q2a list 可选 `?status=planned|done`；非法 400；省略=全部
- Q3a 删靠 FK SET NULL；无手写 bulk clear；无新 timeline/webhook
- Q4a CLI 允许 `project milestone delete`
- Q5a `project milestone …` 子组（对齐 lead/member）
- Q6a `issue create --milestone` + `issue list --milestone`/`__none__` + pins **1.65.0**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E82
