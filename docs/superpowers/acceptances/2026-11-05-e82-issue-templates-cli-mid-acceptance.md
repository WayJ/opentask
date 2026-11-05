# E82 Acceptance：Issue Templates CLI mid · CLI 1.66.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E82-S1`  
基线：`9e76efc`（全文 `9e76efc9641559a726fa86053e58b2bdc14e7acb`；含 E82 design；E81 tip `69b2112` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e82-issue-templates-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e82-issue-templates-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | `GET /api/issue-templates/{id}` → `serialize_issue_template`（复用 `IssueTemplateService.get`）；跨租户/缺失 404；viewer 读 200、写/seed 403；既有 list/seed/create/update/delete 行为不变；**未改** milestone / `issue_project_move` / E72 `project_template` 主表面 |
| B FE | ✅ | 工作区 Issue 模板页 **恢复内置** 按钮 → `fetchSeedIssueTemplates`（`POST /seed`）；`issueTemplateSourceLabel` + `issueTemplateSeedConfirmText` + vitest；elegant-router `/f/:token`+`/r/:token` 保留；未重做 CRUD 页 |
| C CLI 1.66.0 | ✅ | 顶层 `issue-template list\|show\|create\|update\|delete\|seed`（Q3a 允许删含 seed）；`issue create --template-id`；api_client CRUD+seed helpers + `create_issue(template_id=)`；pins：`VERSION` + pyproject + setup + `__init__` + `opentask_cli.VERSION` = **1.66.0**；历史 epic 断言级联 |
| D 安全/邻面/no-emit | ✅ | 未改 E81 milestone / E80 integrity / E79 roster / E72 project-template 语义；无新表 / 无 alembic / 无新 webhook；formula no-emit；无 Activity Push / 无门户 / 无甘特 |
| E 门禁 | ✅ | 见下 |

## Tip

- 分支：`sprint/E82-S1`
- tip short：`85d8bfc`
- tip full：`85d8bfc68ba32605ef95fac0edf2ab0c1bb151a5`
- **未 push / 未开 PR / 未开 E83**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E82 BE `tests/api/test_e82_issue_templates.py` + `test_issue_templates.py` | **14 passed**（E82 定向 6 + 既有 8） |
| Full BE `pytest tests` | **1389 passed**, 24 skipped, **1 failed**（known flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` — order pollution；不阻塞） |
| CLI suite | **637 passed**, 89 skipped（含 directed E82 **6 passed**） |
| FE vitest | **427 passed**（63 files） |
| FE production build | **ok**（elegant-router `f`+`r` 在位；build 仅 warn 目录名 `f`/`r`） |
| VERSION | `agent-harness/opentask-cli/VERSION` = **1.66.0** |

## Q1a–Q6a 落地

- Q1a BE `GET /api/issue-templates/{template_id}` → serialize；跨租户/缺失 404
- Q2a CLI 顶层组 `issue-template`（对齐 E72 `project-template`）
- Q3a delete 允许删 seed 与自定义（既有 API；不加 409）
- Q4a CLI `issue-template seed` + FE「恢复内置」→ `POST /seed`；`fetchSeedIssueTemplates`
- Q5a `issue create --template-id` + pins **1.66.0**
- Q6a FE 仅 seed 薄刀 + 薄 vitest；不重做 CRUD

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E83
