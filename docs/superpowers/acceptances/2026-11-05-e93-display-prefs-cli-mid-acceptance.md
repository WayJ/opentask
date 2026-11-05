# E93 Acceptance：Display Prefs CLI mid · CLI 1.77.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E93-S1`  
基线：`4e818d2`（全文 `4e818d2aabe5c9324bd46f33d98174cdea90495a`；含 E93 design；E92 tip `48e6bb3` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e93-display-prefs-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e93-display-prefs-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | Q1a **无新路由**；复用既有 `GET/PUT /api/display-prefs/issue`（body `{display}`；display 内 **snake_case**）；既有 `test_display_prefs` smoke 绿（null when absent / roundtrip / 跨 WS / 422 / 不覆写 saved-view display）；邻面 spy 绿；**无**新 initiative `/health`；**未改** E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / project-health / cycle / project-watchers / issue-template / milestone / `issue_project_move` / E79 roster |
| B FE | ✅ | **零产品 FE**；vitest smoke；production build ok；elegant-router `/f/:token`+`/r/:token` 保留（build 仅 warn 目录名 `f`/`r`；未冲掉 elegant imports） |
| C CLI 1.77.0 | ✅ | 新组 `display-prefs get|set`；api_client `get_issue_display_prefs` + `put_issue_display_prefs(display)` → GET/PUT + `{display}`（禁 client 侧改写 camelCase `viewMode`）；human 薄摘要 View mode / Group by / Swimlane by / Hide empty lanes；非法 `--display` JSON / 非 object 本地失败不打 BE；缺 prefs → `display: null`；pins：`VERSION` + pyproject + setup + `__init__` + `opentask_cli.VERSION` = **1.77.0**；历史 epic 断言级联；**E49**「无专用子命令」→ 断言组存在 / version 1.77.0 |
| D 安全/邻面/no-emit | ✅ | 未改 E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 integrity / E79 roster；无新表 / 无 alembic / 无新 webhook / **无新 BE 路由**；formula no-emit；无 Activity Push / 无门户 / 无甘特；**未做** Initiative health CLI / 甘特 / bulk project_id / watching filter |
| E 门禁 | ✅ | 见下 |

## Tip

- 分支：`sprint/E93-S1`
- tip short：ce20542
- tip full：ce20542a673fca5cc80210ab3ec3acda27f1cd55
- **未 push / 未开 PR / 未开 E94**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E93 BE `tests/api/test_e93_display_prefs_cli_mid.py` + `test_display_prefs.py` | **11 passed**（E93 spy 5 + display_prefs smoke 6） |
| Full BE `pytest tests` | **1436 passed**, 27 skipped, **1 failed**（known flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` — order pollution；不阻塞） |
| CLI suite | **770 passed**, 89 skipped（含 directed E93 **14** + 更新后 E49 **3** = **17 passed**） |
| FE vitest | **427 passed**（63 files） |
| FE production build | **ok**（elegant-router `f`+`r` 在位；build 仅 warn 目录名 `f`/`r`） |
| VERSION | `agent-harness/opentask-cli/VERSION` = **1.77.0** |

## Q1a–Q6a 落地

- Q1a 不新增 BE 路由；复用既有 GET/PUT `/api/display-prefs/issue`
- Q2a CLI 新顶层组 `display-prefs get|set`
- Q3a api_client 发 `{ "display": <dict> }`，dict 内保持 **snake_case**（非 camelCase `viewMode`）
- Q4a human 薄摘要 view_mode/group_by/swimlane_by/hide_empty_lanes；`--json` 全量；**不**改 FE / `view use` / `issue list`
- Q5a pins **1.77.0**（VERSION + pyproject + setup + `__init__` + `opentask_cli.VERSION`；历史 epic 断言级联；E49 断言更新）
- Q6a 零产品 FE

## superpowers

`superpowers: design/plan/TDD/verify/acceptance = ok`

## 禁区

未触碰：E92 saved-view-write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead；无新表/alembic/webhook/BE 路由；formula no-emit；无 Activity Push / 无门户 / 无甘特；**未做** Initiative health CLI / 甘特 / bulk project_id / watching filter；**未改** `view use` / `view create|…` / `issue list`；E49 断言已更新；未 push / 未开 PR / 未自开 E94。

## 未做 / flake

- 未做：Activity Push / 门户 / 甘特 / Initiative health CLI / bulk project_id / `project list --watching` / E94
- flake：`test_user_search`（已知，不阻塞）
