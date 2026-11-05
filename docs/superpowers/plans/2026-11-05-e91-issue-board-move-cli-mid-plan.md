# E91 Plan：Issue Board Move CLI mid · CLI 1.75.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`651e3d8`（全文 `651e3d83e4fccfca96e1c79b4cbf0874faa47719`；含 E91 design；E90 tip `4b7f34d` ⊂ HEAD）· 分支 `sprint/E91-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e91-issue-board-move-cli-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E92**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** writer+ 可用 CLI **1.75.0** 做 `issue board-move <issue_id> --status … --position N [--ordered-ids …]`；api_client `move_issue_on_board` → **POST** `/api/issues/board/move` + **snake_case** body；可选 `issue show` 人类表薄补 Position；**不**给 `issue update` 加 `--position`；**不**改 E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 health / E84 cycle / E83 watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead；**无**新 webhook/表/**无新 BE 路由**；formula no-emit；零产品 FE；**不做** Initiative health/甘特 / Saved View 全写；不重开 E63–E90。

**Architecture:** 复用既有 `POST /api/issues/board/move` body `{issue_id, status, position, ordered_ids?}`（**snake_case**，与 FE/`test_issue_board` 一致；**非** camelCase `issueId`/`orderedIds`）（Q1a/Q3a）；CLI 单命令 `issue board-move`（贴 `bulk-update` 命名）（Q2a）；`--status` + `--position` 必填、`--ordered-ids` 可选 CSV（Q4a 不改 update；show 可薄补 Position）；pins 1.75.0（Q5a）；FE 零改（Q6a）。语义 = 原子 status+position；可选 ordered_ids 重写目标列；跨 WS 403；缺 Issue 404。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E92；中文 docs；CLI **1.75.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：无新路由 · `issue board-move` · snake_case body · 不给 update 加 `--position` / show 可薄补 · pins 1.75.0 · 零产品 FE
- **不**改 E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / project-health / cycle / project-watchers / issue-template / milestone / `apply_project_move_integrity` / lead-members
- 无新 webhook / 无新表 / 无 alembic / **无新 BE 路由**；formula 永不 emit；无 Activity Push / 无门户 / 无甘特；**不做** Initiative health CLI / 甘特 / Saved View 全写
- 守 E63 `f`+`r`；已知 flake `test_user_search` 记入 acceptance，不挡
- **务必** api_client 发 **snake_case** `issue_id`/`status`/`position`/`ordered_ids`（禁误用 `issueId`/`orderedIds` 作为唯一键）
- **不要**把 board-move 误做成仅 `issue.update` 的 position 字段补丁

## File map
| Path | Role |
|------|------|
| `agent-harness/opentask-cli/opentask/utils/api_client.py` | `move_issue_on_board(issue_id, status, position, ordered_ids=None)` → POST snake_case |
| `agent-harness/opentask-cli/opentask/core/issue.py` | `issue board-move`；`_display_issue_details` 薄补 Position |
| VERSION / pyproject / setup / `__init__` / `opentask_cli.VERSION` | pins **1.75.0** + 历史 epic 断言级联 `1.74.0`→`1.75.0` |
| `agent-harness/opentask-cli/tests/test_e91_issue_board_move.py` | CLI TDD |
| `backend/tests/api/test_e91_issue_board_move_cli_mid.py` | 邻面 spy + board/move 端点存在性 |
| `docs/superpowers/acceptances/2026-11-05-e91-issue-board-move-cli-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e91-issue-board-move-cli-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e91-issue-board-move-cli-mid-acceptance.md
git commit -m "docs(E91): plan + acceptance skeleton"
```

---

### Task 2 — C：CLI api_client helper + `issue board-move` + show 薄补 Position + pins 1.75.0（TDD）

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`（Issues 段追加 `move_issue_on_board`）
- Modify: `agent-harness/opentask-cli/opentask/core/issue.py`（`board-move` 命令 + show Position）
- Modify: VERSION / pyproject.toml / setup.py / `__init__.py` / `opentask_cli.py` → **1.75.0**
- Cascade 历史 epic 测试里的 `1.74.0` → `1.75.0`
- Create: `agent-harness/opentask-cli/tests/test_e91_issue_board_move.py`

**Interfaces (api_client):**
```python
async def move_issue_on_board(
    self,
    issue_id: str,
    status: str,
    position: int,
    ordered_ids: list[str] | None = None,
) -> dict:
    """E91: POST /api/issues/board/move — atomic status+position; optional ordered_ids."""
    body: dict = {
        "issue_id": issue_id,
        "status": status,
        "position": int(position),
    }
    if ordered_ids is not None:
        body["ordered_ids"] = list(ordered_ids)
    return await self.post("/api/issues/board/move", data=body)
