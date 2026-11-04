# E12-S2 Invites + Members UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline; mid-epic). Steps use checkbox syntax. TDD: red → green → refactor.

**Goal:** Copy-link workspace invites (token hashed), accept/register join, member role PATCH + leave, and FE members/invite landing — no SMTP, no de-PGE.

**Architecture:** Alembic after `b8c9d0e1f2a4` adds `workspace_invites`. `InviteService` creates raw token once (return plaintext + store sha256), lists/revokes for owners, previews anonymously, accepts idempotently under login. Extend `WorkspaceService` with `update_member_role` + `leave`. Mount invites under `/api/workspaces/{id}/invites` and public `/api/invites/{token}`. FE: members page + invite landing; register passes optional `inviteToken`.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, pytest+httpx, Vue3 + Naive UI, TypeScript.

## Global Constraints

- Worktree `/workspace/opentask-worktrees/E12-S2`, branch `sprint/E12-S2`; **no push**
- S2 only (no S3 de-PGE / CodingWorker / SMTP)
- Keep `POST …/members` add_member **409** when already member
- Invite roles: `member|viewer` only (never owner via invite)
- Token: 32+ bytes urlsafe; store **sha256 hex**; plaintext only in create response `token` + FE copy link `/invite/{token}`
- Default `expiresInDays=14` (1–90)
- Accept idempotent: already member → 200 with existing membership
- Last owner cannot leave / cannot be demoted / cannot be removed (existing remove + new leave/PATCH)

## File Map

| Layer | Path |
|---|---|
| Migration | `backend/alembic/versions/2026_11_04_1200-c9d0e1f2a3b5_workspace_invites.py` |
| Model | `backend/opentask/models/workspace/invite.py` (+ export) |
| Schemas | `backend/opentask/schemas/workspace.py` (invite/role/leave DTOs) |
| Service | `backend/opentask/services/workspace/invite_service.py`; extend `service.py` |
| API | `backend/opentask/api/workspace/router.py`; `api/invites/router.py`; `app.py`; auth register |
| Tests | `backend/tests/api/test_invites.py`; `test_workspace_members_s2.py` |
| FE API | `frontend/src/service/api/workspace.ts` |
| FE views | `frontend/src/views/workspace/members/index.vue`; `frontend/src/views/invite/token.vue` |
| FE routes | patch elegant imports/routes/transform OR customRoutes for members + invite |
| Acceptance | `docs/superpowers/acceptances/2026-11-04-E12-S2-acceptance.md` |

---

### Task 1: RED — invites + members API tests

**Files:**
- Create: `backend/tests/api/test_invites.py`
- Create: `backend/tests/api/test_workspace_members_s2.py`

**Interfaces:**
- Produces: HTTP expectations for create/list/revoke/preview/accept/register+token/PATCH role/leave

- [ ] **Step 1: Write failing tests** (helpers `_register` / `_auth` same as E12-S1)

```python
# test_invites.py — key cases
# 1) owner creates invite → 200, data has token, role, expiresAt, inviteId; list shows pending
# 2) member creates invite → 403
# 3) GET /api/invites/{token} anonymous → workspaceName, role, expiresAt, status pending
# 4) accept as second user → 200; listed in members with role
# 5) accept twice → 200 idempotent
# 6) revoke then accept → 400/404
# 7) expired invite accept → 400 (plant expires_at via engine)
# 8) register with inviteToken → user in invited WS + still has defaultWorkspaceId
# 9) bad token preview → 404

# test_workspace_members_s2.py
# 1) owner PATCH member role member→viewer → 200
# 2) owner demote last owner → 400
# 3) member leave → 200; no longer in list
# 4) sole owner leave → 400
# 5) add_member duplicate still 409
```

- [ ] **Step 2: Run RED**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest tests/api/test_invites.py tests/api/test_workspace_members_s2.py -v
```

Expected: FAIL (routes/table missing)

- [ ] **Step 3: Commit tests**

```bash
git commit -m "test(E12-S2): RED invites and members role/leave API"
```

---

### Task 2: Model + Alembic

**Files:**
- Create: `backend/opentask/models/workspace/invite.py`
- Create: migration `c9d0e1f2a3b5` revises `b8c9d0e1f2a4`
- Ensure model imported so `create_all` in tests sees table

```python
class WorkspaceInvite(DBModel):
    __tablename__ = "workspace_invites"
    id: Mapped[str]  # uuid
    workspace_id: Mapped[str]  # FK CASCADE
    email: Mapped[Optional[str]]
    role: Mapped[str]  # member|viewer
    token_hash: Mapped[str]  # unique 64
    expires_at: Mapped[datetime]
    status: Mapped[str]  # pending|accepted|revoked|expired
    invited_by: Mapped[str]
    accepted_by: Mapped[Optional[str]]
    accepted_at: Mapped[Optional[datetime]]
    created_at: Mapped[datetime]
```

- [ ] **Step 1: Implement model + migration**
- [ ] **Step 2: Commit** `feat(E12-S2): workspace_invites model and alembic`

---

### Task 3: InviteService + workspace role/leave GREEN

**Files:**
- Create: `services/workspace/invite_service.py`
- Modify: `services/workspace/service.py` (`update_member_role`, `leave`)
- Modify: schemas + workspace router + new `api/invites/router.py` + `app.py`
- Modify: `RegisterBody.inviteToken` optional; `AuthService.register` accepts invite and joins after personal WS

**Logic:**

```python
def hash_invite_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

# create: secrets.token_urlsafe(32); store hash; status=pending
# accept: lookup hash; if accepted&same user → ok; if revoked/expired → 400;
#   if pending past expires_at → mark expired + 400;
#   else add_member-like insert (skip owner check); mark accepted
# update_member_role: owner only; target exists; if demoting owner ensure another owner remains
# leave: require member; if sole owner → 400; else delete membership
```

- [ ] **Step 1: Implement until invite + members_s2 tests GREEN**
- [ ] **Step 2: Commit** `feat(E12-S2): invites API, accept/register, role PATCH, leave`

---

### Task 4: FE members + invite landing

**Files:**
- Extend `frontend/src/service/api/workspace.ts` with members/invites clients
- Create `views/workspace/members/index.vue` (table + invite form + copy link + revoke; leave button)
- Create `views/invite/token.vue` (preview + accept / redirect login?redirect=)
- Wire routes in elegant `imports.ts` / `routes.ts` / `transform.ts` (manual, match cycles pattern) + menu link near workspace
- Register: pass `inviteToken` from query `invite`

- [ ] **Step 1: Implement FE**
- [ ] **Step 2: eslint touched; optional vitest smoke if helpers extracted**
- [ ] **Step 3: Commit** `feat(E12-S2): members UI and invite landing`

---

### Task 5: Gates + acceptance

- [ ] Full `pytest tests/ -q` → ≥ 708 + new, 0 failed
- [ ] Write acceptance; close sprint stub; roadmap S2 closed note
- [ ] Commit; **no push**; do not start S3

## Spec coverage

| Design S2 AC | Task |
|---|---|
| workspace_invites schema | 2 |
| create/list/revoke owner-only | 1, 3 |
| preview anonymous + accept login idempotent | 1, 3 |
| register inviteToken | 1, 3 |
| PATCH role + leave + last-owner guards | 1, 3 |
| keep add_member 409 | 1, 3 |
| FE members + invite landing + copy link | 4 |
| no SMTP | all |

## Exclusions

SMTP, SSO, S3 de-PGE, remote push, inviting as owner role, changing add_member to 200.
