# E94 Acceptance：Issue Reactions CLI mid · CLI 1.78.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E94-S1`  
基线：`d84cba2`（全文 `d84cba2969e393bb0766624a13fcfdbdd8d39ce1`；含 E94 design；E93 tip `577f13d` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e94-issue-reactions-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e94-issue-reactions-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | Q1a **无新路由**；复用既有 Issue/Comment reactions 六端点（GET/POST/DELETE）；`test_notif_prefs_reactions` comment reactions smoke 绿；邻面 spy 绿；**无**新 initiative `/health`；**未改** E93 display-prefs / E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / project-health / cycle / project-watchers / issue-template / milestone / `issue_project_move` / E79 roster / notif prefs / threading |
| B FE | ✅ | **零产品 FE**；vitest smoke；production build ok；elegant-router `/f/:token`+`/r/:token` 保留（build 冲掉 imports/typings → **已 checkout 恢复**；WT 干净） |
| C CLI 1.78.0 | ✅ | 扁平组 `issue reaction list\|add\|remove` + `issue comment-reaction list\|add\|remove`（`rm` 别名）；api_client 六 helpers → GET/POST `{emoji}` / DELETE `?emoji=`；human 薄表 emoji/count（issue）与 emoji/userIds（comment）；add/remove 薄回显；缺 `--emoji` 本地失败不打 BE；**不**改 `issue show` / `issue comment` / attachment；pins：`VERSION` + pyproject + setup + `__init__` + `opentask_cli.VERSION` = **1.78.0**；历史 epic 断言级联 |
| D 安全/邻面/no-emit | ✅ | 未改 E93 display-prefs / E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 integrity / E79 roster；无新表 / 无 alembic / 无新 webhook / **无新 BE 路由**；formula no-emit；无 Activity Push / 无门户 / 无甘特；**未做** Initiative health CLI / 甘特 / bulk project_id / watching filter / notif prefs / threading；**未停** 7377/9527 |
| E 门禁 | ✅ | 见下 |

## Tip

- 分支：`sprint/E94-S1`
- tip short：774b117
- tip full：774b11774fb9c5122bf83057d823c774a6e5d9fc
- **未 push / 未开 PR / 未开 E95**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E94 BE `tests/api/test_e94_issue_reactions_cli_mid.py` + `test_notif_prefs_reactions.py` | **12 passed**（E94 spy 5 + notif/reactions smoke 7） |
| Full BE `pytest tests` | **1444 passed**, 24 skipped, **1 failed**（known flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` — order pollution；不阻塞） |
| CLI suite | **794 passed**, 89 skipped（含 directed E94 **24 passed**） |
| FE vitest | **427 passed**（63 files） |
| FE production build | **ok**（elegant-router `f`+`r` 在位；build 冲掉 imports → 已 checkout 恢复；WT 干净） |
| VERSION | `agent-harness/opentask-cli/VERSION` = **1.78.0** |

## Q1a–Q6a 落地

- Q1a 不新增 BE 路由；复用既有六端点 Issue + Comment reactions
- Q2a CLI 扁平 `issue reaction list|add|remove` + `issue comment-reaction list|add|remove`（主测扁平；`rm` 别名）
- Q3a api_client POST `{ "emoji": <str> }`；DELETE query `emoji=`
- Q4a human 薄表 emoji/count 或 emoji/userIds；add/remove 薄回显；**不**改 `issue show` / FE
- Q5a pins **1.78.0**（VERSION + pyproject + setup + `__init__` + `opentask_cli.VERSION`；历史 epic 断言级联）
- Q6a 零产品 FE

## superpowers

`superpowers: design/plan/TDD/verify/acceptance = ok`

## 禁区

未触碰：E93 display-prefs / E92 saved-view-write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead；无新表/alembic/webhook/BE 路由；formula no-emit；无 Activity Push / 无门户 / 无甘特；**未做** Initiative health CLI / 甘特 / bulk project_id / watching filter / notif prefs / threading；**未改** `issue show` / `issue comment`；**未停** 7377/9527；WT 干净；未 push / 未开 PR / 未自开 E95。

## 未做 / flake

- 未做：Activity Push / 门户 / 甘特 / Initiative health CLI / bulk project_id / `project list --watching` / notif prefs / threading / E95
- flake：`test_user_search`（已知，不阻塞）
