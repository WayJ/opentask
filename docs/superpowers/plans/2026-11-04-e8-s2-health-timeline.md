# E8-S2 Health + Watchers + Inbox + Timeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline; mid-epic no external acceptance ping). Steps use checkbox syntax. TDD required. **No push.**

**Goal:** Deliver project health updates (history + cache), `project_watchers`, Inbox fanout (`type=project_health`), and Timeline MVP (week/month + empty-state) on project-detail. No Favorites (→ S3).

**Architecture:** Alembic after `e5f6a7b8c9d1` adds health cache cols + `project_health_updates` + `project_watchers`. `ProjectHealthService` posts updates (write history, refresh project cache, fanout via `NotificationService.create`). `ProjectWatcherService` lists/watch/unwatch; project create auto-watches actor. Timeline GET aggregates project dates + milestones + due-dated issues. FE: header badge, update/history, watch toggle, Timeline tab with zoom helpers.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, pytest+httpx, Vue3 + Naive UI, vitest.

## Global Constraints

- Worktree `/workspace/opentask-worktrees/E8-S2`, branch `sprint/E8-S2`; baseline `sprint/E8-S1` tip `97a53af`; **no push**
- TDD: failing test first
- Alembic `down_revision = e5f6a7b8c9d1`; new revision `f6a7b8c9d0e2`
- Health enum: `on_track` | `at_risk` | `off_track`; history field `note` (design); cache `health_status/note/updated_at/updated_by`
- Inbox: `type=project_health`, `resource_type=project`; skip actor; no Slack
- Out of scope: Favorites (S3), Slack, Initiatives, remote push, mid-epic Way/Yuri ping, starting E12

## File Map

| Layer | Path |
|---|---|
| Migration | `backend/alembic/versions/2026_11_04_0900-f6a7b8c9d0e2_project_health_watchers.py` |
| Models | `backend/opentask/models/project_health/`, `project_watcher/` (+ Project health_* cols) |
| Services | `backend/opentask/services/project_health/`, `project_watcher/` |
| Notification | extend comment + `notify_project_health` helper |
| API | nested routers on `api/project/router.py` |
| Project create | auto-watch actor when workspace present |
| Tests | `backend/tests/api/test_project_health.py` |
| FE API/types | `frontend/src/service/api/project.ts`, `typings/api/project.d.ts` |
| FE utils | `frontend/src/utils/project-timeline.ts` (+ vitest) |
| FE pages | `project-detail/index.vue`, `inbox/index.vue` |
| Docs | plan / sprint / acceptance / roadmap |

---

### Task 1: Docs

- [x] Write this plan; mark sprint Wave 1 TDD plan checkbox
- [x] Commit `docs(E8-S2): TDD plan for health, watchers, timeline`

### Task 2: Pytest RED — health / watchers / timeline / inbox

**Files:** Create `backend/tests/api/test_project_health.py`

**Interfaces:**
- `POST /api/projects/{id}/health` body `{status, note?}` → history row + project cache; fanout Inbox to watchers ≠ actor
- `GET /api/projects/{id}/health` → `{latest, history?}` with `?history=1`
- `GET/POST/DELETE /api/projects/{id}/watchers` — list / self-watch / self-unwatch
- `GET /api/projects/{id}/timeline` → `{project, milestones, issues}` (issues with due_date only)
- Create project with WS → creator is watcher
- Cross-WS 404; viewer read ok / write 403; invalid status 400

- [x] Write failing tests (mirror `test_milestones` helpers)
- [x] Run `pytest tests/api/test_project_health.py -v` → FAIL (404/missing routes)
- [x] Commit RED tests

### Task 3: Models + Alembic GREEN foundation

- [x] Add `ProjectHealthUpdate`, `ProjectWatcher` models; Project `health_*` columns; export in `models/__init__.py`
- [x] Migration `f6a7b8c9d0e2` revises `e5f6a7b8c9d1`
- [x] Commit models + migration

### Task 4: Services + API GREEN

- [x] `ProjectWatcherService`: list / watch (idempotent) / unwatch; serialize
- [x] `ProjectHealthService`: post update + cache + fanout; get latest/history; timeline DTO
- [x] `NotificationService.notify_project_health` (or inline create loop)
- [x] Nested routers: health, watchers, timeline; wire create_project auto-watch
- [x] Extend `ProjectResponse` + `to_response` with health_* 
- [x] Run pytest file → PASS; commit

### Task 5: FE + vitest

- [x] API helpers + typings for health/watchers/timeline
- [x] `project-timeline.ts`: `isTimelineEmpty`, `HEALTH_LABELS`, zoom day-width helpers + tests
- [x] project-detail: health badge, Update dialog + history, Watch toggle, Timeline tab (week/month, empty-state)
- [x] Inbox: `project_health` label + navigate to project-detail
- [x] lint 0 errors; build; vitest for timeline utils
- [x] Commit FE

### Task 6: Gates + close S2

- [x] Full pytest; eslint --quiet; build
- [x] Acceptance `docs/superpowers/acceptances/2026-11-04-E8-S2-acceptance.md`
- [x] Sprint `state: closed`; roadmap S2 closed / S3 planned; Epic stays active
- [x] Create `sprint/E8-S3` worktree stub from tip (Favorites leftover)
- [x] **No push**

## Acceptance criteria (S2)

1. Health POST writes history + updates project cache columns
2. Watchers receive Inbox `project_health`; actor skipped
3. Watch/unwatch works; create project auto-watches creator
4. Timeline returns project + milestones + due issues; FE week/month + empty-state
5. Header shows latest health; history listable
6. Gates green; Favorites not implemented; no remote push
