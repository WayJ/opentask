# E73 Acceptance：Issue start_date mid — 计划开始日 · CLI 1.57.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E73-S1`  
基线：`be2a150`（全文 `be2a150b212cc76379423405584947c86cc0e7ee`；含 E73 design；E72 实现 tip `6911e71` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e73-issue-start-date-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e73-issue-start-date-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A 数据/BE | ✅ | alembic `issues.start_date` + `timeline_action.start_date_changed`；Create/Update/Response；Q1a start>due→400（同日 OK）；`start_before`/`start_after`；`sort=start_date`；audit `start_date_changed`；**不**改 `started_at` 自动戳 |
| B Timeline/FE | ✅ | 详情「开始」EditableField 邻 due；`issueTimelinePlacement` 双端→bar / 仅 due→dot；vitest；build ok；elegant-router 误删 `f`+`r` 类型/imports 已还原；`routes/index.ts` 仍含 `/f/:token`+`/r/:token` |
| C CLI 1.57.0 | ✅ | Q6a create/update `--start-date`；show Start/Due；list `--start-before/--start-after`；全钉 **1.57.0**：`VERSION` / `pyproject.toml` / `setup.py` / `opentask/__init__.py` / `opentask_cli.VERSION`；历史 epic 版本断言级联至 1.57.0 |
| D 安全/邻面/no-emit | ✅ | Q5a 无新 webhook 事件名（走 `issue.updated`）；formula 不把 start_date 列入 attrs；纯改 start **不**触发 due_date_changed notif；不改 E63–E72 邻面主表面（仅 CLI 版本钉）；无 CSV（Q2a）；无 Activity Push / 无门户 / 无甘特大图 / 无模板再开 |
| E 租户隔离 | ✅ | 既有成员校验 / workspace 隔离路径不变 |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：**1303 passed / 24 skipped / 1 failed**（已知 flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`，与 E73 无关）
- BE 定向 E73 unit+API：**13 passed**
- CLI：**590 passed / 89 skipped**（全钉 **1.57.0**，含 `VERSION` 文件）
- FE vitest：**391 passed**（54 files）；`pnpm run build`：**ok**（elegant-router 误删 f/r 已还原）

## Tip

- 分支：`sprint/E73-S1`
- tip：`262c13f`（全文 `262c13f7d6f25a01f1a4f3bdd2fd37d00f8f4792`）
- **未 push / 未开 PR / 未开 E74**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E74
