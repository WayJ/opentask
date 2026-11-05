# E71 Acceptance：多指派人 mid — issue_assignees · CLI 1.55.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E71-S1`  
基线：`f84a233`（全文 `f84a233a4a9a8dea4c63bd470fde1c737c1b796e`；含 E71 design；E70 实现 tip `5f311f4` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e71-multi-assignee-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e71-multi-assignee-mid.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A 结表 + alembic + 镜像 + 过滤 | ✅ | Q1a 有序首=primary 镜像 `assignee_id`；Q2a 仅 PATCH `assignee_id` 清空协作者；Q3a max 10；Q4a bulk 仍 primary-only；alembic `issue_assignees` + 有 WS 的 assignee_id 回填；embed `assignees[]`；`assignee_id`/`me`=primary，新 `assignee_any`；无 WS 遗留 task 路径仅镜像 primary、不写结表 |
| B 通知 fanout + webhook 复用 | ✅ | Q5a 复用 `issue.assignee_changed`（无新事件名）；payload 可含 `assignee_ids`；`notify_assigned` 扇出全部新人选；评论/到期 recipients 含全部 assignees |
| C FE 多选+叠头像 | ✅ | UserSelect multiple；详情 EditableField `#display` 叠头像；看板 stack；vitest assignees util；elegant-router `f`+`r` 守 E31/E63（build 误删已还原） |
| D CLI 1.55.0（含 VERSION） | ✅ | Q6a create/update `--assignees`；`issue show` Assignees；全钉 **1.55.0**：`VERSION` / `pyproject.toml` / `setup.py` / `opentask/__init__.py` / `opentask_cli.VERSION` |
| E 安全 / no-emit / 邻面不动 | ✅ | WS 成员校验；formula no-emit；不改 E63–E70 邻面主表面（仅 CLI 版本钉）；无 Activity Push / 无门户再厚 / 无甘特 / 无递归孙项 / 无附件再开 |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：**1278 passed / 24 skipped / 1 failed**（已知 flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`，与 E71 无关；任务路径无 WS 同步回归已修）
- BE 定向 E71 API + normalize：**8 + unit normalize = passed**（定向 tasks 合同/jira/mapping 复跑 85 passed）
- CLI：**581 passed / 89 skipped**（全钉 **1.55.0**，含 `VERSION` 文件）
- FE vitest：**380 passed**（53 files）；`pnpm run build`：**ok**（elegant-router 误删 f/r 已还原）

## Tip

- 分支：`sprint/E71-S1`
- tip：`PLACE`（全文 `PLACE`）
- **未 push / 未开 PR / 未开 E72**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E72
