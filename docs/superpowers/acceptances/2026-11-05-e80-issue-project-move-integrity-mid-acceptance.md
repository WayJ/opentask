# E80 Acceptance：Issue project-move integrity mid · CLI 1.64.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E80-S1`  
基线：`171ae4f`（全文 `171ae4ff5e31ee8336da2e22ed146060f4ccbc6a`；含 E80 design；E79 tip `d84f6e4` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e80-issue-project-move-integrity-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e80-issue-project-move-integrity-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | `issue_project_move.apply_project_move_integrity` + `milestone_for_duplicate`；`update_issue` 值变自清 milestone（显式合法保留 / 非法 400）；timeline `project_changed.action_data` 扩 `milestone_cleared`+`milestone_from`；duplicate 跨项目不抄 milestone；不清 cycle；viewer 对 project/milestone 字段 403；无新 webhook 名；formula no-emit |
| B FE | ✅ | `nextMilestoneAfterProjectMove` + `projectMoveClearedMessage`；详情 `saveProject` 清本地 milestone、`loadMilestones(new)`、轻提示；vitest；elegant-router `/f/:token`+`/r/:token` 保留 |
| C CLI 1.64.0 | ✅ | `issue update --project`（空串清）+ `--milestone` / `--clear-milestone`（互斥）；json/verbose 可见 project_id+milestone_id；pins：`agent-harness/opentask-cli/VERSION` + pyproject + setup + `__init__` + `opentask_cli.VERSION` = **1.64.0** |
| D 安全/邻面/no-emit | ✅ | 不清 cycle；未改 E79 lead/members / E78 parent / E77 trash 主表面；E75 duplicate 仅修跨项目 milestone 边；未改 E70 childProgress / E72 template；无 Activity Push / 无门户 / 无甘特；formula no-emit |
| E 门禁 | ✅ | 见下 |

## Tip

- 分支：`sprint/E80-S1`
- tip short：`23d2245`
- tip full：`23d224557cd5f981679f6fd358e36756c51723d1`
- **未 push / 未开 PR / 未开 E81**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E80 BE `tests/api/test_e80_issue_project_move.py` + `tests/services/test_issue_project_move.py` | **19 passed**（API 9 + helper 10） |
| Full BE `pytest tests` | **1376 passed**, 24 skipped, **1 failed**（known flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` — order pollution；不阻塞） |
| CLI suite | **625 passed**, 89 skipped（含 directed E80 **7 passed**） |
| FE vitest | **420 passed** |
| FE production build | **ok**（elegant-router `f`+`r` 在位；build 仅 warn 目录名） |
| VERSION | `agent-harness/opentask-cli/VERSION` = **1.64.0** |

## Q1a–Q6a 落地

- Q1a 任意 `project_id` 值变化即清 milestone（除非 Q2a）
- Q2a 同请求显式合法 milestone → 保留；非法 → 400
- Q3a duplicate 跨项目（或目标非法）不抄 source milestone；同项目仍抄
- Q4a 读不改库
- Q5a 扩 `project_changed.action_data`；无新 enum / 无新 webhook 名
- Q6a CLI + pins 1.64.0

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E81
