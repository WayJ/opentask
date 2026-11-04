# E8-S3 Sidebar Favorites Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline; mid-epic no external acceptance ping). Steps use checkbox syntax. TDD required. **No push.** Do **not** start E12.

**Goal:** Personal sidebar Favorites (Project / Saved View / Issue) distinct from Saved View `is_favorite` star; pin/unpin/reorder; pin Project upserts watcher; Epic E8 local-complete.

**Architecture:** Alembic after `f6a7b8c9d0e2` creates polymorphic `favorites` table. `FavoriteService` validates targets in workspace, lists with lightweight target summaries, pins idempotently (project → upsert watcher; unpin does **not** unwatch), reorders by position. Top-level `/api/favorites`. FE: `FavoritesNav` between Logo and menu mount; pin actions on project-detail / issue-detail / saved-view menus; vitest helpers for sort/group/nav targets. **Does not** mutate `issue_saved_views.is_favorite`.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, pytest+httpx, Vue3 + Naive UI, vitest, pnpm.

## Global Constraints

- Worktree `/workspace/opentask-worktrees/E8-S3`, branch `sprint/E8-S3`; baseline tip includes E8-S2 `@4325b15` (+ stub `700f387`); **no push**
- TDD: failing test first
- Alembic `down_revision = f6a7b8c9d0e2`; new revision `a7b8c9d0e1f3`
- `target_type ∈ {project, saved_view, issue}`; personal scope `(workspace_id, user_id)`
- Unique `(workspace_id, user_id, target_type, target_id)`
- Pin project → upsert `project_watchers`; unpin ≠ unwatch
- Distinct copy: 「收藏到侧栏」 vs View 「星标」
- Out of scope: E12 invites/KEY-N/PGE, Slack, Initiatives, remote push

## File Map

| Layer | Path |
|---|---|
| Migration | `backend/alembic/versions/2026_11_04_1000-a7b8c9d0e1f3_favorites.py` |
| Model | `backend/opentask/models/favorite/` |
| Service | `backend/opentask/services/favorite/` |
| API | `backend/opentask/api/favorites/` + register in `app.py` |
| Tests | `backend/tests/api/test_favorites.py` |
| FE API | `frontend/src/service/api/favorites.ts` |
| FE utils | `frontend/src/utils/favorites.ts` (+ vitest) |
| FE sider | `frontend/src/layouts/modules/global-sider/FavoritesNav.vue` + `index.vue` |
| FE pages | `project-detail`, `issue/detail`, `issue/list` (pin ≠ star) |
| Docs | plan / sprint / acceptance / roadmap → Epic local-complete |

---

### Task 1: Docs

- [x] Write this plan; expand sprint stub Wave 1
- [x] Commit `docs(E8-S3): TDD plan for sidebar Favorites`

### Task 2: Pytest RED — favorites CRUD / ACL / pin→watcher

**Files:** Create `backend/tests/api/test_favorites.py`

**Interfaces:**
- `GET /api/favorites` → rows for current user+WS ordered by `position`, each with `target` summary `{id,type,name,code?}`
- `POST /api/favorites` body `{target_type, target_id}` → create or return existing (idempotent); project pin upserts watcher
- `PATCH /api/favorites/{id}` body `{position}` OR `PUT /api/favorites/reorder` body `{ordered_ids: string[]}`
- `DELETE /api/favorites/{id}` → remove; unpin project does **not** remove watcher
- Cross-user: other member cannot see/delete your favorites
- Cross-WS / missing target → 404; invalid `target_type` → 400
- Pinning saved_view does **not** flip `is_favorite`

- [x] Write failing tests (mirror `test_project_health` helpers)
- [x] Run `pytest tests/api/test_favorites.py -v` → FAIL (404/missing)
- [x] Commit RED tests

### Task 3: Models + Alembic GREEN foundation

- [x] Add `Favorite` model; export in `models/__init__.py`
- [x] Migration `a7b8c9d0e1f3` revises `f6a7b8c9d0e2`
- [x] Commit models + migration

### Task 4: Services + API GREEN

- [x] `FavoriteService`: list/add/remove/reorder; validate target in WS; serialize with summary; pin project → `ProjectWatcherService.watch`
- [x] Router `/api/favorites`; register in `app.py`
- [x] Run pytest file → PASS; commit

### Task 5: FE + vitest

- [x] `favorites.ts` API client + types
- [x] `utils/favorites.ts`: group/sort/nav path helpers + vitest
- [x] `FavoritesNav.vue` in `global-sider` (Logo ↔ menu); collapse = icons
- [x] Pin/Unpin on project-detail header, issue-detail header, saved-view menu (label 「收藏到侧栏」; do not call `/favorite` star API)
- [x] lint 0 errors; build; vitest favorites utils
- [x] Commit FE

### Task 6: Gates + Epic local-complete

- [x] Full pytest; eslint --quiet; build; vitest
- [x] Acceptance `docs/superpowers/acceptances/2026-11-04-E8-S3-acceptance.md`
- [x] Sprint S3 `state: closed`; roadmap S1–S3 closed; Epic **local-complete**; `merged-commit: null`
- [x] **No push**; **do not** start E12

## Acceptance criteria (S3 / Epic)

1. `favorites` table + unique constraint; Alembic after `f6a7b8c9d0e2`
2. List/add/remove/reorder APIs; personal only; target validated in WS
3. Pin project upserts watcher; unpin keeps watcher
4. Sidebar FavoritesNav navigates Project / Saved View / Issue
5. Pin UI ≠ View star (`is_favorite` unchanged by sidebar pin)
6. Gates green; Epic local-complete; no remote push; E12 not started
