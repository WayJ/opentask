# E76 Acceptance：Issue 外链 mid — issue_links · CLI 1.60.0

日期：2026-11-05（Asia/Shanghai）  
分支：`sprint/E76-S1`  
基线：`83273b4`（全文 `83273b451265c876d3e53253d8ec334f6252dbd3`；含 E76 design；E75 tip `6de4382` 为其祖先）  
Design：`docs/superpowers/specs/2026-11-05-e76-issue-external-links-mid-design.md`  
Plan：`docs/superpowers/plans/2026-11-05-e76-issue-external-links-mid-plan.md`

## 范围核对

| 项 | 状态 | 备注 |
|----|------|------|
| A BE | ✅ | alembic `issue_links`（rev `b5c6d7e8f9a0`）；CRUD GET/POST/PATCH/DELETE `/api/issues/{id}/links`；Q2a position 追加末尾 + PATCH position；Q3a ≤50；Q4a 仅 http/https；Q5a timeline `link_added`/`link_removed`（title-only 不刷）；跨 WS 404；viewer 读 OK / 写 403；≠ 附件/VCS/relations |
| B FE | ✅ | 详情「链接」卡（`IssueLinksPanel`）；空态「添加设计稿、文档或仪表盘链接」；新标签打开；编辑/删除；`isHttpUrl`/`hostnameFromUrl` vitest；build ok；`routes/index.ts` 仍含 `/f/:token`+`/r/:token` |
| C CLI 1.60.0 | ✅ | Q6a `issue link list\|add\|rm`（+ optional `update`）；全钉 **1.60.0**：`VERSION` / `pyproject.toml` / `setup.py` / `opentask/__init__.py` / `opentask_cli.VERSION`；历史 epic 版本断言级联至 1.60.0 |
| D 安全/邻面/no-emit | ✅ | 租户隔离；viewer 写 403；无新 webhook 事件名；formula no-emit；不改 E63–E75 邻面主表面（仅 CLI 版本钉）；无 Activity Push / 无门户 / 无甘特；不走附件存储/ACL；不写 `issue_vcs_links` / IssueRelation |
| E 门禁 | ✅ | 见下 |

## ADR

D1–D6 / Q1a–Q6a 按 design 落地。Reorder 端点后置（Q2a PATCH position 够用）。

## 门禁

- BE：**1338 passed / 24 skipped / 4 failed**（全套序污染 flake；单独重跑均绿，与 E76 无关）：
  - `tests/api/test_auth.py::test_login_local_success`
  - `tests/api/test_auth.py::test_login_local_wrong_password`
  - `tests/api/test_auth.py::test_enabled_user_token_accepted`
  - `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`（已知 flake）
- BE 定向 E76 unit+API：**17 passed**
- CLI：**599 passed / 89 skipped**（全钉 **1.60.0**，含 `VERSION` 文件）
- FE vitest：**403 passed**（57 files）；`pnpm run build`：**ok**（elegant-router 目录名 f/r 警告仍在，`f`+`r` 路由未丢）

## Tip

- 分支：`sprint/E76-S1`
- tip：`c13db14`（全文 `c13db14c695feb97ca44ca8b255335ee7426acfd`）
- **未 push / 未开 PR / 未开 E77**

## Receipt

`superpowers: design/plan/TDD/verify/acceptance = ok`

**STOP** — 未 push / 未开 PR / 未开 E77
