# E5-S3 Focus + Hotkeys Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans / TDD. Steps use checkbox syntax.

**Goal:** Deliver list/board/detail issue focus, C/A/S/P/I hotkeys with pickers + assign-to-me, ⌘B Board↔List toggle on `/issue/list`, board detail URL `?id=`, then mark Epic E5 **local-complete**.

**Architecture:** Module-singleton composables (`useIssueFocus`, `useIssueListViewMode`, `useIssueFieldPickers`) + pure helpers in `utils/issue-hotkeys.ts` / board URL builder. Extend `useAppHotkeys`. Host mount for pickers next to CommandPaletteHost. List/board/detail write focus; ignoreWhenEditable for single letters; palette-open blocks single letters; ⌘K/⌘B allowed in inputs.

**Tech Stack:** Vue 3 + TS + Naive UI + `@vueuse/core` + Vitest. No new deps.

## Global Constraints

- Worktree `/workspace/opentask-worktrees/E5-S3`, branch `sprint/E5-S3` from `f5c70d1`; **no remote push**
- No Cycles / Labels L / G-then-X / modal create
- Gates: focused vitest; lint 0 errors; build; pytest ~621+
- Epic → **local-complete**; merged-commit null

---

### Task 1: Pure helpers + Vitest (TDD)

**Files:**
- Create: `frontend/src/utils/issue-hotkeys.ts`
- Create: `frontend/src/utils/issue-hotkeys.test.ts`
- Create: `frontend/src/utils/issue-board-nav.ts`
- Create: `frontend/src/utils/issue-board-nav.test.ts`

**API:**
- `isModB`, `buildIssueDetailLocation(id)`, `toggleListBoardMode(mode)`, `resolveIssueHotkeyAction(input)`

- [x] **Step 1: Write failing tests**
- [x] **Step 2: Run — expect FAIL**
- [x] **Step 3: Implement helpers**
- [x] **Step 4: Tests PASS**

### Task 2: useIssueFocus + useIssueListViewMode (TDD)

**Files:**
- Create: `frontend/src/composables/use-issue-focus.ts`
- Create: `frontend/src/composables/use-issue-focus.test.ts`
- Create: `frontend/src/composables/use-issue-list-view-mode.ts`
- Create: `frontend/src/composables/use-issue-list-view-mode.test.ts`

- [x] Focus: setFocus / clearFocus / ensureDetailFocus / focusedIssueId
- [x] View mode singleton: mode ref + toggle(); list page binds same state as UI buttons

### Task 3: Extend useAppHotkeys + field pickers

**Files:**
- Modify: `frontend/src/composables/use-app-hotkeys.ts`
- Create: `frontend/src/composables/use-issue-field-pickers.ts`
- Create: `frontend/src/layouts/modules/global-search/issue-hotkey-picker-host.vue`
- Modify: `frontend/src/layouts/modules/global-search/command-palette-host.vue` (or base-layout) to mount picker host
- Modify: `frontend/src/utils/hotkeys.ts` if needed (isModB re-export or keep in issue-hotkeys)

Rules:
- C → `/issue/create` when palette closed + not editable
- A/S/P → open picker for focused issue
- I → updateAssignee(focused, authStore.userInfo.userId)
- ⌘B/Ctrl+B → toggle list/board when route is `/issue/list`
- No focus → A/S/P/I no-op (+ optional message)

### Task 4: Wire list / board / detail + board URL

**Files:**
- Modify: `frontend/src/views/issue/list/index.vue` — bind viewMode to singleton; row-props setFocus + focused class; pass focusedId to board
- Modify: `frontend/src/views/issue/list/modules/IssueBoard.vue` — click→setFocus; dblclick→openDetail with `buildIssueDetailLocation`; focused class; fix URL
- Modify: `frontend/src/views/issue/list/modules/IssueListGrouped.vue` — optional row-props if parent passes
- Modify: `frontend/src/views/issue/detail/index.vue` — ensureDetailFocus(issueId)

### Task 5: Docs + gates + Epic local-complete

- Plan / sprint / acceptance
- Amend design + roadmap: S3 closed; Epic status local-complete; ⌘B documented; R10 for ⌘B
- Gates evidence; no push

## Out of scope

Cycles, Labels L, G-then-X, modal create, remote push, mid-ping Yuri
