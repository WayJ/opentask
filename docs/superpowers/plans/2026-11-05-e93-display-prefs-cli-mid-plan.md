# E93 Plan：Display Prefs CLI mid · CLI 1.77.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`4e818d2`（全文 `4e818d2aabe5c9324bd46f33d98174cdea90495a`；含 E93 design；E92 tip `48e6bb3` ⊂ HEAD）· 分支 `sprint/E93-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e93-display-prefs-cli-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E94**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** member+ 可用 CLI **1.77.0** 做个人 Issue Display prefs **get / set**；api_client 两 helpers → 复用既有 `GET/PUT /api/display-prefs/issue`（body `{display}`；display 内 **snake_case**）；可选 human 薄摘要；**不**改 E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 health / E84 cycle / E83 watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead；**无**新 webhook/表/**无新 BE 路由**；formula no-emit；零产品 FE；**不做** Initiative health/甘特 / bulk project_id / watching filter；不重开 E63–E92。

**Architecture:** 复用既有 GET/PUT（Q1a）；新顶层组 `display-prefs get|set`（Q2a）；api_client 发 `{display: <dict>}`，dict 内保持 snake_case，**不**改写成 camelCase `viewMode`（Q3a）；human 薄摘要 view_mode/group_by/swimlane_by（Q4a）；pins 1.77.0 + E49「无子命令」断言改为组存在（Q5a）；FE 零改（Q6a）。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E94；中文 docs；CLI **1.77.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：无新路由 · `display-prefs get|set` · snake_case `{display}` · 可选 human 摘要、不改 FE · pins 1.77.0 · 零产品 FE
- **不**改 E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / project-health / cycle / project-watchers / issue-template / milestone / `apply_project_move_integrity` / lead-members
- 无新 webhook / 无新表 / 无 alembic / **无新 BE 路由**；formula 永不 emit；无 Activity Push / 无门户 / 无甘特；**不做** Initiative health CLI / 甘特 / bulk project_id / watching filter
- 守 E63 `f`+`r`；已知 flake `test_user_search` 记入 acceptance，不挡
- **务必** display 内键 **snake_case**（禁误用 `viewMode` 作为请求唯一键）
- **不要**改 `view use` / `view create|…` / `issue list` 默认行为
- **务必**更新 E49 `test_e49_display_v2.py`「无专用子命令」→ 组存在 / version 1.77.0

## File map
| Path | Role |
|------|------|
| `agent-harness/opentask-cli/opentask/utils/api_client.py` | `get_issue_display_prefs` + `put_issue_display_prefs` |
| `agent-harness/opentask-cli/opentask/core/display_prefs.py` | 新组 `display-prefs get|set` |
| `agent-harness/opentask-cli/opentask/opentask_cli.py` | 注册 `display_prefs_cli` |
| VERSION / pyproject / setup / `__init__` / `opentask_cli.VERSION` | pins **1.77.0** + 历史 epic 断言级联 `1.76.0`→`1.77.0` |
| `agent-harness/opentask-cli/tests/test_e93_display_prefs.py` | CLI TDD |
| `agent-harness/opentask-cli/tests/test_e49_display_v2.py` | 改为断言组存在 + 1.77.0 |
| `backend/tests/api/test_e93_display_prefs_cli_mid.py` | 邻面 spy + display-prefs GET/PUT 存在性 |
| `docs/superpowers/acceptances/2026-11-05-e93-display-prefs-cli-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e93-display-prefs-cli-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e93-display-prefs-cli-mid-acceptance.md
git commit -m "docs(E93): plan + acceptance skeleton"
```

---

### Task 2 — C：CLI api_client 两 helpers + `display-prefs get|set` + pins 1.77.0 + E49 更新（TDD）

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`（Saved Views 段附近或独立段追加两 helpers）
- Create: `agent-harness/opentask-cli/opentask/core/display_prefs.py`
- Modify: `agent-harness/opentask-cli/opentask/opentask_cli.py`（import + `cli.add_command`）
- Modify: VERSION / pyproject.toml / setup.py / `__init__.py` / `opentask_cli.py` → **1.77.0**
- Cascade 历史 epic 测试里的 `1.76.0` → `1.77.0`
- Create: `agent-harness/opentask-cli/tests/test_e93_display_prefs.py`
- Modify: `agent-harness/opentask-cli/tests/test_e49_display_v2.py`

**Interfaces (api_client):**
```python
async def get_issue_display_prefs(self) -> dict:
    """E93: GET /api/display-prefs/issue → {display: null|object}."""
    return await self.get("/api/display-prefs/issue")

