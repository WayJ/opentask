# E88 Plan：Favorite Reorder CLI mid · CLI 1.72.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`34f151a`（全文 `34f151afee076a67644d368e92bb746c87448595`；含 E88 design；E87 tip `c82bc63` ⊂ HEAD）· 分支 `sprint/E88-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e88-favorite-reorder-cli-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E89**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** writer+ 可用 CLI **1.72.0** 做 `favorite reorder --ids …`（可选位置参数）；api_client 有 `reorder_favorites` → **PUT** `/api/favorites/reorder`；`favorite list` 露 `position`；**不**改 E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead；**无**新 webhook/表/**无新 BE 路由**；formula no-emit；零产品 FE；不重开 E63–E87。

**Architecture:** 复用既有 `PUT /api/favorites/reorder` body `{ordered_ids}`（Q1a）；CLI 挂 `favorite reorder`（Q2a）；`--ids` 为主 + 可选位置参数（Q3a）；list 露 position（Q4a）；pins 1.72.0（Q5a）；FE 零改（Q6a）。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E89；中文 docs；CLI **1.72.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：无新路由 · `favorite reorder` · `--ids` 为主 · list 露 position · pins 1.72.0 · 零产品 FE
- **不**改 E87 tag-group / E86 set/multi / project-health / cycle / project-watchers / issue-template / milestone / `apply_project_move_integrity` / lead-members；**不**改 `favorite add|remove` 默认行为
- 无新 webhook / 无新表 / 无 alembic / **无新 BE 路由**；formula 永不 emit；无 Activity Push / 无门户 / 无甘特
- 守 E63 `f`+`r`；已知 flake `test_user_search` 记入 acceptance，不挡
- **务必** PUT（非 POST）接 `/api/favorites/reorder`

## File map
| Path | Role |
|------|------|
| `agent-harness/opentask-cli/opentask/utils/api_client.py` | `reorder_favorites(ordered_ids: list[str])` → PUT |
| `agent-harness/opentask-cli/opentask/core/favorite.py` | `favorite reorder` + list 露 position |
| VERSION / pyproject / setup / `__init__` / `opentask_cli.VERSION` | pins **1.72.0** + 历史 epic 断言级联 |
| `agent-harness/opentask-cli/tests/test_e88_favorite_reorder.py` | CLI TDD |
| `backend/tests/api/test_e88_favorite_reorder_cli_mid.py` | 邻面 spy + 既有 favorites reorder 端点存在性 |
| `docs/superpowers/acceptances/2026-11-05-e88-favorite-reorder-cli-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e88-favorite-reorder-cli-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e88-favorite-reorder-cli-mid-acceptance.md
git commit -m "docs(E88): plan + acceptance skeleton"
```

---

### Task 2 — C：CLI api_client reorder_favorites + favorite reorder + list position + pins 1.72.0（TDD）

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`（Favorites 段追加 `reorder_favorites`）
- Modify: `agent-harness/opentask-cli/opentask/core/favorite.py`
- Modify: VERSION / pyproject.toml / setup.py / `__init__.py` / `opentask_cli.py` → **1.72.0**
- Cascade 历史 epic 测试里的 `1.71.0` → `1.72.0`
- Create: `agent-harness/opentask-cli/tests/test_e88_favorite_reorder.py`

**Interfaces (api_client):**
```python
async def reorder_favorites(self, ordered_ids: list[str]) -> dict:
    """E88: PUT /api/favorites/reorder — ordered_ids must cover all current favorites."""
    return await self.put(
        "/api/favorites/reorder",
        data={"ordered_ids": list(ordered_ids)},
    )
```

**CLI commands:**
```python
def _parse_ordered_ids(ids_csv: str | None, positional: tuple[str, ...]) -> list[str]:
    ids: list[str] = []
    if ids_csv is not None and str(ids_csv).strip() != "":
        ids.extend([p.strip() for p in str(ids_csv).split(",") if p.strip()])
    for p in positional or ():
        s = str(p).strip()
        if s:
            ids.append(s)
    return ids

@favorite_cli.command(name="reorder")
@click.option("--ids", "ids_csv", default=None, help="Comma-separated favorite ids in new order")
@click.argument("positional_ids", nargs=-1)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def favorite_reorder(obj, ids_csv, positional_ids, as_json):
    # require_workspace_id; parse ids; if empty → ClickException
    # client.reorder_favorites(ordered_ids)
    # json → echo_json; human → success "顺序已更新"

# favorite list human table: columns ID, Type, Target, Position
#   position from r.get("position")
```

**Tests (at least):**
- `hasattr` `reorder_favorites`；`inspect.signature` / source 含 `put` + `/api/favorites/reorder`（非 post）
- `favorite --help` 含 `reorder`；`favorite reorder --help` 含 `--ids`
- `favorite reorder --ids a,b,c --json` → `reorder_favorites(["a","b","c"])`
- `favorite reorder id1 id2 --json`（位置参数）→ `reorder_favorites(["id1","id2"])`
- 无 `--ids` 且无位置参数 → exit ≠ 0
- `favorite list --json` 输出含 `position`（mock rows 带 position）
- pins 1.72.0（VERSION + pyproject + setup + `__init__` + `--version`）

- [ ] **Step 1:** Write failing CLI tests
- [ ] **Step 2:** Run directed → FAIL（缺 helper/command / pins 仍 1.71.0）
- [ ] **Step 3:** Implement helper + command + list position + pins cascade
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E88): CLI 1.72.0 favorite reorder + list position`

---

### Task 3 — A：BE 邻面 spy + 既有 favorites reorder 端点存在性

**Files:**
- Create: `backend/tests/api/test_e88_favorite_reorder_cli_mid.py`

**Tests:**
- spy：`api/favorites/router.py` 仍含 `@router.put("/reorder")` + `async def reorder_favorites` + `FavoriteReorder` + `ordered_ids`；**无** `@router.post("/reorder")`
- 无 alembic 新文件命名 e88
- 邻面 markers 仍在（tag-groups / replace_tags / project health / cycles generate-upcoming / project_watcher enrich / issue_templates / milestone / issue_project_move / E86 update_tag）
- formula no-emit soft guard
- 附跑既有：`tests/api/test_favorites.py`（含 `test_favorites_reorder_by_ordered_ids`）

- [ ] **Step 1:** Write spy tests
- [ ] **Step 2–4:** 绿
- [ ] **Step 5:** commit `test(E88): BE favorite-reorder mid spy`

---

### Task 4 — E：门禁 + acceptance

- Directed BE：`test_e88_favorite_reorder_cli_mid.py` + `test_favorites.py`
- Full BE `pytest tests`（flake 记入）
- CLI suite（含 directed e88）
- FE：零产品改动 → vitest smoke + production build；确认 `frontend/src/router/routes/index.ts` 仍有 `/f/:token` + `/r/:token`（若 build 冲掉 elegant imports → checkout 恢复）
- 写满 acceptance（tip SHA + 门禁数 + Q1a–Q6a + superpowers 行）
- commit `docs(E88): acceptance`
- **STOP** — 不 push / 不开 PR / 不自开 E89

---

## Self-review
1. Spec coverage：A 无新路由 + smoke；C reorder + list position + api_client PUT + 1.72.0；B 零 FE；D 邻面不动；E 门禁 — 均有 task
2. Placeholder scan：无 TBD
3. Types：helper `reorder_favorites(ordered_ids: list[str])`；command `favorite reorder`；pins 1.72.0；**PUT** 一致
