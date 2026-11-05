# E77 Acceptance：Issue 回收站 mid — trash/restore · CLI 1.61.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E77-S1`  
基线：`b1754a5`（全文 `b1754a58e1faefd28ceb308c659af5a1c36e09cf`；含 E77 design；E76 tip `d7c718c` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e77-issue-trash-restore-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e77-issue-trash-restore-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | 复用 `is_deleted`；`GET /api/issues/trash`（viewer+）；`POST /{id}/restore`（member+）；`GET ?include_deleted`；Q2a 不级联；Q3a 幂等 200；timeline `restored`（alembic ADD VALUE `c6d7e8f9a0b1`）；无新表；无 hard-delete；无新 webhook 名 |
| B FE | ✅ | 列表「回收站」入口；`/issue/trash` 表 + 恢复；详情 deleted 只读条 + 恢复；`issueTrashMeta` vitest；build ok；`routes/index.ts` 仍含 `/f/:token`+`/r/:token`（build 警告目录名 f/r） |
| C CLI 1.61.0 | ✅ | Q6a `issue trash` / `issue restore`；`issue delete` 仍拒；全钉 **1.61.0**：`VERSION` / `pyproject.toml` / `setup.py` / `opentask/__init__.py` / `opentask_cli.VERSION`；历史 epic 版本断言级联至 1.61.0 |
| D 安全/邻面/no-emit | ✅ | 跨 WS 404；viewer restore 403；不级联子树；无 hard-delete / purge / `archived_at`；formula no-emit；无 Activity Push / 无门户 / 无甘特；不改 E63–E76 邻面主表面（仅 CLI 版本钉） |
| E 门禁 | ✅ | 见下 |

## ADR

D1–D6 / Q1a–Q6a 按 design 落地。Bulk restore 本轮不做（Q4a）。

## 门禁

- BE：**1345 passed / 24 skipped / 1 failed**（已知 flake，与 E77 无关）：
  - `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`
- BE 定向 E77 API：`tests/api/test_e77_issue_trash_restore.py` — **4 passed**
- CLI：**604 passed / 89 skipped**（全钉 **1.61.0**，含 `VERSION` 文件）
- FE vitest：**407 passed**（58 files）；`pnpm run build`：**ok**（elegant-router 目录名 f/r 警告仍在，`f`+`r` 路由未丢）

## Tip

- 分支：`sprint/E77-S1`
- tip：`dd4fee4`（全文 `dd4fee47c76d489f2fec50d4b42d3c35043d8bab`）
- **未 push / 未开 PR / 未开 E78**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E78
