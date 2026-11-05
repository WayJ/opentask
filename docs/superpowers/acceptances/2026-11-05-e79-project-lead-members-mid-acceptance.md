# E79 Acceptance：Project lead + members mid · CLI 1.63.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E79-S1`  
基线：`c07f94b`（全文 `c07f94b87797155e7e0fd03ba693733c02ceb76a`；含 E79 design；E78 tip `6fe2b57` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e79-project-lead-members-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e79-project-lead-members-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | Alembic `e8f9a0b1c2d3`：`projects.lead_id` + `project_members`；PATCH/PUT `lead_id`；`GET/POST/DELETE /api/projects/{id}/members`；list slim `lead_id`+`member_count`；show full `lead`+`members[]`；Q3a set-lead upserts member / clear 保留 row；跨 WS user→400；viewer write→403；跨租户→404；无新 webhook；formula no-emit；users 离 WS 时序列化 null/skip |
| B FE | ✅ | Project detail Lead picker + Members add/remove；list `lead_id`/`member_count` typings；helper + vitest；**不**按 membership 隐藏项目；elegant-router `/f/:token`+`/r/:token` 保留 |
| C CLI 1.63.0 | ✅ | `project lead set\|clear` + `project member add\|remove\|list`；`--json`；pins：`agent-harness/opentask-cli/VERSION` + pyproject + setup + `__init__` = **1.63.0** |
| D 安全/邻面/no-emit | ✅ | roster-only：未改 WS/Issue ACL / 无私有项目；members ≠ `project_watchers`；未改 E72 template apply / 未写 lead 入模板；未重开 E63–E78 主表面；无 Activity Push / 无门户 / 无甘特；formula no-emit |
| E 门禁 | ✅ | 见下 |

## Tip

- 分支：`sprint/E79-S1`
- tip short：`c97d981`
- tip full：`c97d9817798ac6534601095b849a341f3864326f`
- **未 push / 未开 PR / 未开 E80**

## Gates（verification-before-completion）

| 门禁 | 结果 |
|------|------|
| Directed E79 BE `tests/api/test_e79_project_lead_members.py` | **6 passed** |
| Full BE `pytest tests` | **1357 passed**, 24 skipped, **1 failed**（known flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search` — order pollution；不阻塞） |
| SQLite curated fixtures | `test_data_scope` + `test_dept_snapshot` 补 `project_members` 后 **9 passed**（曾因缺表 OperationalError） |
| CLI suite | **618 passed**, 89 skipped（含 directed E79 **7 passed**） |
| FE vitest | **413 passed** |
| FE production build | **ok**（elegant-router `f`+`r` 在位） |
| VERSION | `agent-harness/opentask-cli/VERSION` = **1.63.0** |

## Q1a–Q6a 落地

- Q1a 单 `lead_id` FK-style VARCHAR NULL（无 `users` 表名 FK；同 `health_updated_by`）
- Q2a `project_members(project_id, user_id, role?, created_at)` unique `(project_id, user_id)`
- Q3a set lead → upsert member；clear lead → **不**删 member row
- Q4a list slim / show full
- Q5a 无新 webhook 事件名
- Q6a CLI + pins 1.63.0

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E80
