# E10-S1 Initiatives Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline; mid-epic). Steps use checkbox syntax. TDD required. **No push.** Do **not** start S2/S3.

**Goal:** Workspace-scoped Initiative CRUD with many-to-many Project links; FE list/detail on Issue/Project axis only (no PGE/`requirements`).

**Architecture:** Alembic after `f2a3b4c5d6e8` creates `initiatives` + `initiative_projects`. `InitiativeService` lists/CRUD/set_projects with same-WS checks. Top-level `/api/initiatives`. FE `/initiatives` + detail; project picker via existing `/api/projects`. **No** health rollup (S2), Docs (S3), or PGE routes.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, pytest+httpx, Vue3 + Naive UI, elegant-router.

## Global Constraints

- Worktree `/workspace/opentask-worktrees/E10-S1`, branch `sprint/E10-S1`; baseline docs `568206e` / E9 tip `f06dc9f`; **no push**
- Yuri: Initiatives on Issue/Project only; **no PGE dual-axis**; no requirements navigation
- TDD: failing API tests first
- Alembic `down_revision = f2a3b4c5d6e8`; revision id `b2c3d4e5f6a7` (avoid colliding `a1b2c3d4e5f6`)
- viewer GET; member+ write; cross-WS 404
- Out of scope: health summary, Docs, Favorites initiative, Estimates, E11, push

## File Map

| Layer | Path |
|---|---|
| Migration | `backend/alembic/versions/2026_11_04_1600-b2c3d4e5f6a7_initiatives.py` |
| Model | `backend/opentask/models/initiative/` |
| Service | `backend/opentask/services/initiative/` |
| API | `backend/opentask/api/initiatives/` + `app.py` |
| Tests | `backend/tests/api/test_initiatives.py` |
| FE API | `frontend/src/service/api/initiatives.ts` |
| FE views | `frontend/src/views/initiatives/index.vue` + `detail/index.vue` |
| Routes | elegant routes/imports/transform + typings + i18n |
| Docs | plan / acceptance / sprint stub / roadmap S1 |

---

### Task 1: Docs plan

- [ ] Write this plan; commit `docs(E10-S1): TDD plan for Initiatives`

### Task 2: Pytest RED

**Files:** `backend/tests/api/test_initiatives.py`

**Interfaces (camelCase responses):**

- `GET /api/initiatives` → `{ rows, total }`; each: `id, workspaceId, name, description, status, targetDate, ownerUserId, sortOrder, projectIds, createdAt, updatedAt`
- `POST /api/initiatives` body `{ name, description?, status?, targetDate?, ownerUserId?, sortOrder?, projectIds? }` → member+
- `GET /api/initiatives/{id}` → detail + `projectIds`
- `PATCH /api/initiatives/{id}` → update fields
- `DELETE /api/initiatives/{id}` → delete
- `PUT /api/initiatives/{id}/projects` body `{ projectIds: string[] }` → replace links; reject foreign-WS project (400)
- `POST /api/initiatives/{id}/projects/{projectId}` / `DELETE …` → attach/detach
- viewer GET ok, POST 403; cross-WS id → 404; duplicate name → 400/409
- create with `projectIds` same WS ok

- [ ] Failing tests; commit RED

### Task 3: Model + Alembic GREEN

```python
class Initiative(DBModel):
    __tablename__ = "initiatives"
    # columns per design §4.1
    UniqueConstraint workspace_id, name

class InitiativeProject(DBModel):  # or Table
    __tablename__ = "initiative_projects"
    initiative_id FK CASCADE
    project_id FK CASCADE
    PK (initiative_id, project_id)
```

- [ ] Model + `models/__init__.py` export; migration `b2c3d4e5f6a7`; commit

### Task 4: Service + API GREEN

- `require_writer` (owner|member)
- serialize camelCase + `projectIds`
- Router register in `app.py` next to issue_templates
- [ ] pytest file PASS; commit

### Task 5: FE

- `initiatives.ts` client
- List page create/delete; detail edit + project multi-select (`fetchProjectList`)
- Routes `/initiatives`, `/initiatives/detail`; i18n; **no** link to knowledge PGE/requirements
- eslint + build if feasible
- [ ] Commit FE

### Task 6: Gates + acceptance

- [ ] Full pytest; note count + pre-existing protocol_rules fails
- [ ] Acceptance + close S1 stub; roadmap S1 closed
- [ ] **No push**; **do not** start S2/S3

## Acceptance criteria

1. `initiatives` + `initiative_projects` + Alembic after snooze
2. CRUD + M2M ACL/cross-WS/name unique
3. FE list/detail project picker; no PGE routes
4. No health/Docs/push
