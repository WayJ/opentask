# E89 Plan：Custom Fields Reorder CLI mid · CLI 1.73.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`dc4779c`（全文 `dc4779c6de9d5dd892c25c76a9deea3466162888`；含 E89 design；E88 tip `d09142c` ⊂ HEAD）· 分支 `sprint/E89-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e89-custom-fields-reorder-cli-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E90**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** writer+ 可用 CLI **1.73.0** 做 `custom-field reorder --ids …`（可选位置参数）；api_client 有 `reorder_custom_fields` → **POST** `/api/custom-fields/reorder` body **`orderedIds`**；**不**改 list（已有 Pos）；**不**改 E88 favorite reorder / E87 tag-group / E86 label set/multi / E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead；**无**新 webhook/表/**无新 BE 路由**；formula no-emit；零产品 FE；不重开 E63–E88。

**Architecture:** 复用既有 `POST /api/custom-fields/reorder` body `{orderedIds}`（Q1a；**非 PUT**、**非** `ordered_ids`）；CLI 挂 `custom-field reorder`（Q2a）；`--ids` 为主 + 可选位置参数（Q3a）；list 不动（Q4a）；pins 1.73.0（Q5a）；FE 零改（Q6a）。语义对齐既有 BE **软更新**（命中 id 写 position；未命中忽略；**勿**套 Favorites 全集 400）。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E90；中文 docs；CLI **1.73.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：无新路由 · `custom-field reorder` · `--ids` 为主 · 不改 list · pins 1.73.0 · 零产品 FE
- **不**改 E88 favorite reorder / E87 tag-group / E86 set/multi / project-health / cycle / project-watchers / issue-template / milestone / `apply_project_move_integrity` / lead-members；**不**改 `custom-field create|update|validate-formula` 默认行为
- 无新 webhook / 无新表 / 无 alembic / **无新 BE 路由**；formula 永不 emit；无 Activity Push / 无门户 / 无甘特
- 守 E63 `f`+`r`；已知 flake `test_user_search` 记入 acceptance，不挡
- **务必** POST（非 PUT）+ JSON key **`orderedIds`**（camelCase；勿发 `ordered_ids`）
- **勿**把 Favorites「必须覆盖当前全部，否则 400」硬套到本端点

## File map
| Path | Role |
|------|------|
| `agent-harness/opentask-cli/opentask/utils/api_client.py` | `reorder_custom_fields(ordered_ids)` → POST + `orderedIds` |
| `agent-harness/opentask-cli/opentask/core/custom_field.py` | `custom-field reorder`（list 不动） |
| VERSION / pyproject / setup / `__init__` / `opentask_cli.VERSION` | pins **1.73.0** + 历史 epic 断言级联 `1.72.0`→`1.73.0` |
| `agent-harness/opentask-cli/tests/test_e89_custom_fields_reorder.py` | CLI TDD |
| `backend/tests/api/test_e89_custom_fields_reorder_cli_mid.py` | 邻面 spy + POST reorder 端点存在性 |
| `docs/superpowers/acceptances/2026-11-05-e89-custom-fields-reorder-cli-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e89-custom-fields-reorder-cli-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e89-custom-fields-reorder-cli-mid-acceptance.md
git commit -m "docs(E89): plan + acceptance skeleton"
```

---

### Task 2 — C：CLI api_client reorder_custom_fields + custom-field reorder + pins 1.73.0（TDD）

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`（Custom Fields 段追加 `reorder_custom_fields`）
- Modify: `agent-harness/opentask-cli/opentask/core/custom_field.py`
- Modify: VERSION / pyproject.toml / setup.py / `__init__.py` / `opentask_cli.py` → **1.73.0**
- Cascade 历史 epic 测试里的 `1.72.0` → `1.73.0`
- Create: `agent-harness/opentask-cli/tests/test_e89_custom_fields_reorder.py`

**Interfaces (api_client):**
```python
async def reorder_custom_fields(self, ordered_ids: list[str]) -> dict:
    """E89: POST /api/custom-fields/reorder — soft update positions by orderedIds (unknown ids ignored)."""
    return await self.post(
        "/api/custom-fields/reorder",
        data={"orderedIds": list(ordered_ids)},
    )
