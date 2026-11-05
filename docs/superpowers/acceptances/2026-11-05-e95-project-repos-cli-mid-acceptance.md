# E95 Acceptance：Project Repos CLI mid · CLI 1.79.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E95-S1`  
基线：`490bf30`（全文 `490bf30ccfaca44c28624f82eb951ea5dd0789f6`；含 E95 design；E94 tip `315d459` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e95-project-repos-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e95-project-repos-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | Q1a **无新路由**；复用既有 project repos 五端点（GET/POST/PUT/DELETE）；`TestRepoConfigCRUD` 5 绿；邻面 spy 绿；**无**新 initiative `/health`；**未改** E94 reactions / E93 display-prefs / E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / project-health / cycle / project-watchers / issue-template / milestone / `issue_project_move` / E79 roster；**未改** requirement-repos |
| B FE | ✅ | **零产品 FE**；vitest smoke；production build ok；elegant-router `/f/:token`+`/r/:token` 保留（build 冲掉 imports/typings → **已 checkout 恢复**；WT 干净） |
| C CLI 1.79.0 | ✅ | 子组 `project repo list\|show\|add\|update\|remove`（`rm` 别名）；api_client 五 helpers → GET/POST（body 含 `project_id`）/PUT/DELETE；human 薄表 id/name/url/main_branch；add/update/remove 薄回显；缺 `--name`/`--url` 与 update 无 flag 本地失败不打 BE；`main_branch` 默认 `main`；**不**改 `project show` / milestone / health / lead / member；pins：`VERSION` + pyproject + setup + `__init__` + `opentask_cli.VERSION` = **1.79.0**；历史 epic 断言级联 |
| D 安全/邻面/no-emit | ✅ | 未改 E94 reactions / E93 display-prefs / E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 integrity / E79 roster；无新表 / 无 alembic / 无新 webhook / **无新 BE 路由**；formula no-emit；无 Activity Push / 无门户 / 无甘特；**未做** Initiative health CLI / 甘特 / bulk project_id / watching filter / requirement-repos / 真 Git；**未停** 7377/9527 |
| E 门禁 | ✅ | 见下 |

## Tip

- 分支：`sprint/E95-S1`
- tip short：fea58a6
- tip full：fea58a6f2e6d7e17edffaeeab5840af52ec458c2
- **未 push / 未开 PR / 未开 E96**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E95 BE `tests/api/test_e95_project_repos_cli_mid.py` + `TestRepoConfigCRUD` | **11 passed**（E95 spy 6 + RepoConfigCRUD 5） |
| Full BE `pytest tests` | **1450 passed**, 24 skipped, **1 failed**（known flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` — order pollution；不阻塞） |
| CLI suite | **816 passed**, 89 skipped（含 directed E95 **22 passed**） |
| FE vitest | **427 passed**（63 files） |
| FE production build | **ok**（elegant-router `f`+`r` 在位；build 冲掉 imports → 已 checkout 恢复；WT 干净） |
| VERSION | `agent-harness/opentask-cli/VERSION` = **1.79.0** |

## Q1a–Q6a 落地

- Q1a 不新增 BE 路由；复用既有五端点 project repos CRUD（GET/POST/PUT/DELETE）
- Q2a CLI `project repo list|show|add|update|remove`（`rm` 别名；挂既有 `project` 子组）
- Q3a api_client create body `{name,url,main_branch,project_id}`；update 用 **PUT** 仅提供字段
- Q4a human 薄表 id/name/url/main_branch；add/update/remove 薄回显；**不**改 `project show` / FE
- Q5a pins **1.79.0**（VERSION + pyproject + setup + `__init__` + `opentask_cli.VERSION`；历史 epic 断言级联）
- Q6a 零产品 FE

## superpowers

`superpowers: design/plan/TDD/verify/acceptance = ok`

## 禁区

未触碰：E94 reactions / E93 display-prefs / E92 saved-view-write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead；无新表/alembic/webhook/BE 路由；formula no-emit；无 Activity Push / 无门户 / 无甘特；**未做** Initiative health CLI / 甘特 / bulk project_id / watching filter / requirement-repos / `/api/repositories/*/git/*` 真 Git；**未改** `project show`；**未停** 7377/9527；WT 干净；未 push / 未开 PR / 未自开 E96。

## 未做 / flake

- 未做：Activity Push / 门户 / 甘特 / Initiative health CLI / bulk project_id / `project list --watching` / requirement-repos / 真 Git clone·commit·PR / E96
- flake：`test_user_search`（已知，不阻塞）
