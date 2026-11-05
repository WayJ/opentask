# E75 Acceptance：Issue 复制 mid — duplicate · CLI 1.59.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E75-S1`  
基线：`78e12bb`（全文 `78e12bb29300a6e0cd9a84db3e2befd69beb9702`；含 E75 design；E74 tip `98d5bf4` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e75-issue-duplicate-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e75-issue-duplicate-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | `POST /api/issues/{id}/duplicate`；白名单字段复制；`status=open`；reporter=actor；Q1a timeline `duplicated_from`（无列/无 alembic）；Q2a 保留 `parent_issue_id`；Q3a 标题后缀 ` (copy)`；Q4a `relates_to`→源（非 triage `duplicates`）；跳过 formula CF；tags/assignees/CF 复制；与 triage `/triage/{id}/duplicate` 分路径 |
| B FE | ✅ | 详情头「复制 Issue」→ POST → toast 新 code → `router.push` 新 id；`buildDuplicateTitle` vitest；build ok；elegant-router 误删 `f`+`r` 已还原；`routes/index.ts` 仍含 `/f/:token`+`/r/:token` |
| C CLI 1.59.0 | ✅ | Q6a `issue duplicate <id> [--title] [--json]`；全钉 **1.59.0**：`VERSION` / `pyproject.toml` / `setup.py` / `opentask/__init__.py` / `opentask_cli.VERSION`；历史 epic 版本断言级联至 1.59.0 |
| D 安全/邻面/no-emit | ✅ | 跨 WS 404；viewer 403；Q5a 仍 `issue.created`（无 `issue.duplicated`）；formula no-emit（跳过 formula CF 写入）；不改 E63–E74 邻面主表面（仅 CLI 版本钉）；无 Activity Push / 无门户 / 无甘特；不深拷贝评论/附件/子项/关系（除 Q4a） |
| E 租户隔离 | ✅ | `require_workspace_context` + workspace 过滤 get；非成员/跨 WS 路径保持 404/403 |

## ADR

D1–D7 / Q1a–Q6a 按 design 落地。

## 门禁

- BE：**1324 passed / 24 skipped / 1 failed**（已知 flake `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`，与 E75 无关）
- BE 定向 E75 unit+API：**7 passed**
- CLI：**595 passed / 89 skipped**（全钉 **1.59.0**，含 `VERSION` 文件）
- FE vitest：**399 passed**（56 files）；`pnpm run build`：**ok**（elegant-router 误删 f/r 已还原）

## Tip

- 分支：`sprint/E75-S1`
- tip：`0238e1c`（全文 `0238e1cf16144f69b3c45ac240c42d509b2a33e0`）
- **未 push / 未开 PR / 未开 E76**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E76
