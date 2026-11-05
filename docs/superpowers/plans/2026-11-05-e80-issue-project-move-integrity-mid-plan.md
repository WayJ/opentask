# E80 Plan：Issue project-move integrity mid · CLI 1.64.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`171ae4f`（全文 `171ae4ff5e31ee8336da2e22ed146060f4ccbc6a`；含 E80 design；E79 tip `d84f6e4` ⊂ HEAD）· 分支 `sprint/E80-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e80-issue-project-move-integrity-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E81**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** member+ 将 Issue 换到另一 Project（或清空 Project）后，**不会**再持有不属于新 Project 的 `milestone_id`；duplicate 跨项目 override 不抄旧 milestone；FE 换项目后里程碑 UI 一致；CLI **1.64.0** `issue update --project`/`--milestone`/`--clear-milestone`；viewer 写 403；跨租户 404；**不**清 cycle；无新 webhook 名；formula no-emit；不重开 E63–E79。

**Architecture:** 纯函数 helper `apply_project_move_integrity` + `milestone_for_duplicate`；`update_issue` 在 project_id 值变时注入 `milestone_id=None`（除非同请求显式 milestone），timeline `project_changed.action_data` 扩 `milestone_cleared`/`milestone_from`；duplicate create_payload 跨项目不抄 milestone；FE `nextMilestoneAfterProjectMove` + saveProject 清本地；CLI pins 1.64.0。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E81；中文 docs；CLI **1.64.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：值变即清 · 显式合法 milestone 优先（非法 400）· duplicate 跨项目不抄 · 读不改库 · 扩 project_changed.action_data · CLI 1.64.0
- **不清** `cycle_id`；无新表 / 无新 timeline enum / 无新 webhook 名
- 共用 helper 覆盖一切改 `project_id` 写路径（本轮：`update_issue` + `duplicate_issue`；board-move 不改 project）
- 不改 E79 lead/members、E78 parent、E77 trash、E76 links 主表面；E75 duplicate 仅修跨项目 milestone 边
- 不改 E70 childProgress / E72 template apply；formula 永不 emit；无 Activity Push / 无门户 / 无甘特
- 不改 E63–E79 邻面主表面（仅 CLI version pins）
- 已知 flake `test_user_search`（及序污染）记入 acceptance，不挡
- 非目标见 design §2

## File map
| Path | Role |
|------|------|
| `backend/opentask/services/issue_project_move.py` | `apply_project_move_integrity` + `milestone_for_duplicate` |
| `backend/opentask/services/issue_service.py` | update + duplicate 接入；timeline action_data 扩字段 |
| `backend/tests/api/test_e80_issue_project_move.py` | API TDD |
| `backend/tests/services/test_issue_project_move.py` | 纯函数单测（可选合入 API 文件旁） |
| `frontend/src/utils/nextMilestoneAfterProjectMove.ts` (+test) | FE 纯 helper |
| `frontend/src/views/issue/detail/index.vue` | saveProject 清 milestone + loadMilestones + 轻提示 |
| `agent-harness/opentask-cli/**` | 1.64.0 + `issue update --project|--milestone|--clear-milestone` |
| `docs/superpowers/acceptances/2026-11-05-e80-issue-project-move-integrity-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e80-issue-project-move-integrity-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e80-issue-project-move-integrity-mid-acceptance.md
git commit -m "docs(E80): plan + acceptance skeleton"
```

---

### Task 2 — A：纯 helper `apply_project_move_integrity` / `milestone_for_duplicate`（TDD）

**Files:**
- Create: `backend/opentask/services/issue_project_move.py`
- Create: `backend/tests/services/test_issue_project_move.py`（或并入 API 测文件前的 unit）

**Interfaces:**
```python
@dataclass
class ProjectMoveIntegrityResult:
    milestone_cleared: bool = False
    milestone_from: str | None = None

def apply_project_move_integrity(
    update_data: dict,
    *,
    existing_project_id: str | None,
    existing_milestone_id: str | None,
) -> ProjectMoveIntegrityResult:
    """Q1a/Q2a: if project_id in update_data and value ≠ existing →
    if 'milestone_id' not in update_data: set milestone_id=None;
    if existing_milestone_id: mark cleared + milestone_from.
    Same-value project re-submit → no-op (do not clear).
    Explicit milestone_id in payload → leave for caller validation (Q2a).
    Never touches cycle_id.
    """

def milestone_for_duplicate(
    *,
    source_project_id: str | None,
    target_project_id: str | None,
    source_milestone_id: str | None,
) -> str | None:
    """Q3a: same project → copy; else None."""
```

