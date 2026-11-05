# E78 Acceptance：Issue 父子转换 mid — set-parent / convert · CLI 1.62.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E78-S1`  
基线：`d2e30be`（全文 `d2e30bea3bf5a1aef9c2339419b2be7086a5a527`；含 E78 design；E77 tip `04d5118` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e78-issue-set-parent-convert-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e78-issue-set-parent-convert-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | Q1a 复用 PUT `parent_issue_id`；Q2a JSON null 清父；Q3a 软删父 → 400「不能将已删除的 Issue 设为父」；timeline `parent_changed`（alembic ADD VALUE `d7e8f9a0b1c2`）；同值跳过 timeline；viewer 改 parent → 403；无新表；无新 webhook 名；未改 `child_progress.py` |
| B FE | ✅ | 详情「设为子项…」/「更换父」选择器 + 「提升为根」；`issueParentMeta` vitest；build ok；`routes/index.ts` 仍含 `/f/:token`+`/r/:token`（elegant-router 目录名 f/r 警告仍在） |
| C CLI 1.62.0 | ✅ | Q6a `issue parent set` / `issue parent clear`；全钉 **1.62.0**：`VERSION` / `pyproject.toml` / `setup.py` / `opentask/__init__.py` / `opentask_cli.VERSION`；历史 epic 版本断言级联至 1.62.0 |
| D 安全/邻面/no-emit | ✅ | 跨 WS 父 400；viewer parent 写 403；不改 E70 childProgress；不改 E74 comment `parent_id`；不重开 trash/links/duplicate 等邻面；formula no-emit；无 Activity Push / 无门户 / 无甘特 |
| E 门禁 | ✅ | 见下 |

## ADR

D1–D6 / Q1a–Q6a 按 design 落地。无 max-depth（Q5a）。无独立 `/set-parent` 端点（Q1a）。

## 门禁

- BE：**1351 passed / 24 skipped / 1 failed**（已知 flake，与 E78 无关）：
  - `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`
- BE 定向 E78 API：`tests/api/test_e78_issue_set_parent.py` — **6 passed**
- CLI：**611 passed / 89 skipped**（全钉 **1.62.0**，含 `VERSION` 文件）
- FE vitest：**410 passed**（59 files）；`pnpm run build`：**ok**（elegant-router 目录名 f/r 警告仍在，`f`+`r` 路由未丢）

## Tip

- 分支：`sprint/E78-S1`
- tip：`9d509c7`（全文 `9d509c76f35256ac065cf5766354aa5d3d1daf9a`）
- **未 push / 未开 PR / 未开 E79**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E79
