# E6-S3 Complete / Rollover / Capacity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline; mid-epic no external acceptance ping). Steps use checkbox syntax. TDD required.

**Goal:** Finish thick Epic E6 — complete Cycle with rollover policies, capacity hint, generate-upcoming, FE polish; mark Epic **local-complete**. No push.

**Architecture:** Extend `CycleService` with `complete` / `capacity_hint` / `generate_upcoming`; register static routes before `/{cycle_id}`; FE settings page adds complete confirm, capacity card, empty upcoming CTA. Capacity samples = completed issues still on each completed Cycle (post-rollover incomplete already left).

**Tech Stack:** FastAPI, SQLAlchemy 2, pytest+httpx, Vue3 + Naive UI.

## Global Constraints

- Worktree `/workspace/opentask-worktrees/E6-S3`, branch `sprint/E6-S3`; **no push**
- Baseline: `sprint/E6-S2` tip `9a59df0`
- TDD: failing pytest first
- Incomplete = status NOT IN (`resolved`, `closed`)
- into_next with no next → auto `generate_upcoming` then roll
- Do **not** auto-activate next on complete
- No Jira sprint / Initiatives / Slack / velocity charts / E7 / mid-epic Way/Yuri ping

## File Map

| Layer | Path |
|---|---|
| Service | `backend/opentask/services/cycle/service.py` |
| Router | `backend/opentask/api/cycles/router.py` |
| Tests | `backend/tests/api/test_cycle_complete.py` |
| FE API | `frontend/src/service/api/cycles.ts` |
| FE page | `frontend/src/views/workspace/cycles/index.vue` |
| Docs | plans/sprints/acceptances/roadmap/design |

---

### Task 1: Docs

- [ ] Sprint plan + this plan committed

### Task 2: Pytest RED

**Files:** Create `backend/tests/api/test_cycle_complete.py`

- [ ] **Step 1: Write failing tests**

1. `test_complete_into_next_rolls_incomplete` — active+upcoming; open+resolved on active; complete → open on next, resolved stays, active→completed with completedAt
2. `test_complete_into_next_auto_generates_upcoming` — only active; into_next; complete creates upcoming and rolls open issues
3. `test_complete_leave_unassigned` — policy leave; open cleared; resolved stays
4. `test_complete_rejects_non_active` — upcoming complete → 400
5. `test_capacity_hint_from_history` — completed cycles with done issues → basis=history, suggested ≈ mean
6. `test_capacity_hint_members_fallback` — no completed → basis=members, suggested=member_count
7. `test_generate_upcoming` — POST creates upcoming after last ends
8. `test_viewer_cannot_complete_or_generate` — 403

Helpers: mirror test_cycles / test_issue_cycle.

- [ ] **Step 2: Run RED** `.venv/bin/pytest tests/api/test_cycle_complete.py -v --tb=short`
- [ ] **Step 3: Commit** `test(E6-S3): red — complete rollover + capacity + generate`

### Task 3: Service + Router GREEN

- [ ] `generate_upcoming(workspace)` — load ws duration; base = max(now, latest ends_at) or now; create upcoming
- [ ] `_find_next_upcoming(cycle)` — upcoming with starts_at ≥ ends_at preferred; else earliest upcoming by starts_at
- [ ] `complete(cycle, workspace)` — assert active; apply policy; set completed; return `{cycle, rolled_count, next_cycle_id}`
- [ ] `capacity_hint(workspace, cycle_id?)` — lookback completed ordered by completed_at desc; count done issues still on each; mean or member_count
- [ ] Router: GET `/capacity-hint`, POST `/generate-upcoming` **before** `/{cycle_id}`; POST `/{cycle_id}/complete`
- [ ] GREEN pytest; commit `feat(E6-S3): complete rollover + capacity-hint + generate-upcoming`

### Task 4: FE

- [ ] `fetchCompleteCycle` / `fetchCapacityHint` / `fetchGenerateUpcoming`
- [ ] Active row: 结束 Cycle + confirm dialog (show incomplete preview if available)
- [ ] Capacity card when enabled
- [ ] Empty upcoming CTA → generate
- [ ] Commit `feat(E6-S3): cycles FE complete + capacity + empty CTA`

### Task 5: Gates + Epic close

- [ ] Full pytest; npm lint 0 errors; npm build; vitest only if FE unit added
- [ ] Acceptance; close S3; roadmap status **local-complete**; S1–S3 closed; design note; **no push**
