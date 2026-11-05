# E13 Linear Visual Restyle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adopt getdesign `linear.app` tokens into OpenTask product UI (DESIGN.md + Naive/soybean theme + Linear-like sidebar IA + priority page polish), local-only.

**Architecture:** Keep Vue3/Naive/soybean; rewrite visual source of truth; map Linear dark canvas + indigo primary into CSS vars and `themeColor`; flatten route menu meta to Linear IA; polish high-traffic pages without API changes.

**Tech Stack:** Vue 3, Naive UI, soybean-admin shell, UnoCSS, existing i18n locales.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-11-04-e13-linear-visual-restyle-design.md`
- Source dump: `docs/superpowers/specs/2026-11-04-getdesign-linear.app-source.md`
- Primary `#5e6ad2`; canvas `#010102`; logo D + title OpenTask unchanged
- Default `themeScheme: 'dark'`; light uses inverse tokens
- No Linear proprietary fonts — system stack only
- **Do not push remote**; commit on local sprint branch
- Do not change backend APIs / business logic
- Worktree: `/workspace/opentask-worktrees/E11-S4` (or new `E13-S*` from tip if preferred — document choice in commit)

---

### Task 1: DESIGN.md + CSS tokens + themeColor

**Files:**
- Modify: `DESIGN.md`
- Modify: `frontend/src/styles/design-system.css`
- Modify: `frontend/src/styles/design-tokens.css` (if still referenced)
- Modify: `frontend/src/theme/settings.ts` (`themeColor`, `themeScheme` default, radius)
- Reference: `docs/superpowers/specs/2026-11-04-e13-linear-visual-restyle-design.md`

- [ ] **Step 1:** Rewrite root `DESIGN.md` frontmatter + prose to Linear product tokens (table from spec). Drop soybean `#646cff` as truth. Note dark default + light inverse. Keep version bump (e.g. 2.0).

- [ ] **Step 2:** Update `design-system.css` `--color-*` / surfaces / borders / text to match. Add dark-scheme overrides on `html.dark` / Naive dark body if needed so canvas ≈ `#010102` and surfaces ≈ `#0f1011`.

- [ ] **Step 3:** Set `themeColor: '#5e6ad2'`, `themeScheme: 'dark'`, tune `otherColor` success toward `#27a644` where it doesn’t break Naive.

- [ ] **Step 4:** Smoke: `pnpm` / vite already on :9527 — hard reload login; confirm primary indigo + dark shell without console errors.

- [ ] **Step 5:** Commit `style(theme): adopt Linear.app tokens as DESIGN.md truth (E13-S1)`

---

### Task 2: Sidebar / route IA → Linear shape

**Files:**
- Modify: `frontend/src/router/elegant/routes.ts` and/or `frontend/src/router/routes/builtin.ts` / `index.ts` as needed
- Modify: `frontend/src/locales/langs/zh-cn.ts`, `en-us.ts` (menu titles)
- Modify: route shared helpers under `frontend/src/store/modules/route/` if menu filtering lives there
- Test: `frontend/src/router/__tests__/de-pge-nav.test.ts` and any menu tests — update expectations

**Target order:** Inbox → My issues → Workspace (Views/Projects/Cycles/Initiatives/Docs) → Favorites → project/team list → Settings/Members/Profile. Hide Soybean “工作管理 / 研发流水线 / 系统管理” clutter groupings.

- [ ] **Step 1:** Inventory current menu tree (log or dump from routes meta). Map each real feature route to Linear bucket; mark orphans `hideInMenu: true`.

- [ ] **Step 2:** Apply meta/order/i18n changes so sidebar matches target. Keep deep links working.

- [ ] **Step 3:** Update/fix unit tests for nav filtering.

- [ ] **Step 4:** Visual check sidebar vs `/workspace/opentask-smoke/compare/linear-new-ui-2.png`.

- [ ] **Step 5:** Commit `feat(nav): flatten sidebar IA to Linear-like structure (E13-S2)`

---

### Task 3: Shell chrome (header / tabs / content)

**Files:**
- Layout modules under `frontend/src/layouts/modules/` (global-header, global-menu, global-tab, etc.)
- Minimal CSS overrides; prefer tokens over one-off hex

- [ ] **Step 1:** Quiet header/tabs: hairline borders, reduce heavy shadows, align heights to ~56 / quieter tabs.

- [ ] **Step 2:** Content padding 12–16px; cards use surface + hairline.

- [ ] **Step 3:** Spot-check logged-in shell on `/issue/list`.

- [ ] **Step 4:** Commit `style(shell): Linear-density header/sidebar/content chrome (E13-S2)`

---

### Task 4: Priority pages visual pass

**Files:** issue list/board/detail, inbox, home, settings/members/profile Vue SFCs under `frontend/src/views/` (discover exact paths in tree)

- [ ] **Step 1:** Issue list + board — spacing, table/board chrome, empty states use tokens only.

- [ ] **Step 2:** Issue detail + Inbox same.

- [ ] **Step 3:** Home + settings/members/profile same; login already branded — ensure dark/light both OK.

- [ ] **Step 4:** No API/behavior changes; run relevant vitest.

- [ ] **Step 5:** Commit `style(pages): Linear-adjacent polish on core views (E13-S3)`

---

### Task 5: Epic acceptance

- [ ] **Step 1:** Checklist from spec Acceptance section — all boxes true.

- [ ] **Step 2:** Capture screenshots to `/workspace/opentask-smoke/e13/` (login, sidebar, issue list, inbox).

- [ ] **Step 3:** Report tip SHA + branch; **do not push**. Stand by for Way re-verify.

---

## Out of scope reminders

P1 backlog items unrelated to visuals; remote push/PR; replacing Naive; new features.
