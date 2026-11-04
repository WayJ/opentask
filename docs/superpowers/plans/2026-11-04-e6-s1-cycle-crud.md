# E6-S1 Cycle CRUD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline; mid-epic no external acceptance ping). Steps use checkbox syntax.

**Goal:** Deliver Workspace-scoped `cycles` table + workspace Cycles settings columns + `/api/cycles` CRUD (+ activate) + Cycles settings UI (enable / list / create upcoming). No `Issue.cycle_id`.

**Architecture:** Mirror Saved Views / Workspace patterns: SQLAlchemy model + Alembic (revises `e1f2a3b4c5d6`) → `CycleService` → FastAPI `/api/cycles` with `require_workspace_context` → FE `service/api/cycles.ts` + `/workspace/cycles` settings page. Owner-only workspace `cycles_*` settings via extended `PATCH /api/workspaces/{id}`.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, pytest+httpx, Vue3 + Naive UI + soybean elegant-router, TypeScript.

## Global Constraints

- Worktree `/workspace/opentask-worktrees/E6-S1`, branch `sprint/E6-S1`; **no push**
- TDD: failing pytest first for API behaviors
- Header `X-Workspace-Id` required on cycle APIs; cross-tenant 403/404
- Write Cycle: member+; settings toggle: owner; viewer read-only
- Delete only `upcoming`; at most one `active` per workspace
- S1 **must not** add `issues.cycle_id` / estimate_points / rollover / capacity / ⌘K cycle
- camelCase JSON responses (match Saved Views / Workspace)
- Mid-epic: do **not** ping Way/Yuri for acceptance

## File Map

| Layer | Path |
|---|---|
| Migration | `backend/alembic/versions/2026_11_04_0300-f0e1d2c3b4a5_cycles_and_workspace_settings.py` |
| Model | `backend/opentask/models/cycle/model.py` + `__init__.py` |
| Models export | `backend/opentask/models/__init__.py` |
| Workspace model | `backend/opentask/models/workspace/model.py` (+ 4 columns) |
| Workspace schema | `backend/opentask/schemas/workspace.py` |
| Workspace service/router | `backend/opentask/services/workspace/service.py`, `api/workspace/router.py` |
| Cycle service | `backend/opentask/services/cycle/service.py` + `__init__.py` |
| Cycle API | `backend/opentask/api/cycles/router.py` + `__init__.py` |
| App | `backend/opentask/app.py` |
| Tests | `backend/tests/api/test_cycles.py` |
| FE API | `frontend/src/service/api/cycles.ts` + `workspace.ts` + `index.ts` |
| FE page | `frontend/src/views/workspace/cycles/index.vue` |
| Router/i18n | `frontend/src/router/elegant/routes.ts`, `imports.ts`, `typings/elegant-router.d.ts`, locales |

---

### Task 1: Pytest RED — Cycle CRUD + settings + isolation

**Files:**
- Create: `backend/tests/api/test_cycles.py`

- [ ] **Step 1: Write failing tests**

Cover:
1. `test_create_and_list_cycles` — POST upcoming → list contains id; GET by id
2. `test_cycles_cross_workspace_isolation` — B cannot read A's cycle (403 header or 404 get)
3. `test_delete_upcoming_cycle` — DELETE upcoming → gone
4. `test_refuse_delete_active_cycle` — activate then DELETE → 4xx
5. `test_activate_enforces_single_active` — second activate while one active → 400
6. `test_update_cycle_name_and_dates` — PATCH upcoming
7. `test_cycles_require_workspace_header` — missing header 400; foreign ws 403
8. `test_viewer_cannot_create_cycle` — add viewer member; POST → 403
9. `test_owner_patch_cycles_enabled` — PATCH workspace `cyclesEnabled` persists on GET
10. `test_member_cannot_patch_cycle_settings` — member PATCH cyclesEnabled → 403
11. `test_create_rejects_ends_before_starts` — 400

Helpers mirror `test_saved_views.py` (`_register`, `_auth`, `_add_member`).

Cycle create body:
```json
{ "name": "Cycle 1", "starts_at": "2026-11-04T00:00:00", "ends_at": "2026-11-18T00:00:00" }
```
Response fields camelCase: `id`, `workspaceId`, `name`, `number`, `status`, `startsAt`, `endsAt`, `completedAt`, `createdAt`, `updatedAt`.

Workspace settings fields on WorkspaceOut: `cyclesEnabled`, `cycleDurationDays`, `cycleRolloverPolicy`, `cycleCapacityLookback`.

- [ ] **Step 2: Run to verify RED**

```bash
cd backend && uv run pytest tests/api/test_cycles.py -v --tb=short
```
Expected: import/collection OK or FAIL (404 / AttributeError) — no silent pass.

- [ ] **Step 3: Commit tests only**

```bash
git add backend/tests/api/test_cycles.py docs/superpowers/plans/2026-11-04-e6-s1-cycle-crud.md
git commit -m "test(E6-S1): red — cycles CRUD + settings + isolation"
```

---

### Task 2: Model + Alembic + Workspace columns

**Files:**
- Create model/migration as File Map
- Modify workspace model + schemas + `_ws_out` + `WorkspaceUpdate` + `WorkspaceService.update`

- [ ] **Step 1: Cycle model**

