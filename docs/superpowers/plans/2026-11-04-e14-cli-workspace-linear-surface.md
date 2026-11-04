# E14 OpenTask CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline) — thick epic, single session. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CLI 1.1.0 以 Workspace + Issue 为主轴，请求一律带 `X-Workspace-Id`，并对齐 Linear 常用 HTTP 面。

**Architecture:** 扩展 `Config` / `OpenTaskClient._get_headers`；新增 `opentask/core/*.py` 命令组；API 方法集中在 `api_client.py`；单测 mock httpx/client；冒烟脚本打 `:7377`。

**Tech Stack:** Python 3.8+、Click、httpx、pytest、pytest-asyncio

## Global Constraints

- 分支 `sprint/E14-S1`，基线 `eb76295`；**禁止 push / PR**
- 不改 E13 FE 视觉与无关后端
- 版本 `1.1.0`；README/help 中文可混用，验收文档中文
- PGE 路径保留但非主轴
- VCS 遵循 `docs/superpowers/contracts/2026-11-04-e11-vcs-http-contract.md`

## File map

| 文件 | 职责 |
|---|---|
| `opentask/utils/config.py` | active_workspace_id/name |
| `opentask/utils/api_client.py` | X-Workspace-Id + 新 API methods |
| `opentask/opentask_cli.py` | 注册命令组、VERSION、help 文案 |
| `opentask/core/workspace.py` | workspace list/use/current/show |
| `opentask/core/cycle.py` | cycle 命令 |
| `opentask/core/label.py` | tags 命令（别名 label） |
| `opentask/core/triage.py` | triage |
| `opentask/core/inbox.py` | inbox + snooze |
| `opentask/core/favorite.py` | favorites |
| `opentask/core/view.py` | saved views |
| `opentask/core/member.py` | members + invite |
| `opentask/core/initiative.py` | initiatives |
| `opentask/core/doc.py` | entity-documents |
| `opentask/core/issue.py` | children/relations；ensure KEY-N |
| `opentask/core/project.py` | list 尊重 rows + WS |
| `tests/test_workspace_*.py` 等 | 单测 |
| `scripts/e14_cli_smoke.sh` 或 `docs/...` | 冒烟 |
| `README.md` / pyproject / `__init__` | 文档与版本 |

---

### Task 1: Config + X-Workspace-Id header

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/utils/config.py`
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`
- Test: `agent-harness/opentask-cli/tests/test_workspace_header.py`

**Interfaces:**
- Produces: `Config.active_workspace_id`, `Config.active_workspace_name`, `clear_workspace_context()`
- Produces: headers include `X-Workspace-Id` when set

- [ ] **Step 1: Write failing test** — assert `_get_headers()` contains workspace id when config set; absent when not
- [ ] **Step 2: Run** `uv run pytest tests/test_workspace_header.py -v` → FAIL
- [ ] **Step 3: Implement** config props + header injection
- [ ] **Step 4: PASS + commit** `feat(cli): send X-Workspace-Id from active workspace`

### Task 2: `opentask workspace` commands

**Files:**
- Create: `opentask/core/workspace.py`
- Modify: `opentask_cli.py` register
- Modify: `api_client.py` list/get workspaces
- Test: `tests/test_workspace_commands.py`

- [ ] list / use / current / show；use 写 config；`--json` 稳定
- [ ] commit `feat(cli): workspace list|use|current|show`

### Task 3: Issue first-class polish

**Files:** issue.py, api_client.py, tests

- [ ] `issue children`、`issue relations`（list/add/remove）
- [ ] 确认 assign/status/show KEY-N 单测覆盖
- [ ] commit `feat(cli): issue children and relations`

### Task 4: Linear surface — cycle / label / triage

- [ ] API methods + command modules + unit tests (help + path)
- [ ] commit per group or one `feat(cli): cycle label triage commands`

### Task 5: inbox / favorite / view / member / invite

- [ ] 同上；invite preview/accept 走 `/api/invites`
- [ ] commit `feat(cli): inbox favorite view member invite`

### Task 6: initiative / doc + project WS list fix

- [ ] entity-documents + initiatives CRUD 最小
- [ ] project list 正确解包 `rows`；依赖 header
- [ ] commit `feat(cli): initiative doc; project list respects workspace`

### Task 7: Docs, version 1.1.0, smoke, acceptance

- [ ] README 重写主轴；`--help` 示例 Issue/WS
- [ ] `scripts/e14_cli_smoke.sh` + acceptance md（中文）
- [ ] 全量 `uv run pytest` 绿；记录条数
- [ ] commit `docs(cli): E14 1.1.0 README smoke acceptance`；**不 push**

## Verification

```bash
cd agent-harness/opentask-cli && uv run pytest -q
opentask --version   # 1.1.0
opentask --help      # workspace/issue 在前
# 冒烟（BE :7377 已起）
bash scripts/e14_cli_smoke.sh
```
