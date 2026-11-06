# E94 Plan：Issue Reactions CLI mid · CLI 1.78.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`d84cba2`（全文 `d84cba2969e393bb0766624a13fcfdbdd8d39ce1`；含 E94 design；E93 tip `577f13d` ⊂ HEAD）· 分支 `sprint/E94-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e94-issue-reactions-cli-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E95**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** member+ 可用 CLI **1.78.0** 做 Issue 与 Comment **reaction list / add / remove**；api_client 六 helpers → 复用既有六端点；human 薄表；**不**改 E93 display-prefs / E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 health / E84 cycle / E83 watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead；**无**新 webhook/表/**无新 BE 路由**；formula no-emit；零产品 FE；**不做** Initiative health/甘特 / bulk project_id / watching filter / notif prefs / threading；不重开 E63–E93。

**Architecture:** 复用既有 Issue + Comment reactions GET/POST/DELETE（Q1a）；CLI 挂 `issue` 下扁平两组 `reaction` + `comment-reaction`（Q2a）；api_client POST `{emoji}` / DELETE query `emoji=`（Q3a）；human 薄表 emoji/count 或 emoji/userIds；add/remove 薄回显；**不**改 `issue show`（Q4a）；pins 1.78.0（Q5a）；FE 零改（Q6a）。**不要**停 7377/9527。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E95；中文 docs；CLI **1.78.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：无新路由 · `issue reaction` + `issue comment-reaction` · snake_case `{emoji}` · human 薄表、不改 FE / show · pins 1.78.0 · 零产品 FE
- **不**改 E93 display-prefs / E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / project-health / cycle / project-watchers / issue-template / milestone / `apply_project_move_integrity` / lead-members / notif prefs / threading
- 无新 webhook / 无新表 / 无 alembic / **无新 BE 路由**；formula 永不 emit；无 Activity Push / 无门户 / 无甘特；**不做** Initiative health CLI / 甘特 / bulk project_id / watching filter
- 守 E63 `f`+`r`（FE build 冲掉 imports → **必须 checkout 恢复**；收尾 `git status` 干净）；已知 flake `test_user_search` 记入 acceptance，不挡
- **不要**停 7377 后端或 9527 前端
- 缺 `--emoji` 本地失败不打 BE；DELETE 缺反应透传既有 404
- 既有 `issue comment` / `issue comment attachment` 组**别破坏**

## File map
| Path | Role |
|------|------|
| `agent-harness/opentask-cli/opentask/utils/api_client.py` | 六 reaction helpers |
| `agent-harness/opentask-cli/opentask/core/issue.py` | 新组 `reaction` + `comment-reaction` 挂 `issue_cli` |
| VERSION / pyproject / setup / `__init__` / `opentask_cli.VERSION` | pins **1.78.0** + 历史 epic 断言级联 `1.77.0`→`1.78.0` |
| `agent-harness/opentask-cli/tests/test_e94_issue_reactions.py` | CLI TDD |
| `backend/tests/api/test_e94_issue_reactions_cli_mid.py` | 邻面 spy + reactions 六端点存在性 |
| `docs/superpowers/acceptances/2026-11-05-e94-issue-reactions-cli-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e94-issue-reactions-cli-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e94-issue-reactions-cli-mid-acceptance.md
git commit -m "docs(E94): plan + acceptance skeleton"
```

---

### Task 2 — C：CLI api_client 六 helpers + `issue reaction` / `issue comment-reaction` + pins 1.78.0（TDD）

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`（Comments 段附近追加六 helpers）
- Modify: `agent-harness/opentask-cli/opentask/core/issue.py`（两组 + 六命令）
- Modify: VERSION / pyproject.toml / setup.py / `__init__.py` / `opentask_cli.py` → **1.78.0**
- Cascade 历史 epic 测试里的 `1.77.0` → `1.78.0`
- Create: `agent-harness/opentask-cli/tests/test_e94_issue_reactions.py`

**Interfaces (api_client):**
```python
async def list_issue_reactions(self, issue_id: str) -> dict:
    """E94: GET /api/issues/{id}/reactions → {rows,total}."""
    return await self.get(f"/api/issues/{issue_id}/reactions")

async def add_issue_reaction(self, issue_id: str, emoji: str) -> dict:
    """E94: POST /api/issues/{id}/reactions body {emoji}."""
    return await self.post(
        f"/api/issues/{issue_id}/reactions",
        data={"emoji": emoji},
    )

async def remove_issue_reaction(self, issue_id: str, emoji: str) -> dict:
    """E94: DELETE /api/issues/{id}/reactions?emoji=."""
    return await self.delete(
        f"/api/issues/{issue_id}/reactions",
        params={"emoji": emoji},
    )

async def list_comment_reactions(self, issue_id: str, comment_id: str) -> dict:
    """E94: GET /api/issues/{id}/comments/{cid}/reactions → {reactions}."""
    return await self.get(
        f"/api/issues/{issue_id}/comments/{comment_id}/reactions"
    )

async def add_comment_reaction(
    self, issue_id: str, comment_id: str, emoji: str
) -> dict:
    """E94: POST …/comments/{cid}/reactions body {emoji}."""
    return await self.post(
        f"/api/issues/{issue_id}/comments/{comment_id}/reactions",
        data={"emoji": emoji},
    )