```python
# backend/opentask/models/cycle/model.py
class Cycle(DBModel):
    __tablename__ = "cycles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, insert_default="upcoming")  # upcoming|active|completed
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at / updated_at as usual
    __table_args__ = (
        Index("idx_cycles_ws_status", "workspace_id", "status"),
        Index("idx_cycles_ws_starts", "workspace_id", "starts_at"),
    )
```

- [ ] **Step 2: Workspace columns on model**

```python
cycles_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=False, server_default=sa_false_or_text)
cycle_duration_days: Mapped[int] = mapped_column(Integer, nullable=False, insert_default=14, server_default="14")
cycle_rollover_policy: Mapped[str] = mapped_column(String(32), nullable=False, insert_default="into_next", server_default="into_next")
cycle_capacity_lookback: Mapped[int] = mapped_column(Integer, nullable=False, insert_default=3, server_default="3")
```

Use `from sqlalchemy import Boolean, Integer` and `server_default=sa.false()` / `sa.text('14')` style consistent with other migrations.

- [ ] **Step 3: Migration `f0e1d2c3b4a5` revises `e1f2a3b4c5d6`**

inspect-if-exists for table + columns (copy saved_views / parent_issue_id style).

- [ ] **Step 4: Register Cycle in `models/__init__.py`**

- [ ] **Step 5: Extend WorkspaceUpdate + `_ws_out` + service.update** for the four fields (owner already required by update).

Validate `cycle_rollover_policy ∈ {into_next, leave_unassigned}`; duration/lookback positive ints.

- [ ] **Step 6: Commit**

```bash
git commit -m "feat(E6-S1): cycles table + workspace cycle settings columns"
```

---

### Task 3: CycleService + API router (GREEN)

**Files:** service + api/cycles + app.py

**Interfaces:**
- `CycleService.list(workspace_id, status=None) -> list[Cycle]`
- `get(id, workspace_id) -> Cycle | None`
- `create(..., name?, starts_at, ends_at, status='upcoming')`
- `update(cycle, name?, starts_at?, ends_at?)` — if status==completed: only name (or reject date changes with 400)
- `delete(cycle)` — raises 400 unless upcoming
- `activate(cycle)` — raises 400 if not upcoming or another active exists
- `serialize_cycle(c) -> dict` camelCase
- `require_writer(member)` — role in {owner, member}

Router paths:
- `GET /api/cycles?status=`
- `POST /api/cycles`
- `GET /api/cycles/{id}`
- `PATCH /api/cycles/{id}`
- `DELETE /api/cycles/{id}`
- `POST /api/cycles/{id}/activate`

Auto `number`: max(number)+1 in workspace (nullable ok).

Default name if omitted: `Cycle {number}`.

- [ ] **Step 1: Implement service + router + register**
- [ ] **Step 2: Run `uv run pytest tests/api/test_cycles.py -v` → all green**
- [ ] **Step 3: Commit** `feat(E6-S1): /api/cycles CRUD + activate`

---

### Task 4: Frontend API + Cycles settings page

**Files:** as File Map

- [ ] **Step 1: `cycles.ts`** — types + fetchList/Create/Update/Delete/Activate
- [ ] **Step 2: Extend `WorkspaceItem` + `fetchUpdateWorkspace`** for cycle settings fields
- [ ] **Step 3: Page `views/workspace/cycles/index.vue`**
  - Load workspace + cycles
  - If `!cyclesEnabled`: empty state + CTA enable (owner)
  - Else: Switch enabled, duration/rollover/lookback form (owner writable), table, Create upcoming modal (defaults starts=today, ends=starts+durationDays)
  - Delete upcoming; Activate button for upcoming when no active
- [ ] **Step 4: Wire elegant-router** — add route `workspace_cycles` path `/workspace/cycles` (parent `workspace` or top-level like inbox with `hideInMenu: false` or true + reachable). Prefer:
  ```ts
  { name: 'workspace_cycles', path: '/workspace/cycles', component: 'layout.base$view.workspace_cycles', meta: { title: 'Cycles', i18nKey: 'route.workspace_cycles', icon: 'mdi:reload', order: 3.5 } }
  ```
  Update `imports.ts` + `elegant-router.d.ts` + zh-cn/en-us `route.workspace_cycles`.
- [ ] **Step 5: `npm run lint` (0 errors) && `npm run build`**
- [ ] **Step 6: Commit** `feat(E6-S1): Cycles settings UI + API client`

---

### Task 5: Full gates + acceptance + close S1 (Epic stays active)

- [ ] **Step 1:** `cd backend && uv run pytest tests/ -v` — prior ~621 + new cycle tests all green
- [ ] **Step 2:** FE lint + build already green
- [ ] **Step 3:** Write `docs/superpowers/acceptances/2026-11-04-E6-S1-acceptance.md` with scenario evidence + fingerprint SHA
- [ ] **Step 4:** Update sprint frontmatter `state: closed`, roadmap S1 `closed`, Epic **still active**; checkboxes
- [ ] **Step 5:** Commit docs `docs(E6-S1): acceptance + close sprint (epic active)`
- [ ] **Step 6:** Confirm `git status` clean enough; **do not push**

## Out of scope (leftover S2/S3)

- S2: `Issue.cycle_id`, estimate_points, list/board filter, assign UI, ⌘K cycle kind
- S3: complete/rollover, capacity-hint, generate-upcoming polish, Epic local-complete

## Self-review

- Spec S1 rows covered: table, workspace cols, CRUD, activate, settings UI, enable empty state
- No Issue.cycle_id in this plan
- Filename matches user brief: `e6-s1-cycle-crud.md`
