# E9-S2 Issue Templates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline; mid-epic no external acceptance ping). Steps use checkbox syntax. TDD required. **No push.** Do **not** start S3 (snooze).

**Goal:** Workspace-scoped Issue templates with CRUD API, seed from FE `ISSUE_TEMPLATES`, apply via create flow + ⌘K; optional `templateId` on `POST /api/issues`.

**Architecture:** Alembic after `d0e1f2a3b4c6` creates `issue_templates`. `IssueTemplateService` lists/CRUD/seeds builtins (`seed_key`), merges payload into Issue create. Top-level `/api/issue-templates`. FE Selector prefers API; constants remain seed/fallback. Settings page under `/workspace/issue-templates`. ⌘K「从模板创建」→ create with `?pickTemplate=1`. **Not** PGE `prompt_generator`.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, pytest+httpx, Vue3 + Naive UI, elegant-router.

## Global Constraints

- Worktree `/workspace/opentask-worktrees/E9-S2`, branch `sprint/E9-S2`; baseline `e0aad93`; **no push**
- TDD: failing API tests first
- Alembic `down_revision = d0e1f2a3b4c6`; revision id `e1f2a3b4c5d7`
- Table `issue_templates`; uq `(workspace_id, name)`; optional uq `(workspace_id, seed_key)` where seed_key not null
- payload JSON: `{ title?, description?, type?, priority?, labelIds?, projectId?, fields? }`
- Seed 5 builtins: bug_report / feature_request / improvement / question / task → types bug/feature/improvement/question/feedback
- viewer GET; member+ write; cross-WS 404
- Out of scope: snooze, triage changes, PGE prompts, Project templates, remote push

## File Map

| Layer | Path |
|---|---|
| Migration | `backend/alembic/versions/2026_11_04_1400-e1f2a3b4c5d7_issue_templates.py` |
| Model | `backend/opentask/models/issue_template/` |
| Service | `backend/opentask/services/issue_template/` |
| API | `backend/opentask/api/issue_templates/` + `app.py` |
| Issue create | `api/issue/router.py` + `IssueCreate.template_id` optional |
| Seeds | `services/issue_template/seeds.py` (builtin definitions) |
| Tests | `backend/tests/api/test_issue_templates.py` |
| FE API | `frontend/src/service/api/issue-templates.ts` |
| FE Selector | `IssueTemplateSelector.vue` load API |
| FE settings | `views/workspace/issue-templates/index.vue` + elegant routes |
| FE create / ⌘K | `views/issue/create` query pickTemplate; palette action |
| Docs | plan / sprint stub / acceptance / roadmap |

---

### Task 1: Docs

- [x] Write this plan + S2 sprint stub
- [x] Commit `docs(E9-S2): TDD plan for Issue templates`

### Task 2: Pytest RED

**Files:** Create `backend/tests/api/test_issue_templates.py`

**Interfaces (camelCase):**

- `GET /api/issue-templates` → auto-seed if empty; `{ rows, total }`; each row: `id, workspaceId, name, description, icon, payload, sortOrder, source, seedKey, createdAt, updatedAt`
- `POST /api/issue-templates` body `{ name, description?, icon?, payload?, sortOrder? }` → member+
- `PATCH /api/issue-templates/{id}` → update fields
- `DELETE /api/issue-templates/{id}` → delete
- `POST /api/issue-templates/seed` → idempotent ensure builtins (optional explicit; GET also seeds)
- viewer GET ok, POST 403
- cross-WS id → 404
- duplicate name in WS → 400/409
- `POST /api/issues` with `template_id` (or `templateId` alias): merges payload type/priority/description/title defaults; request body fields override template
- create without template still works
- seed twice → still 5 builtins (idempotent by seed_key)

- [x] Write failing tests; run → FAIL 404
- [x] Commit RED

### Task 3: Model + Alembic GREEN

```python
class IssueTemplate(DBModel):
    __tablename__ = "issue_templates"
    id: str PK uuid
    workspace_id: FK workspaces CASCADE
    name: str(100)
    description: Optional[str]
    icon: Optional[str]
    payload: JSON default {}
    sort_order: int default 0
    source: str  # seed|custom
    seed_key: Optional[str]
    created_by: Optional[str]
    created_at / updated_at
    UniqueConstraint workspace_id, name
    UniqueConstraint workspace_id, seed_key  # allow multiple NULL via partial or just app-enforce
```

- [x] Model + export in `models/__init__.py`
- [x] Migration `e1f2a3b4c5d7`
- [x] Commit

### Task 4: Service + API + templateId on create GREEN

- Builtin seed map in `seeds.py` (not imported from PGE)
- `ensure_seeds(workspace_id, user_id)` upsert by seed_key
- Router `/api/issue-templates`; register in `app.py`
- Extend `IssueCreate` with optional `template_id: Optional[str] = None` (snake; FE may send template_id)
- In `create_issue` router or service: if template_id, load in WS, merge payload into create data (body wins)

Merge rules:
- If body.title empty and payload.title → use payload.title (else require title as today)
- description: if body description empty → payload.description
- type/priority: if not explicitly different from schema defaults… simpler: apply template first then overlay body model_dump(exclude_unset) — IssueCreate always has defaults for type/priority. Better approach: service accepts optional template merge before create:
  1. Start with payload defaults
  2. Overlay request fields that were set
  For API test: send minimal `{ title: "X", template_id }` and expect type from template.

- [x] Implement; pytest file PASS; commit

### Task 5: FE

- `issue-templates.ts` client
- Selector: fetch list on open; map API → IssueTemplate shape (`fields` from `payload.fields` or FE constant by seedKey)
- Create page: on `?pickTemplate=1` open selector; optional `?templateId=`
- Settings page CRUD at `/workspace/issue-templates`
- ⌘K: `nav.create_from_template` → `/issue/create?pickTemplate=1`
- Keep `ISSUE_TEMPLATES` as fallback/seed mirror only
- eslint + vitest if touched; build if feasible

- [x] Commit FE

### Task 6: Gates + acceptance

- [x] Full pytest ≥736 + new template tests
- [x] Acceptance + sprint closed; roadmap S2 closed local
- [x] **No push**; **do not** start S3

## Acceptance criteria

1. `issue_templates` table + Alembic after triage
2. CRUD + auto-seed 5 builtins idempotent
3. `template_id` on create merges payload
4. FE selector API-first; settings page; ⌘K pick template
5. No PGE conflation; no snooze; no push