```

**CLI command:**
```python
@issue_cli.command(name="board-move")
@click.argument("issue_id")
@click.option(
    "--status",
    required=True,
    type=click.Choice(
        ["open", "in_progress", "feedback", "resolved", "closed", "rejected"],
        case_sensitive=False,
    ),
    help="Target board column / IssueStatus",
)
@click.option("--position", required=True, type=int, help="0-based position in target column")
@click.option("--ordered-ids", "ordered_ids_csv", default=None, help="Optional CSV of issue ids rewriting column order")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def board_move_issue(obj, issue_id, status, position, ordered_ids_csv, as_json):
    # require_workspace_id
    # resolve KEY-N → uuid via get_issue(by_code=True) if needed
    # if position < 0 → error
    # ordered = [p.strip() for p in ordered_ids_csv.split(",") if p.strip()] if ordered_ids_csv else None
    # client.move_issue_on_board(real_id, status.lower(), position, ordered)
    # json → echo; human → success "Issue 看板位置已更新" + status/position hints
```

**show 薄补（Q4a）:**
```python
# _display_issue_details 主 status_block 追加 Position（缺省显示 "—"）
skin.status_block({
    ...,
    "Position": issue.get("position", "—") if issue.get("position") is not None else "—",
    ...
})
# 注意：不给 issue update 加 --position
```

**Tests (at least):**
- `hasattr(OpenTaskClient, "move_issue_on_board")`；源码含 `self.post` + `/api/issues/board/move` + `issue_id` + `ordered_ids`；**禁** `"issueId"` / `"orderedIds"` JSON keys；**禁** `self.put` 作为本 helper 主方法
- `issue --help` 含 `board-move`；`issue board-move --help` 含 `--status` / `--position` / `--ordered-ids`
- `issue board-move ISS --status in_progress --position 3 --json` → helper 收到 `(ISS, "in_progress", 3, None)`
- 带 `--ordered-ids a,b,c` → helper 收到 `ordered_ids=["a","b","c"]`
- 缺 `--status` 或 `--position` → exit ≠ 0
- show human 输出含 `Position`（mock get_issue 返回 position）
- **不**给 `issue update --help` 加 `--position`（断言 update help **无** board-only `--position`，或至少不因本 epic 新增；link update 的 `--position` 是 E76 邻面，勿误伤——定向断言 `issue update --help` 不出现独立 board position flag 时可用：「`--position` not in update help」——注意 E76 link 是 `issue link update --position`，`issue update --help` 本就不含）
- pins 1.75.0（VERSION + pyproject + setup + `__init__` + `--version`）
- bulk-update / trash 等邻面命令仍在 help

- [ ] **Step 1:** Write failing CLI tests
- [ ] **Step 2:** Run directed → FAIL（缺 helper/command / pins 仍 1.74.0）
- [ ] **Step 3:** Implement helper + command + show 薄补 + pins cascade
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E91): CLI 1.75.0 issue board-move`

---

### Task 3 — A：BE 邻面 spy + 既有 board/move 端点存在性

**Files:**
- Create: `backend/tests/api/test_e91_issue_board_move_cli_mid.py`

**Tests:**
- spy：`api/issue/router.py` 仍含 `@router.post("/board/move")` + `async def move_issue_on_board` + `IssueBoardMove`
- schema：`IssueBoardMove` 仍含 `issue_id` / `status` / `position` / `ordered_ids`（snake）；**无** `issueId`/`orderedIds` 字段名
- **无**新 `@router.* /board/` 以外的 board 路由；无新 initiative `/health`
- 无 alembic 新文件命名 e91
- 邻面 markers 仍在（initiatives projects PUT/POST/DELETE / custom-fields POST reorder / favorites PUT reorder / tag-groups / replace_tags / project health / cycles generate-upcoming / project_watcher enrich / issue_templates / milestone / issue_project_move / E65 relations）
- formula no-emit soft guard
- 附跑既有：`tests/api/test_issue_board.py` smoke

- [ ] **Step 1:** Write spy tests
- [ ] **Step 2–4:** 绿
- [ ] **Step 5:** commit `test(E91): BE issue-board-move mid spy`

---

### Task 4 — E：门禁 + acceptance

- Directed BE：`test_e91_issue_board_move_cli_mid.py` + `test_issue_board.py`
- Full BE `pytest tests`（flake 记入）
- CLI suite（含 directed e91）
- FE：零产品改动 → vitest smoke + production build；确认 `frontend/src/router/routes/index.ts` 仍有 `/f/:token` + `/r/:token`（若 build 冲掉 elegant imports → checkout 恢复）
- 写满 acceptance（tip SHA + 门禁数 + Q1a–Q6a + superpowers 行；**勿留** `_pending_`/骨架）
- commit `docs(E91): acceptance`
- **STOP** — 不 push / 不开 PR / 不自开 E92

---

## Self-review
- Spec A–D / Q1a–Q6a / ADR D1–D6 均有对应任务
- 无 TBD/TODO 占位
- api_client 签名与 CLI 参数一致（snake_case body）
- 明确禁：update `--position`、新路由、initiative health、Saved View 全写、push/PR/E92