async def put_issue_display_prefs(self, display: dict) -> dict:
    """E93: PUT /api/display-prefs/issue body {display}; keep snake_case keys."""
    return await self.put("/api/display-prefs/issue", data={"display": display})
```

**CLI commands (display_prefs.py):**
- `display-prefs get [--json]`
- `display-prefs set --display JSON [--json]`
- 非法 `--display` JSON → `click.ClickException("JSON 无效: …")`（不打 BE）
- `--display` 必须是 JSON object；非 object → ClickException
- human `get`/`set`：薄打印 View mode / Group by / Swimlane by / Hide empty lanes；`display: null` 时明示无 prefs
- `--json` 全量

**Tests (at least):**
- pins 1.77.0（VERSION + pyproject + setup + `__init__` + `--version`）
- 两 helpers 存在；源码含正确 method+path；PUT body 顶层键 `display`；禁 `"viewMode"` 作为唯一请求键写法（源码不改写 camelCase）
- `display-prefs --help` 含 `get`/`set`
- get/set 调用对应 helper（mock）
- get null → human 含无 prefs / null 语义；有 prefs → 含 View mode
- 非法 `--display` JSON → exit ≠ 0 且不调 helper
- `--display` 非 object → exit ≠ 0
- E49：`--help` 含 `display-prefs`；version 1.77.0
- 邻面：`view --help` 仍含 create；`issue --help` 仍含 board-move

- [ ] **Step 1:** Write failing CLI tests
- [ ] **Step 2:** Run directed → FAIL（缺 helper/command / pins 仍 1.76.0）
- [ ] **Step 3:** Implement helpers + commands + pins cascade + E49 update
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E93): CLI 1.77.0 display-prefs get|set`

---

### Task 3 — A：BE 邻面 spy + 既有 display-prefs GET/PUT 存在性

**Files:**
- Create: `backend/tests/api/test_e93_display_prefs_cli_mid.py`

**Tests:**
- spy：`api/display_prefs/router.py` 仍含 `@router.get("/issue")`、`@router.put("/issue")`、`async def get_issue_display_prefs`、`async def put_issue_display_prefs`、`class DisplayPrefsPut` + `display:`；无新路由装饰器前缀外路径
- **无**新 alembic 命名 e93；无新 initiative `/health`
- 邻面 markers 仍在（saved-views write · board/move · initiatives projects · CF reorder · favorites reorder · tag-groups · replace_tags · project health · cycles · project_watcher · issue_templates · milestone · issue_project_move · E65 relations）
- formula no-emit soft guard
- 附跑既有：`tests/api/test_display_prefs.py` smoke

- [ ] **Step 1:** Write spy tests
- [ ] **Step 2–4:** 绿
- [ ] **Step 5:** commit `test(E93): BE display-prefs mid spy`

---

### Task 4 — E：门禁 + acceptance

- Directed BE：`test_e93_display_prefs_cli_mid.py` + `test_display_prefs.py`
- Full BE `pytest tests`（flake 记入）
- CLI suite（含 directed e93 + 更新后的 E49）
- FE：零产品改动 → vitest smoke + production build；确认 `f`+`r`（若 build 冲掉 elegant imports → checkout 恢复）
- 写满 acceptance（tip SHA + 门禁数 + Q1a–Q6a + superpowers 行；**勿留** `_pending_`/骨架）
- commit `docs(E93): acceptance`
- **STOP** — 不 push / 不开 PR / 不自开 E94

---

## Self-review
- Spec A–D / Q1a–Q6a / ADR D1–D6 均有对应任务
- 无 TBD/TODO 占位
- api_client 签名与 CLI 参数一致（`{display}` + snake_case）
- 明确禁：新路由、initiative health、bulk project_id、watching filter、push/PR/E94；E49 断言必须更新
