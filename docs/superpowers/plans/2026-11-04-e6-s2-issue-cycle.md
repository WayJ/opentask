# E6-S2 Issue.cycle_id Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline; mid-epic no external acceptance ping). Steps use checkbox syntax.

**Goal:** Attach Issues to Workspace Cycles (`cycle_id` + optional `estimate_points`), filter list/board by Cycle, assign from detail UI, and extend ⌘K with `kind=cycle`.

**Architecture:** Alembic adds nullable FK + points on `issues` → Pydantic/Service validate same-workspace Cycle → Issue list query `cycle_id` (UUID or `__none__`) → FE filters + EditableField assign → palette entity group via `fetchCycles`.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, pytest+httpx, Vue3 + Naive UI, vitest.

## Global Constraints

- Worktree `/workspace/opentask-worktrees/E6-S2`, branch `sprint/E6-S2`; **no push**
- Baseline: `sprint/E6-S1` tip `15b95ea` (impl `bd22f89`); migration down_revision `f0e1d2c3b4a5`
- TDD: failing pytest/vitest first
- Cross-tenant: Cycle must belong to Issue's workspace
- Keep `estimated_hours`; add optional `estimate_points`
- No complete/rollover/capacity/generate-upcoming/Jira sprint
- Mid-epic: do **not** ping Way/Yuri

## File Map

| Layer | Path |
|---|---|
| Migration | `backend/alembic/versions/2026_11_04_0400-a1b2c3d4e5f7_issue_cycle_id.py` (rev `a1b2c3d4e5f7`) |
| Model | `backend/opentask/models/issue/model.py` |
| Schema | `backend/opentask/models/issue/schema.py` |
| Service | `backend/opentask/services/issue_service.py` |
| Router | `backend/opentask/api/issue/router.py` |
| Tests | `backend/tests/api/test_issue_cycle.py` |
| FE types | `frontend/src/typings/api/issue.d.ts` |
| FE API | `frontend/src/service/api/issue.ts` (params only if needed) |
| FE list | `frontend/src/views/issue/list/index.vue` |
| FE detail | `frontend/src/views/issue/detail/index.vue` |
| Palette | `command-palette.ts`, `command-palette-entities.ts`, `use-command-palette.ts`, `command-palette-host.vue` + tests |
| Docs | plans/sprints/acceptances/roadmap |

---

### Task 1: Pytest RED — Issue ↔ Cycle

**Files:** Create `backend/tests/api/test_issue_cycle.py`

- [ ] **Step 1: Write failing tests**

1. `test_create_issue_with_cycle_id` — create cycle, POST issue with cycle_id → response has it; GET returns it
2. `test_update_issue_cycle_id_and_clear` — PATCH cycle_id then PATCH null
3. `test_list_issues_filter_by_cycle_id` — two issues different cycles; filter returns one
4. `test_list_issues_filter_none_cycle` — `cycle_id=__none__` returns only unassigned
5. `test_reject_cross_workspace_cycle` — Cycle in A, Issue workspace B → 400
6. `test_create_with_estimate_points` — optional points round-trip; estimated_hours still ok

Helpers: mirror `test_sub_issues` / `test_cycles` (`_register`, `_auth`, `_create_issue`, `_create_cycle`).

- [ ] **Step 2: Run RED** `cd backend && .venv/bin/pytest tests/api/test_issue_cycle.py -v --tb=short`
- [ ] **Step 3: Commit** `test(E6-S2): red — issue cycle_id + filter + isolation`

---

### Task 2: Migration + model + schema

- [ ] Add columns on Issue model:
  - `cycle_id` String(36) FK cycles.id ON DELETE SET NULL, index
  - `estimate_points` Numeric(8,2) nullable
  - Index `idx_issues_cycle`
- [ ] Migration `a1b2c3d4e5f7` revises `f0e1d2c3b4a5`, inspect-if-exists
- [ ] Schema: IssueBase / IssueUpdate / IssueResponse inherit; IssueQueryParams.cycle_id Optional[str]
- [ ] Commit `feat(E6-S2): issues.cycle_id + estimate_points migration`

---

### Task 3: Service + router GREEN

- [ ] `_validate_cycle_id(cycle_id, workspace_id)`: None ok; else Cycle exists and `workspace_id` matches; else ValueError
- [ ] Call from create_issue / update_issue when cycle_id present (incl. explicit null skip validate)
- [ ] `get_issues`: if params.cycle_id == `__none__` → `Issue.cycle_id.is_(None)`; elif set → equality
- [ ] Router GET: add Query `cycle_id`; pass into IssueQueryParams
- [ ] Run pytest GREEN; commit `feat(E6-S2): issue cycle_id API filter + validation`

---

### Task 4: FE list/board filter + detail assign

- [ ] Types: `cycle_id`, `estimate_points` on IssueBase/UpdateIssue/IssueQueryParams
- [ ] list/index.vue: `filters.cycle_id`; load `fetchCycles`; NSelect options 全部(clear)/无 Cycle(`__none__`)/cycles; wire query `?cycle_id=`; client filter + API params; board shares filteredIssues
- [ ] detail: EditableField Cycle NSelect; save via updateIssue `{ cycle_id }`
- [ ] Commit `feat(E6-S2): FE cycle filter + detail assign`

---

### Task 5: ⌘K cycle kind

- [ ] `PaletteItemKind` += `'cycle'`
- [ ] `buildPaletteGroups` + `setEntitySources` + groupLabels.cycles
- [ ] `cyclesToPaletteItems(cycles, navigate)` → `/issue/list?cycle_id=`
- [ ] host: fetchCycles + filterByNameQuery when q
- [ ] vitest updates; commit `feat(E6-S2): command palette cycle group`

---

### Task 6: Gates + acceptance

- [ ] Full pytest; npm lint (0 errors); npm build
- [ ] Acceptance + close sprint; roadmap S2 closed; Epic active; **no push**
