# E92 Acceptance：Saved View Write CLI mid · CLI 1.76.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E92-S1`  
基线：`4df134a`（全文 `4df134a776dfc629c080091b73eefd4bf461f5f0`；含 E92 design；E91 tip `6acec05` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e92-saved-view-write-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e92-saved-view-write-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | Q1a **无新路由**；复用既有 POST/PATCH/DELETE `/api/saved-views…` + `POST /{id}/favorite` + `POST /{id}/save-as`；请求体 **snake_case** `is_favorite`/`is_shared`/`filter`…；既有 `test_saved_views` smoke 绿（create/update/favorite/shared ACL/save-as/跨 WS；共享 favorite→403）；邻面 spy 绿；**无**新 initiative `/health`；**未改** E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / project-health / cycle / project-watchers / issue-template / milestone / `issue_project_move` / E79 roster |
| B FE | ✅ | **零产品 FE**；vitest smoke；production build ok；elegant-router `/f/:token`+`/r/:token` 保留（build 曾冲掉 elegant imports/typings/components.d.ts，已 checkout 恢复） |
| C CLI 1.76.0 | ✅ | `view create|update|delete|favorite|save-as`；保留 `list|show|use`；api_client 五 helpers → POST/PATCH/DELETE + snake_case（禁 camelCase `isFavorite`/`isShared` 请求键）；list/show 人类表薄补 **Favorite/Shared**；**未改** `view use`；pins：`VERSION` + pyproject + setup + `__init__` + `opentask_cli.VERSION` = **1.76.0**；历史 epic 断言级联 |
| D 安全/邻面/no-emit | ✅ | 未改 E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 integrity / E79 roster；无新表 / 无 alembic / 无新 webhook / **无新 BE 路由**；formula no-emit；无 Activity Push / 无门户 / 无甘特；**未做** Initiative health CLI / 甘特 / Display prefs / bulk project_id |
| E 门禁 | ✅ | 见下 |

## Tip

- 分支：`sprint/E92-S1`
- tip short：6324f5c
- tip full：6324f5c51efc79cfc051f5942320ca742693e52a
- **未 push / 未开 PR / 未开 E93**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E92 BE `tests/api/test_e92_saved_view_write_cli_mid.py` + `test_saved_views.py` | **21 passed**（E92 spy 6 + saved_views smoke 15） |
| Full BE `pytest tests` | **1431 passed**, 27 skipped, **1 failed**（known flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` — order pollution；不阻塞） |
| CLI suite | **756 passed**, 89 skipped（含 directed E92 **19 passed**） |
| FE vitest | **427 passed**（63 files） |
| FE production build | **ok**（elegant-router `f`+`r` 在位；build 曾冲掉 elegant imports/typings/components.d.ts，已 checkout 恢复；build 仅 warn 目录名 `f`/`r`） |
| VERSION | `agent-harness/opentask-cli/VERSION` = **1.76.0** |

## Q1a–Q6a 落地

- Q1a 不新增 BE 路由；复用既有 POST/PATCH/DELETE + favorite + save-as
- Q2a CLI 挂既有 `view` 组：`create|update|delete|favorite|save-as`；保留 `list|show|use`
- Q3a api_client 发 **snake_case** `is_favorite`/`is_shared`/`filter`（非 camelCase `isFavorite`/`isShared`）
- Q4a list/show 人类表薄补 Favorite/Shared；**不**改 `view use`
- Q5a pins **1.76.0**（VERSION + pyproject + setup + `__init__` + `opentask_cli.VERSION`；历史 epic 断言级联）
- Q6a 零产品 FE

## superpowers

`superpowers: design/plan/TDD/verify/acceptance = ok`

## 禁区

未触碰：E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead；无新表/alembic/webhook/BE 路由；formula no-emit；无 Activity Push / 无门户 / 无甘特；**未做** Initiative health CLI / 甘特 / Display prefs / bulk project_id；**未改** `view use`；未 push / 未开 PR / 未自开 E93。

## 未做 / flake

- 未做：Activity Push / 门户 / 甘特 / Initiative health CLI / Display prefs / bulk project_id / `project list --watching` / E93
- flake：`test_user_search`（已知，不阻塞）