- [ ] **Step 1:** Write failing unit tests (same-value no-clear; A→B clears; A→null clears; explicit milestone kept in dict; duplicate same/cross)
- [ ] **Step 2:** Run → FAIL (module missing)
- [ ] **Step 3:** Implement helper
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E80): project-move integrity helper`

---

### Task 3 — A：update_issue + duplicate + timeline action_data（TDD）

**Files:**
- Modify: `backend/opentask/services/issue_service.py`
- Create: `backend/tests/api/test_e80_issue_project_move.py`

**Wire-in (update_issue):**
1. After building `update_data`, if `"project_id" in update_data`: load existing (or reuse)
2. `meta = apply_project_move_integrity(update_data, existing_project_id=..., existing_milestone_id=...)`
3. Existing `_validate_milestone_id` still runs when `"milestone_id" in update_data` against **new** project
4. When writing `project_changed` timeline, if `meta.milestone_cleared`: action_data += `milestone_cleared: True`, `milestone_from: meta.milestone_from`
5. Do **not** clear `cycle_id`; do **not** add new webhook event name

**Wire-in (duplicate_issue):**
```python
"milestone_id": milestone_for_duplicate(
    source_project_id=source.project_id,
    target_project_id=project_id,
    source_milestone_id=source.milestone_id,
),
```

**API tests (at least):**
- PATCH/PUT only `project_id` A→B with milestone on A → response/DB `milestone_id is None`; `cycle_id` unchanged
- Same request `project_id=B, milestone_id=<B's ms>` → keeps that ms
- `project_id=B, milestone_id=<A's ms>` → 400
- project→null → milestone null
- same-value project re-submit → milestone unchanged
- duplicate with override project ≠ source → new issue milestone null
- timeline `project_changed.action_data` has `milestone_cleared` when cleared
- spy: webhook events only known names (no new); viewer write 403

- [ ] **Step 1:** Write failing API tests
- [ ] **Step 2:** Run directed → FAIL
- [ ] **Step 3:** Wire service
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E80): clear invalid milestone on project move + duplicate edge`

---

### Task 4 — B：FE helper + saveProject UX（TDD）

**Files:**
- Create: `frontend/src/utils/nextMilestoneAfterProjectMove.ts`
- Create: `frontend/src/utils/nextMilestoneAfterProjectMove.test.ts`
- Modify: `frontend/src/views/issue/detail/index.vue` (`saveProject`)

```typescript
export function nextMilestoneAfterProjectMove(
  oldProjectId: string | null | undefined,
  newProjectId: string | null | undefined,
  milestoneId: string | null | undefined,
): string | null {
  const a = oldProjectId ?? null;
  const b = newProjectId ?? null;
  if (a === b) return milestoneId ?? null;
  return null;
}

export function projectMoveClearedMessage(
  oldProjectId: string | null | undefined,
  newProjectId: string | null | undefined,
  hadMilestone: boolean,
): string | null {
  if (!hadMilestone) return null;
  if ((oldProjectId ?? null) === (newProjectId ?? null)) return null;
  return '已清除原项目里程碑';
}
```

`saveProject`: after success → set `tempMilestone` via helper; `loadMilestones(newPid)`; optional message; use `project_id: tempProject.value || null` (allow clear).

- [ ] **Step 1:** vitest failing
- [ ] **Step 2:** implement helper + wire vue
- [ ] **Step 3:** vitest PASS；confirm elegant-router `f`+`r` still present
- [ ] **Step 4:** commit `feat(E80): FE clear milestone UI after project move`

---

### Task 5 — C：CLI 1.64.0

**Files:**
- Modify: `VERSION` / `pyproject.toml` / `setup.py` / `__init__.py` / `opentask_cli.py` → **1.64.0**
- Cascade 历史 epic 测试里的 `1.63.0` → `1.64.0`
- Modify: `opentask/core/issue.py` `update` — add `--project` / `--milestone` / `--clear-milestone`
- Create: `agent-harness/opentask-cli/tests/test_e80_issue_project_move.py`

```python
@click.option("--project", "project_id", default=None,
              help="E80: set project_id (empty string clears)")
@click.option("--milestone", "milestone_id", default=None, help="E80: set milestone_id")
@click.option("--clear-milestone", is_flag=True, help="E80: clear milestone_id")
```

Semantics:
- `--project` present (incl. `""`) → kwargs `project_id` = value or None
- `--clear-milestone` → `milestone_id=None`; conflict with `--milestone` → error
- Output (verbose or json) shows `project_id` + `milestone_id`
- Directed mock test: `--project B` after issue had milestone → update called with project_id; assert response milestone cleared when mock returns null

- [ ] **Step 1:** failing CLI tests
- [ ] **Step 2:** implement + pin cascade
- [ ] **Step 3:** CLI suite PASS
- [ ] **Step 4:** commit `feat(E80): CLI 1.64.0 issue update --project|--milestone`

---

### Task 6 — verify + acceptance

- [ ] Directed E80 BE PASS
- [ ] Full BE suite（document flake）
- [ ] CLI suite PASS
- [ ] FE vitest PASS + production build ok；`f`+`r` 在位
- [ ] Fill acceptance with tip SHA + gate counts + `superpowers: design/plan/TDD/verify/acceptance = ok`
- [ ] commit `docs(E80): acceptance`
- [ ] **STOP** — 不 push / 不开 PR / 不自开 E81

## Self-review
- Spec A–G → Tasks 2–6 cover
- Q1a–Q6a locked; cycle never cleared
- No placeholders; helper covers update + duplicate