```

**CLI commands:**
```python
def _parse_ordered_ids(ids_csv: str | None, positional: tuple[str, ...] | None) -> list[str]:
    ids: list[str] = []
    if ids_csv is not None and str(ids_csv).strip() != "":
        ids.extend([p.strip() for p in str(ids_csv).split(",") if p.strip()])
    for p in positional or ():
        s = str(p).strip()
        if s:
            ids.append(s)
    return ids

@custom_field_cli.command(name="reorder")
@click.option("--ids", "ids_csv", default=None, help="Comma-separated custom-field ids in new order")
@click.argument("positional_ids", nargs=-1)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def custom_field_reorder(obj, ids_csv, positional_ids, as_json):
    # require_workspace_id; parse ids; if empty → ClickException
    # client.reorder_custom_fields(ordered_ids)
    # json → echo_json; human → success "顺序已更新"
```

**Tests (at least):**
- `hasattr` `reorder_custom_fields`；source 含 `self.post` + `/api/custom-fields/reorder` + `orderedIds`；**禁** `self.put` / `ordered_ids` 作为 JSON key
- `custom-field --help` 含 `reorder`；`custom-field reorder --help` 含 `--ids`
- `custom-field reorder --ids a,b,c --json` → `reorder_custom_fields(["a","b","c"])`
- `custom-field reorder id1 id2 --json`（位置参数）→ `reorder_custom_fields(["id1","id2"])`
- 无 `--ids` 且无位置参数 → exit ≠ 0
- pins 1.73.0（VERSION + pyproject + setup + `__init__` + `--version`）
- **不**断言改 list（Q4a）

- [ ] **Step 1:** Write failing CLI tests
- [ ] **Step 2:** Run directed → FAIL（缺 helper/command / pins 仍 1.72.0）
- [ ] **Step 3:** Implement helper + command + pins cascade
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E89): CLI 1.73.0 custom-field reorder`

---

### Task 3 — A：BE 邻面 spy + 既有 custom-fields POST reorder 端点存在性

**Files:**
- Create: `backend/tests/api/test_e89_custom_fields_reorder_cli_mid.py`

**Tests:**
- spy：`api/custom_fields/router.py` 仍含 `@router.post("/reorder")` + `async def reorder_custom_fields` + `class CustomFieldReorder` + `orderedIds`；**无** `@router.put("/reorder")`
- service soft-update：`CustomFieldService.reorder` 源码含 `if fid in by_id`（未命中忽略）；**不**强制全集
- 无 alembic 新文件命名 e89
- 邻面 markers 仍在（favorites PUT reorder / tag-groups / replace_tags / project health / cycles generate-upcoming / project_watcher enrich / issue_templates / milestone / issue_project_move / E86 update_tag）
- formula no-emit soft guard
- 附跑既有：`tests/api/test_custom_fields.py` smoke

- [ ] **Step 1:** Write spy tests
- [ ] **Step 2–4:** 绿
- [ ] **Step 5:** commit `test(E89): BE custom-fields-reorder mid spy`

---

### Task 4 — E：门禁 + acceptance

- Directed BE：`test_e89_custom_fields_reorder_cli_mid.py` + `test_custom_fields.py`
- Full BE `pytest tests`（flake 记入）
- CLI suite（含 directed e89）
- FE：零产品改动 → vitest smoke + production build；确认 `frontend/src/router/routes/index.ts` 仍有 `/f/:token` + `/r/:token`（若 build 冲掉 elegant imports → checkout 恢复）
- 写满 acceptance（tip SHA + 门禁数 + Q1a–Q6a + superpowers 行；**勿留** `_pending_`/骨架）
- commit `docs(E89): acceptance`
- **STOP** — 不 push / 不开 PR / 不自开 E90

---

## Self-review
1. Spec coverage：A 无新路由 + soft + soft-update；C reorder + api_client POST/`orderedIds` + 1.73.0；B 零 FE；D 邻面不动；E 门禁 — 均有 task
2. Placeholder scan：无 TBD
3. Types：helper `reorder_custom_fields(ordered_ids: list[str])`；command `custom-field reorder`；pins 1.73.0；**POST** + **`orderedIds`** 一致；与 E88 PUT/`ordered_ids` 刻意不同
