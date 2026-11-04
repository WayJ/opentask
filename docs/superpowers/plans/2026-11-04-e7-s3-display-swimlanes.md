# E7-S3 Display Options + Board Swimlanes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline; mid-epic no external acceptance ping). Steps use checkbox syntax. TDD required. **No push.**

**Goal:** Finish thick Epic E7 — personal `issue_display_prefs`, extended `display_json` (`fields` / `swimlane_by` / `hide_empty_lanes`), Display options UI, Board row swimlanes + hide empty; mark Epic **local-complete**.

**Architecture:** New table `issue_display_prefs` (unique workspace+user) + `DisplayPrefsService` + `/api/display-prefs/issue` GET/PUT. Saved View `display_json` may store the same keys as view defaults; applying a View overlays session display without writing prefs unless user clicks「设为个人默认」. FE pure helpers normalize display + build swimlane matrix; `IssueBoard` renders row lanes × status columns; list page hosts Display popover.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, pytest+httpx, Vue3 + Naive UI, vitest.

## Global Constraints

- Worktree `/workspace/opentask-worktrees/E7-S3`, branch `sprint/E7-S3`; baseline `sprint/E7-S2` @ `0965005`; **no push**
- TDD: failing test first for each behavior
- Alembic `down_revision = c3d4e5f6a7b9`; new revision `d4e5f6a7b8c0`
- Personal prefs ≠ View defaults (D9); no force unique workspace layout
- Board columns stay status; swimlanes display-only (no cross-lane field mutation) (D10)
- Out of scope: E8 milestones/Favorites, label retirement, Insights, remote push, mid-epic Way/Yuri ping

## File Map

| Layer | Path |
|---|---|
| Migration | `backend/alembic/versions/2026_11_04_0700-d4e5f6a7b8c0_issue_display_prefs.py` |
| Model | `backend/opentask/models/issue_display_prefs/model.py` (+ `__init__.py`) |
| Service | `backend/opentask/services/display_prefs/service.py` |
| Router | `backend/opentask/api/display_prefs/router.py` |
| App | `backend/opentask/app.py` (include router) |
| Models export | `backend/opentask/models/__init__.py` |
| Tests | `backend/tests/api/test_display_prefs.py` |
| FE API | `frontend/src/service/api/display-prefs.ts` |
| FE types | extend `frontend/src/service/api/saved-views.ts` `SavedViewDisplay` |
| FE utils | `frontend/src/utils/display-prefs.ts`, `boardSwimlanes.ts` (+ tests) |
| FE apply | `frontend/src/utils/apply-saved-view.ts` (+ test) |
| FE board | `frontend/src/views/issue/list/modules/IssueBoard.vue` |
| FE list | `frontend/src/views/issue/list/index.vue` (+ Display popover module optional) |
| Docs | plans / sprints / acceptances / roadmap / design note |

---

### Task 1: Docs stub

**Files:**
- Create: `docs/superpowers/plans/2026-11-04-e7-s3-display-swimlanes.md` (this file)
- Create: `docs/superpowers/sprints/2026-11-04-E7-S3-plan.md`

- [ ] **Step 1:** Write sprint frontmatter `state: active`, scope Display+swimlanes, leftover none→Epic complete
- [ ] **Step 2:** Commit `docs(E7-S3): plan + sprint stub for display prefs and swimlanes`

---

### Task 2: Pytest RED — display prefs API

**Files:**
- Create: `backend/tests/api/test_display_prefs.py`

**Interfaces (target):**
- `GET /api/display-prefs/issue` → `data: { display: null | object }`
- `PUT /api/display-prefs/issue` body `{ display: object }` → upsert; returns `{ display }`
- Header `X-Workspace-Id` required
- Prefs upsert must **not** mutate any `issue_saved_views.display_json`

- [ ] **Step 1: Write failing tests**

```python
# helpers mirror test_saved_views (_register, _auth)

async def test_get_prefs_null_when_absent(test_client):
    user = await _register(test_client, "dp_g")
    resp = await test_client.get("/api/display-prefs/issue", headers=_auth(...))
    assert resp.status_code == 200
    assert resp.json()["data"]["display"] is None

async def test_put_and_get_roundtrip(test_client):
    display = {
        "view_mode": "board",
        "group_by": "none",
        "swimlane_by": "assignee",
        "hide_empty_lanes": True,
        "fields": {"assignee": True, "priority": False, "issue_code": True},
    }
    # PUT then GET → same keys present; hide_empty_lanes True; swimlane_by assignee

async def test_put_upserts_same_user_ws(test_client):
    # two PUTs; only one row semantics (second overwrites)

async def test_prefs_isolated_per_user(test_client):
    # A puts; B in same WS gets null (or own prefs)

async def test_prefs_require_workspace_header(test_client):
    # no X-Workspace-Id → 4xx

async def test_prefs_do_not_overwrite_saved_view_display(test_client):
    # create personal saved view with display {view_mode:list, group_by:status}
    # PUT prefs with different display
    # GET saved-view still has original display
```

