# E9-S3 Inbox Snooze Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline; mid-epic no external acceptance ping). Steps use checkbox syntax. TDD required. **No push.** Do **not** start E10.

**Goal:** Add `notifications.snoozed_until`, snooze/unsnooze API, Inbox FE presets; hide snoozed until due; Epic E9 local-complete.

**Architecture:** Alembic after `e1f2a3b4c5d7` adds nullable `snoozed_until`. `NotificationService.list_for_user` excludes `snoozed_until > now()` unless `include_snoozed=true`. `POST /api/inbox/{id}/snooze` body `{ until }` (≤ now+90d); `POST …/unsnooze` clears. FE Inbox row dropdown 1h/3h/明天/下周一 + unsnooze when viewing snoozed (optional include). Triage stays separate.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, pytest+httpx, Vue3 + Naive UI.

## Global Constraints

- Worktree `/workspace/opentask-worktrees/E9-S3`, branch `sprint/E9-S3`; baseline `223b264`; **no push**
- TDD: failing snooze tests first
- Alembic `down_revision = e1f2a3b4c5d7`; revision id `f2a3b4c5d6e8`
- Personal Inbox only; not Triage; no email/SMTP; no E10
- Pre-existing `opentask/api/test/test_task_protocol_rules.py` mapper fails: note separately; do not “fix” unless trivial

## File Map

| Layer | Path |
|---|---|
| Migration | `backend/alembic/versions/2026_11_04_1500-f2a3b4c5d6e8_notification_snoozed_until.py` |
| Model | `backend/opentask/models/notification/model.py` |
| Service | `backend/opentask/services/notification/service.py` |
| API | `backend/opentask/api/inbox/router.py` |
| Tests | `backend/tests/api/test_inbox_snooze.py` (+ keep `test_inbox.py`) |
| FE API | `frontend/src/service/api/inbox.ts` |
| FE UI | `frontend/src/views/inbox/index.vue` |
| Docs | plan / sprint stub / S3 acceptance / roadmap epic complete |

---

### Task 1: Docs

- [x] Write this plan + S3 sprint stub
- [x] Commit `docs(E9-S3): TDD plan for Inbox snooze`

### Task 2: Pytest RED

**Files:** Create `backend/tests/api/test_inbox_snooze.py`

**Interfaces:**

- `POST /api/inbox/{id}/snooze` body `{ "until": "<ISO8601>" }` → 200; row has `snoozedUntil`; only recipient
- After snooze: `GET /api/inbox` default **hides** that row; `unreadCount` excludes it
- `GET /api/inbox?include_snoozed=true` shows it with `snoozedUntil`
- `POST /api/inbox/{id}/unsnooze` → clears; appears in default list again
- Snooze with `until` in the past (or ≤ now): treat as immediate visible OR reject 400 — prefer **400** if until ≤ now
- `until` > now+90d → **400**
- Other user’s notification id → **404**
- Snooze then wait: set until to near-past via service/DB in test → default list shows again (lazy)
- Mark read while snoozed still works when fetched with include_snoozed; unsnooze preserves `readAt`

Helper: create notif via assign like `test_inbox.py`.

- [x] Write failing tests; run → FAIL (404 / no field)
- [x] Commit RED

### Task 3: Model + Alembic GREEN

```python
snoozed_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
# optional index idx_notifications_recipient_snoozed
```

Migration `f2a3b4c5d6e8` adds column if missing.

- [x] Model + migration
- [x] Commit

### Task 4: Service + API GREEN

- `list_for_user(..., include_snoozed: bool = False)`: if not include, add `(snoozed_until.is_(None) | snoozed_until <= utcnow())` to list + unread_count filters
- `snooze(id, user_id, until: datetime)` / `unsnooze(...)`
- Router: query `include_snoozed`; POST snooze body Pydantic `until: datetime`; serialize `snoozedUntil`
- [x] Implement; pytest file PASS; commit

### Task 5: FE

- `InboxNotification.snoozedUntil?: string | null`
- `fetchSnoozeInbox(id, untilISO)`, `fetchUnsnoozeInbox(id)`
- Inbox page: row stop-propagation dropdown 「延后」→ 1小时 / 3小时 / 明天 9:00 / 下周一 9:00; call API; reload
- Optional toggle「显示已延后」→ `includeSnoozed`
- Empty copy: 「暂无通知（个人收件箱，与分诊队列无关）」
- Subtitle under title clarifying notifications vs Triage
- eslint + build if feasible

- [x] Commit FE

### Task 6: Gates + Epic local-complete

- [x] Full pytest; note new count + any pre-existing fails
- [x] Acceptance `docs/superpowers/acceptances/2026-11-04-E9-S3-acceptance.md`
- [x] Sprint stub closed; roadmap S3 closed + DoD checkboxes + **Epic tip SHA** for Yuri
- [x] Optional `docs/superpowers/acceptances/2026-11-04-E9-epic-local-complete.md` or fold into S3 acceptance (E12 folded into S3)
- [x] **No push**; **do not** start E10

## Acceptance criteria

1. `snoozed_until` column + migration after templates
2. snooze/unsnooze + default list filter + include_snoozed + 90d cap
3. FE presets + unsnooze path; Triage separate
4. Epic S1–S3 closed local; tip SHA recorded; no E10
