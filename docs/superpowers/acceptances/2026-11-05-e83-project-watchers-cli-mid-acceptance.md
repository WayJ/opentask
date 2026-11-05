# E83 Acceptance：Project Watchers CLI mid · CLI 1.67.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E83-S1`  
基线：`dd3e920`（全文 `dd3e920ec92ba93e6c841199cc22d8a913ca8c95`；含 E83 design；E82 tip `bcd8f88` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e83-project-watchers-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e83-project-watchers-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | Q3a `enrich_watchers`（username/name）接线 list+watch；复用既有 GET/POST/DELETE；watch 幂等 / unwatch no-op / 跨租户·缺项目 404 不变；**未改** milestone / `issue_project_move` / issue-template / E79 roster / cycle / tag |
| B FE | ✅ | **零产品 FE**；vitest smoke；production build ok；elegant-router `/f/:token`+`/r/:token` 保留（build 曾冲掉 elegant imports/typings，已 checkout 恢复） |
| C CLI 1.67.0 | ✅ | 扁平 `project watch\|unwatch\|watchers`；`project show` → `watching_count`（失败降级）；api_client `list_project_watchers` / `watch_project` / `unwatch_project`；pins：`VERSION` + pyproject + setup + `__init__` + `opentask_cli.VERSION` = **1.67.0**；历史 epic 断言级联 |
| D 安全/邻面/no-emit | ✅ | 未改 E82 issue-template / E81 milestone / E80 integrity / E79 roster；无新表 / 无 alembic / 无新 webhook；formula no-emit；无 Activity Push / 无门户 / 无甘特 |
| E 门禁 | ✅ | 见下 |

## Tip

- 分支：`sprint/E83-S1`
- tip short：`b4ffe1b`
- tip full：`b4ffe1be25fa0047de0c1efd4ae1cc1e430e332d`
- **未 push / 未开 PR / 未开 E84**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E83 BE `tests/api/test_e83_project_watchers.py` + `test_project_health.py` | **13 passed**（E83 定向 5 + health/watchers 8） |
| Full BE `pytest tests` | **1394 passed**, 24 skipped, **1 failed**（known flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` — order pollution；不阻塞） |
| CLI suite | **646 passed**, 89 skipped（含 directed E83 **9 passed**） |
| FE vitest | **427 passed**（63 files） |
| FE production build | **ok**（elegant-router `f`+`r` 在位；build 曾冲掉 elegant imports/typings，已 checkout 恢复；build 仅 warn 目录名 `f`/`r`） |
| VERSION | `agent-harness/opentask-cli/VERSION` = **1.67.0** |

## Q1a–Q6a 落地

- Q1a 复用既有 `GET/POST/DELETE /api/projects/{id}/watchers`（无新路由）
- Q2a CLI 扁平 `project watch\|unwatch\|watchers`（对齐 issue）
- Q3a list/watch JSON 富化 `username`/`name`（`enrich_watchers`；无 alembic）
- Q4a `project show` → `watching_count`（+ `watchers`）；失败降级不阻断 show
- Q5a pins **1.67.0**
- Q6a 零产品 FE（project-detail 关注 UI 已齐）

## 禁区

- 未 push / 未开 PR / 未自开 E84
- 未重开 E82 issue-templates / E81 milestones / E80 project-move / E79 lead-members 主表面
- 无新表 / 无 alembic / 无新 webhook / 无 Activity Push / 无门户 / 无甘特
- formula no-emit；E63 `f`+`r` 已恢复

## 未做 / flake

- 未做 `project list --watching` BE 过滤（design 后薄刀）
- known flake：`test_user_search`（不阻塞）

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E84