async def remove_comment_reaction(
    self, issue_id: str, comment_id: str, emoji: str
) -> dict:
    """E94: DELETE …/comments/{cid}/reactions?emoji=."""
    return await self.delete(
        f"/api/issues/{issue_id}/comments/{comment_id}/reactions",
        params={"emoji": emoji},
    )
```

**CLI commands (issue.py):**
- `@issue_cli.group(name="reaction")` → `list|add|remove`（`remove` 可兼 alias `rm`）
- `@issue_cli.group(name="comment-reaction")` → `list|add|remove`
- 形状：
  - `issue reaction list ISSUE [--json]`
  - `issue reaction add ISSUE --emoji EMOJI [--json]`
  - `issue reaction remove ISSUE --emoji EMOJI [--json]`
  - `issue comment-reaction list ISSUE COMMENT [--json]`
  - `issue comment-reaction add ISSUE COMMENT --emoji EMOJI [--json]`
  - `issue comment-reaction remove ISSUE COMMENT --emoji EMOJI [--json]`
- `--emoji` required on add/remove → 缺参本地 Click 失败，不打 BE
- human：issue list 薄表 emoji/count；comment list 薄表 emoji/userIds；add/remove 薄回显
- `--json` 全量；支持 KEY-N（`_resolve_issue_id`）；**不**改 `issue show` / `issue comment` / attachment
- 既有 `comment` 组保持不变

**Tests (at least):**
- pins 1.78.0（VERSION + pyproject + setup + `__init__` + `--version`）
- 六 helpers 存在；源码含正确 method+path；POST body 键 `emoji`；DELETE 带 `params`/`emoji`
- `issue --help` 含 `reaction` + `comment-reaction`；仍含 `comment` / `board-move` / `bulk-update`
- `issue reaction --help` 含 list/add/remove；`issue comment-reaction --help` 同
- list/add/remove（issue + comment）调用对应 helper（mock）
- 缺 `--emoji` → exit ≠ 0 且不调 helper
- issue list human 含 emoji/count；comment list human 含 emoji
- 邻面：`display-prefs --help` 仍含 get/set；`view --help` 仍含 create

- [ ] **Step 1:** Write failing CLI tests
- [ ] **Step 2:** Run directed → FAIL（缺 helper/command / pins 仍 1.77.0）
- [ ] **Step 3:** Implement helpers + commands + pins cascade
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E94): CLI 1.78.0 issue reaction + comment-reaction`

---

### Task 3 — A：BE 邻面 spy + 既有六 reactions 端点存在性

**Files:**
- Create: `backend/tests/api/test_e94_issue_reactions_cli_mid.py`

**Tests:**
- spy：`api/issue/router.py` 仍含六装饰器/函数：
  - `@router.get("/{issue_id}/reactions")` + `async def get_reactions`
  - `@router.post("/{issue_id}/reactions")` + `async def add_reaction`
  - `@router.delete("/{issue_id}/reactions")` + `async def remove_reaction`
  - `@router.get("/{issue_id}/comments/{comment_id}/reactions")` + `async def get_comment_reactions`
  - `@router.post("/{issue_id}/comments/{comment_id}/reactions")` + `async def add_comment_reaction`
  - `@router.delete("/{issue_id}/comments/{comment_id}/reactions")` + `async def remove_comment_reaction`
- **无**新 alembic 命名 e94；无新 initiative `/health`
- 邻面 markers 仍在（display-prefs GET/PUT · saved-views write · board/move · initiatives projects · CF reorder · favorites reorder · tag-groups · replace_tags · project health · cycles · project_watcher · issue_templates · milestone · issue_project_move · E65 relations）
- formula no-emit soft guard
- 附跑既有：`tests/api/test_notif_prefs_reactions.py` 中 comment reactions smoke（可选定向）

- [ ] **Step 1:** Write spy tests
- [ ] **Step 2–4:** 绿
- [ ] **Step 5:** commit `test(E94): BE issue-reactions mid spy`

---

### Task 4 — E：门禁 + acceptance

- Directed BE：`test_e94_issue_reactions_cli_mid.py` + `test_notif_prefs_reactions.py`（comment reactions）
- Full BE `pytest tests`（flake 记入）
- CLI suite（含 directed e94）
- FE：零产品改动 → vitest smoke + production build；确认 `f`+`r`（若 build 冲掉 elegant imports → **checkout 恢复**）；收尾 `git status` 干净
- 写满 acceptance（tip SHA + 门禁数 + Q1a–Q6a + superpowers 行；**勿留** `_pending_`/骨架）
- commit `docs(E94): acceptance`
- **STOP** — 不 push / 不开 PR / 不自开 E95；不停 7377/9527

---

## Self-review
- Spec A–D / Q1a–Q6a / ADR D1–D6 均有对应任务
- 无 TBD/TODO 占位
- api_client 签名与 CLI 参数一致（`{emoji}` + DELETE query）
- 明确禁：新路由、initiative health、bulk project_id、watching filter、notif prefs、threading、push/PR/E95、停 7377/9527；主测走扁平 `comment-reaction`