- [ ] **Step 2: Run RED**

```bash
cd backend && .venv/bin/pytest tests/api/test_display_prefs.py -v --tb=short
```

Expected: FAIL (404 / import / router missing)

- [ ] **Step 3: Commit** `test(E7-S3): red — display prefs get/put isolation`

---

### Task 3: Model + Alembic + Service + Router GREEN

**Files:**
- Create model `IssueDisplayPrefs` with columns id, workspace_id FK CASCADE, user_id, display_json JSON NOT NULL, updated_at; UniqueConstraint `(workspace_id, user_id)` name `uq_issue_display_prefs_ws_user`
- Migration idempotent inspect create table + unique
- `DisplayPrefsService.get` / `upsert`
- `normalize_display_json(raw) -> dict` merges defaults; keeps view_mode/group_by; adds fields/swimlane_by/hide_empty_lanes; ignores unknown keys for forward compat (store full client payload but normalize known)
- Router + `app.py` include
- Export model in `models/__init__.py`

Default fields dict:

```python
DEFAULT_FIELDS = {
    "assignee": True,
    "priority": True,
    "labels": True,
    "estimate_points": False,
    "due_date": False,
    "project": False,
    "cycle": False,
    "issue_code": True,
    "type": False,
}
DEFAULT_DISPLAY = {
    "view_mode": "list",
    "group_by": "none",
    "swimlane_by": "none",
    "hide_empty_lanes": False,
    "fields": DEFAULT_FIELDS,
}
```

Serialize GET as camelCase-free nested display object (same shape as saved view display_json — FE already uses snake for display keys).

- [ ] **Step 1:** Implement minimal GREEN
- [ ] **Step 2:** pytest file GREEN
- [ ] **Step 3:** Commit `feat(E7-S3): issue_display_prefs model + API`

---

### Task 4: FE display helpers + apply-saved-view (vitest TDD)

**Files:**
- Create: `frontend/src/utils/display-prefs.ts` + `.test.ts`
- Create: `frontend/src/utils/boardSwimlanes.ts` + `.test.ts`
- Modify: `apply-saved-view.ts` + test — return `swimlaneBy`, `hideEmptyLanes`, `fields`
- Modify: `SavedViewDisplay` type with optional `swimlane_by`, `hide_empty_lanes`, `fields`

```ts
export type SwimlaneBy = 'none' | 'assignee' | 'priority' | 'type' | 'label';
export type DisplayFieldKey =
  | 'assignee' | 'priority' | 'labels' | 'estimate_points'
  | 'due_date' | 'project' | 'cycle' | 'issue_code' | 'type';

export interface IssueDisplayFields { /* each key boolean */ }
export interface IssueDisplayState {
  viewMode: 'list' | 'board';
  groupBy: GroupByKey;
  swimlaneBy: SwimlaneBy;
  hideEmptyLanes: boolean;
  fields: IssueDisplayFields;
}

export function defaultIssueDisplay(): IssueDisplayState
export function normalizeIssueDisplay(raw: unknown): IssueDisplayState
export function displayStateToJson(state: IssueDisplayState): Record<string, unknown>
```

`buildBoardSwimlanes(issues, swimlaneBy, hideEmptyLanes)`:
- `none` → single lane `{ key: '__all__', label: '', columns: status→issues[] }`
- else reuse grouping keys from `groupIssuesBy` (map GroupByKey); for each lane bucket, split by status
- if `hideEmptyLanes`, drop lanes where every status list empty

- [ ] RED vitest → GREEN → Commit `feat(E7-S3): display normalize + board swimlanes helpers`

---

### Task 5: FE API + IssueBoard + list Display UI

**Files:**
- Create `frontend/src/service/api/display-prefs.ts` — fetchGet / fetchPut
- Update `IssueBoard.vue` props: `swimlaneBy`, `hideEmptyLanes`, `fields`; render lanes; card meta respects `fields.*`
- Update `index.vue`: session display state; load personal prefs on mount when no view; apply view overlays; Display popover (field switches, swimlane select, hide empty, 设为个人默认, 重置); save view includes new keys; pass props to board

Drag stays **within** a status cell of a lane (no cross-lane field write).

- [ ] Implement + lint slice
- [ ] Commit `feat(E7-S3): display UI + board swimlanes`

---

### Task 6: Gates + Epic local-complete

- [ ] Full `.venv/bin/pytest tests/ -q`
- [ ] `npx vitest run` for display-prefs, boardSwimlanes, apply-saved-view
- [ ] `npm run lint` 0 errors; `npm run build` (copy `.env.prod` if needed like S2)
- [ ] Acceptance `docs/superpowers/acceptances/2026-11-04-E7-S3-acceptance.md`
- [ ] Sprint S3 `state: closed`; roadmap `status: local-complete`; S1–S3 closed; design status note; `merged-commit: null`
- [ ] **No push**

## Self-review

- Spec §4.4 / §5.3 / §6.3 covered by Tasks 2–5
- D8/D9/D10 honored
- No placeholders; no E8 scope
