# E7-S2 Shared Saved Views Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline; mid-epic no external acceptance ping). Steps use checkbox syntax.

**Goal:** Workspace-shared Saved Views: `is_shared` column, personal/shared list isolation, member+ create, creator+workspace-owner write, member Save As (personal copy), favorite remains personal-only; FE sections + share toggle + Save As; ⌘K continues to apply all accessible views.

**Architecture:** Extend `issue_saved_views` with `is_shared` (bool default false). `SavedViewService` gains `list_accessible` (personal mine + shared in WS), `get_accessible`, `assert_can_write_view`, `save_as`. List API returns `{ personal, shared, rows, total }` (`rows` = personal∪shared for compat). Cross-tenant / others' personal → 404. Viewer read-only on shared; cannot create/write/save-as.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, pytest+httpx, Vue3 + Naive UI, TypeScript, vitest.

## Global Constraints

- Worktree `/workspace/opentask-worktrees/E7-S2`, branch `sprint/E7-S2` from E7-S1 tip `b024ba2`; **no push**
- TDD: failing pytest (then FE vitest if needed) first
- Header `X-Workspace-Id` required; camelCase JSON
- Favorite: **personal only** (shared favorite → E8); POST favorite on shared → 403
- S2 **must not** add display prefs table or board swimlanes
- Mid-epic: do **not** ping Way/Yuri for acceptance

## File Map

| Layer | Path |
|---|---|
| Migration | `backend/alembic/versions/2026_11_04_0600-c3d4e5f6a7b9_saved_views_is_shared.py` (down_revision `b2c3d4e5f6a8`) |
| Model | `backend/opentask/models/issue_saved_view/model.py` |
| Service | `backend/opentask/services/saved_view/service.py` |
| API | `backend/opentask/api/saved_views/router.py` |
| Tests | `backend/tests/api/test_saved_views.py` (extend) |
| FE API | `frontend/src/service/api/saved-views.ts` |
| FE list | `frontend/src/views/issue/list/index.vue` |
| FE util test | `frontend/src/utils/saved-view-sections.test.ts` (+ helper if extracted) |
| Docs | sprint stub, acceptance, roadmap S2 closed |

## Permission matrix

| Action | personal (mine) | personal (other) | shared (creator) | shared (WS owner, not creator) | shared (member) | shared (viewer) |
|---|---|---|---|---|---|---|
| List / GET | yes | 404 / omit | yes | yes | yes | yes |
| PATCH / DELETE | yes | 404 | yes | yes | 403 | 403 |
| Favorite | yes | 404 | 403 | 403 | 403 | 403 |
| Save As | yes (copy) | 404 | yes → personal | yes → personal | yes → personal | 403 |
| Create is_shared | member+ | — | — | — | — | 403 |

---

### Task 1: Pytest RED — shared views permissions

**Files:** Modify `backend/tests/api/test_saved_views.py`

- [x] Add helpers: `_add_member(..., role=)` like tags tests
- [x] Cover:
  1. `test_create_shared_view_listed_for_other_member` — A creates `is_shared=true`; B list has it in `shared` not `personal`; A personal empty of that id; serialize has `isShared: true`
  2. `test_list_personal_shared_isolation` — A personal + A shared; B sees only shared (+ B's own personal)
  3. `test_member_cannot_patch_others_personal` — 404
  4. `test_member_cannot_patch_shared_unless_creator` — non-creator member → 403; creator → 200
  5. `test_workspace_owner_can_patch_shared_created_by_member` — owner patches member's shared → 200
  6. `test_save_as_shared_creates_personal_copy` — B save-as A's shared → new personal for B; filter/sort/display deep-copied; `isShared=false`; original unchanged
  7. `test_viewer_can_get_shared_cannot_create_or_save_as` — GET ok; POST create 403; save-as 403
  8. `test_favorite_rejected_on_shared_view` — 403; personal favorite still works
  9. `test_shared_cross_workspace_invisible` — other WS member cannot see shared (403 header or empty)
  10. Update existing list assertions if response shape adds `personal`/`shared` (keep `rows` combined)

Response shape:
```json
{ "personal": [...], "shared": [...], "rows": [...], "total": N }
```

Serialize adds `"isShared": bool`.

- [x] Run RED: `cd backend && .venv/bin/pytest tests/api/test_saved_views.py -v --tb=short`
- [x] Commit tests + plan + sprint stub

### Task 2: Model + Alembic GREEN foundation

- [x] Add `is_shared: Mapped[bool]` default false; optional index `idx_saved_views_ws_shared`
- [x] Migration `c3d4e5f6a7b9` revises `b2c3d4e5f6a8`; idempotent inspect; server_default false; NOT NULL
- [x] Commit

### Task 3: Service + Router GREEN

- [x] `list_accessible` → (personal, shared)
- [x] `get_accessible` — mine personal OR shared in WS
- [x] `assert_can_write_view(view, *, user_id, member_role)` — personal: owner only; shared: owner_user_id or role==owner; else HTTPException 403 (caller uses 404 when not accessible)
- [x] `create(..., is_shared=False)` ; reject is_favorite=True when is_shared (force false)
- [x] `save_as(view, *, owner_user_id, name=None)` → new personal row
- [x] Router: require_writer on create/update/delete/save-as; favorite only personal accessible; update create/update bodies with `is_shared`
- [x] GREEN pytest test_saved_views
- [x] Commit

### Task 4: FE API + list UI + sections

- [x] Extend `SavedView` with `isShared`; list result `personal`/`shared`/`rows`; `fetchSaveAsSavedView`
- [x] Helper `partitionSavedViews` or use API sections; dropdown groups 「我的」/「共享」
- [x] Save modal: checkbox 「共享给工作区」; title adapts
- [x] When active view is shared and current user cannot write: show 「另存为」 instead of/in addition to update path; hide favorite for shared
- [x] Favorites chips: only personal favorites
- [x] loadSavedViews merges personal+shared into `savedViews` for apply/⌘K
- [x] Optional vitest: `partitionSavedViewOptions` builds group keys
- [x] lint + build
- [x] Commit

### Task 5: Gates + acceptance + close S2

- [x] Full pytest; vitest slice if any; lint 0 errors; build
- [x] Acceptance doc; sprint state=closed; roadmap S2 closed; Epic still active
- [x] **No push**

## Out of scope (leftover → S3)

- Display prefs table / personal default
- Board swimlanes / fields visibility UI
- Shared view favorites (E8)

## Self-review

- Design §4.3 / §5.2 / §6.2 mapped to Tasks 1–5
- Favorite personal-only explicit
- Cross-tenant + others' personal 404 covered
- No display prefs / swimlanes in S2
