# E97 Acceptance：Issue VCS unlink + update CLI mid · CLI 1.81.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E97-S1`  
基线：`0f6248c`（全文 `0f6248cb3ae695e6ab8ed5ebe0ea8429b53d4743`；含 E97 design；E96 tip `d864818` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e97-issue-vcs-unlink-update-cli-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e97-issue-vcs-unlink-update-cli-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | Q1a **无新路由**；复用既有 `DELETE/PATCH /api/issues/{id}/vcs/links/{link_id}`；`VcsLinkUpdate` camelCase 字段仍在；邻面 spy **6 passed**；**无**新 alembic/e97；**未改** E96 access-token / E95 project-repos / E94 reactions / E93 display-prefs / E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / project-health / cycle / project-watchers / issue-template / milestone / `issue_project_move` / E79 roster；未绑定 requirement-repos / 真 Git / OAuth2 |
| B FE | ✅ | **零产品 FE**；vitest **427 passed**（63 files）；production build ok；elegant-router `/f/:token`+`/r/:token` 保留（build 冲掉 imports/typings → **已 checkout 恢复**；E97 跟踪文件 WT 干净） |
| C CLI 1.81.0 | ✅ | 扁平 `issue unlink-vcs`（别名 `vcs-unlink`）+ `issue update-vcs`；api_client 接线既有 `delete_issue_vcs_link` + **新增** `update_issue_vcs_link` → PATCH camelCase（`branchName`/`prUrl`/`provider`/`externalId`/`status`/`title`）；空 update 本地非零退出、不发空 PATCH；human 薄回显 id/kind/status/url-or-branch；`--json` 全量；**保留**既有 `branch-name`/`link-branch`/`link-pr`/`vcs-links`；pins：`VERSION` + pyproject + setup + `__init__` + `opentask_cli.VERSION` = **1.81.0**；历史 epic 断言级联；directed **16 passed**；既有 `test_issue_vcs_commands` **5 passed** |
| D 安全/邻面/no-emit | ✅ | 未改 E79–E96 邻面；无新表 / 无 alembic / 无新 webhook / **无新 BE 路由**；formula no-emit；无 Activity Push / 无门户 / 无甘特；**未做** OAuth2 client CRUD / 真 Git / requirement-repos / Initiative health / bulk project_id / watching filter；**未停** 7377/9527 |
| E 门禁 | ✅ | 见下 |

## Tip

- 分支：`sprint/E97-S1`
- tip short：772cabb
- tip full：772cabb28c4c188669cac9f6cc13be94e33ba6c4
- **未 push / 未开 PR / 未开 E98**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E97 BE `tests/api/test_e97_issue_vcs_unlink_update_cli_mid.py` | **6 passed** |
| Directed E97 CLI `tests/test_e97_issue_vcs_unlink_update.py` | **16 passed** |
| Directed 既有 Issue VCS CLI `tests/test_issue_vcs_commands.py` | **5 passed** |
| Directed 既有 Issue VCS BE `tests/api/test_issue_vcs.py` (+ e97 spy) | **11 passed**（合跑） |
| Full BE `pytest tests` | **1462 passed**, 24 skipped, **1 failed**（known flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` — order pollution；不阻塞） |
| CLI suite | **852 passed**, 89 skipped（含 directed E97 **16 passed**） |
| FE vitest | **427 passed**（63 files） |
| FE production build | **ok**（elegant-router `f`+`r` 在位；build 冲掉 imports → 已 checkout 恢复） |
| VERSION | `agent-harness/opentask-cli/VERSION` = **1.81.0** |

## Q1a–Q6a 落地

- Q1a 不新增 BE 路由；复用既有 `DELETE` + `PATCH /api/issues/{id}/vcs/links/{link_id}`
- Q2a CLI 扁平 `issue unlink-vcs`（`vcs-unlink`）+ `issue update-vcs`；保留既有 branch-name/link-branch/link-pr/vcs-links；不强制 `issue vcs` 子组
- Q3a 既有 `delete_issue_vcs_link` 接线 CLI；新增 `update_issue_vcs_link` → PATCH + camelCase body；ISSUE_REF 经 `_resolve_issue_id`；空 update CLI 非零退出不发空 PATCH；status 文档示例 `open|draft|merged|closed|unknown`（透传 BE）
- Q4a human unlink/update 薄回显 id/kind/status/url-or-branch；`--json` 全量；不改 `issue show` 默认
- Q5a pins **1.81.0**（VERSION + pyproject + setup + `__init__` + `opentask_cli.VERSION`；历史 epic 断言级联）
- Q6a 零产品 FE

## superpowers

`superpowers: design/plan/TDD/verify/acceptance = ok`

## 禁区

未触碰：E96 access-token / E95 project-repos / E94 reactions / E93 display-prefs / E92 saved-view-write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead；**未改**既有 `branch-name`/`link-branch`/`link-pr`/`vcs-links` 默认语义；**未**重组 `issue vcs` 子组；无新表/alembic/webhook/BE 路由；formula no-emit；无 Activity Push / 无门户 / 无甘特；**未做** OAuth2 client CRUD / SSO / 真 Git / requirement-repos / Initiative health / bulk project_id / watching filter；**未停** 7377/9527；E97 跟踪文件 WT 干净；未 push / 未开 PR / 未自开 E98。

## 未做 / flake

- 未做：Activity Push / 门户 / 甘特 / Initiative health CLI / bulk project_id / `project list --watching` / OAuth2 client CRUD / 真 Git / requirement-repos / `issue vcs` 子组重组（Q2b）/ Issue comment update / E98
- flake：`tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`（已知，不阻塞）
- 注：工作区另有未跟踪 `docs/superpowers/specs/2026-11-05-e98-linear-issue-identifiers-design.md`（非本 Epic 产出；大软**未**打开/提交 E98）
