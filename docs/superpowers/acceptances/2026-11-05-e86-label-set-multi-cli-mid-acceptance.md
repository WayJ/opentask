# E86 Acceptance：Label Set/Multi CLI mid · CLI 1.70.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E86-S1`  
基线：`f8b1b27`（全文 `f8b1b27c806aa3b22688f8e6a34fc747aeee76df`；含 E86 design；E85 tip `5fa6e3b` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e86-label-set-multi-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e86-label-set-multi-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | Q1a **无新路由**；复用 `PUT /api/issues/{id}/tags` + `PATCH /api/tags/{id}` + POST/DELETE attach + GET issue tags；既有 tags smoke（create/list/patch/replace/viewer 403/跨 WS）绿；邻面 spy 绿；**未改** project-health / cycle / project-watchers / issue-template / milestone / `issue_project_move` / E79 roster |
| B FE | ✅ | **零产品 FE**；vitest smoke；production build ok；elegant-router `/f/:token`+`/r/:token` 保留（build 曾冲掉 elegant imports/typings，已 checkout 恢复） |
| C CLI 1.70.0 | ✅ | `label set`（`--ids` / `--clear`）+ `label update` + multi `--tag-id` attach/detach（位置参数兼容）+ 可选 `label issue`；api_client `replace_issue_tags` / `update_tag`；pins：`VERSION` + pyproject + setup + `__init__` + `opentask_cli.VERSION` = **1.70.0**；历史 epic 断言级联；**未改** `list|create|delete` 默认行为 |
| D 安全/邻面/no-emit | ✅ | 未改 E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 integrity / E79 roster；无新表 / 无 alembic / 无新 webhook / **无新 BE 路由**；formula no-emit；无 Activity Push / 无门户 / 无甘特 |
| E 门禁 | ✅ | 见下 |

## Tip

- 分支：`sprint/E86-S1`
- tip short：PENDING
- tip full：PENDING
- **未 push / 未开 PR / 未开 E87**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E86 BE `tests/api/test_e86_label_set_multi_cli_mid.py` + `test_tags.py` | **15 passed**（E86 spy 4 + tags smoke 11） |
| Full BE `pytest tests` | **1404 passed**, 24 skipped, **1 failed**（known flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` — order pollution；不阻塞） |
| CLI suite | **681 passed**, 89 skipped（含 directed E86 **14 passed**） |
| FE vitest | **427 passed**（63 files） |
| FE production build | **ok**（elegant-router `f`+`r` 在位；build 曾冲掉 elegant imports/typings，已 checkout 恢复；build 仅 warn 目录名 `f`/`r`） |
| VERSION | `agent-harness/opentask-cli/VERSION` = **1.70.0** |

## Q1a–Q6a 落地

- Q1a 不新增 BE 路由；复用 PUT replace + PATCH tag + 既有 attach/detach + GET
- Q2a CLI `label set` + `label update` + multi attach/detach
- Q3a `--ids ""` 或 `--clear` → PUT `tag_ids=[]` 清空
- Q4a 可重复 `--tag-id`；保留位置参数 `attach ISSUE TAG` / `detach ISSUE TAG` 兼容
- Q5a pins **1.70.0**
- Q6a 零产品 FE（replaceTags/UI 已齐）

## 禁区

- 未 push / 未开 PR / 未自开 E87
- 未重开 E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead-members 主表面
- 无新表 / 无 alembic / 无新 webhook / 无新 BE 路由 / 无 Activity Push / 无门户 / 无甘特
- formula no-emit；E63 `f`+`r` 已恢复

## 未做 / flake

- 未做 Tag group CLI 加厚（runners-up → E87+）
- 未做 Initiative health CLI / Activity Push / 门户 / 甘特（runners-up）
- known flake：`test_user_search`（不阻塞）

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E87
