# E72 Acceptance：Project 模板 mid — project_templates · CLI 1.56.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E72-S1`  
基线：`91bea39`（全文 `91bea3924df93461dad0da01736a1b0b97630111`；含 E72 design；E71 实现 tip `b95da6f` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e72-project-templates-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e72-project-templates-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A 表 + payload + apply/from-project | ✅ | Q1a payload `{description?, milestones:[{name, description?, position?, targetOffsetDays?}]}`；Q3a max 30；alembic `project_templates`；apply 按 base+offset 种子 Milestone；from-project 仅里程碑骨架；**0** Issues |
| B API CRUD + template_id create | ✅ | Q2a `POST /projects` 可选 `template_id` + `POST /api/project-templates/{id}/apply`；camelCase 列表 `{rows,total}`；跨 WS 404；viewer 写 403 |
| C FE 设置 + 创建选 + 另存 | ✅ | `/workspace/project-templates`；Projects 创建对话框模板下拉+里程碑预览；详情「另存为模板」；vitest offset/validate；elegant-router `f`+`r` 守 E31/E63（build 误删已还原） |
| D CLI 1.56.0（含 VERSION） | ✅ | Q6a `project-template` list/show/create/update/delete/apply/from-project；`project create --template-id`；全钉 **1.56.0**：`VERSION` / `pyproject.toml` / `setup.py` / `opentask/__init__.py` / `opentask_cli.VERSION` |
| E 安全 / no-emit / 邻面不动 | ✅ | Q5a 无新 webhook 事件名；formula no-emit；不改 E63–E71 邻面主表面（仅 CLI 版本钉）；不复制 Issues/附件/成员/watchers/health；无 Activity Push / 无门户再厚 / 无甘特 / 无多指派再开 |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：**1290 passed / 24 skipped / 1 failed**（已知 flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`，与 E72 无关）
- BE 定向 E72 API + payload unit：**12 passed**
- CLI：**585 passed / 89 skipped**（全钉 **1.56.0**，含 `VERSION` 文件）
- FE vitest：**385 passed**（54 files）；`pnpm run build`：**ok**（elegant-router 误删 f/r 已还原）

## Tip

- 分支：`sprint/E72-S1`
- tip：`bd65c80`（全文 `bd65c802438b69613a6c1cd723d5a39563216879`）
- **未 push / 未开 PR / 未开 E73**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E73
