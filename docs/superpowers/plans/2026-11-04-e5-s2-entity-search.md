# E5-S2 Entity Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add debounced entity search groups (Issues / Projects / Saved Views) to the ⌘K command palette, with Saved View apply via `/issue/list?view=`, without S3 hotkeys/focus.

**Architecture:** Pure helpers for issue-code detection, entity→PaletteItem mapping, extended `buildPaletteGroups`, and `deriveListStateFromSavedView`. Extend `useCommandPalette` singleton with entity sources + loading. Host runs 300ms-debounced fetches. List page watches `route.query.view` and applies via shared helper. FE `getIssue` gains `{ byCode }`.

**Tech Stack:** Vue 3 + TS + Naive UI + `@vueuse/core` (`useDebounceFn`) + Vitest. No new deps.

## Global Constraints

- Worktree `/workspace/opentask-worktrees/E5-S2`, branch `sprint/E5-S2`; **no remote push**
- No Cycles / Labels L / C/A/S/P/I / ⌘B / board URL / cmdk
- Empty query → Actions only (skip recent)
- Gates: focused vitest; `npm run lint` 0 errors; `npm run build`; backend pytest regression
- Epic roadmap stays **active** (not local-complete); only S2 → closed

---

### Task 1: Pure helpers + Vitest (TDD)

**Files:**
- Create: `frontend/src/utils/command-palette-entities.ts`
- Create: `frontend/src/utils/command-palette-entities.test.ts`
- Create: `frontend/src/utils/apply-saved-view.ts`
- Create: `frontend/src/utils/apply-saved-view.test.ts`
- Modify: `frontend/src/utils/command-palette.ts` (`buildPaletteGroups` entity groups)
- Modify: `frontend/src/utils/command-palette.test.ts`

**Interfaces:**
- Produces: `looksLikeIssueCode`, `issuesToPaletteItems`, `projectsToPaletteItems`, `savedViewsToPaletteItems`, `filterByNameQuery`, `deriveListStateFromSavedView`, extended `buildPaletteGroups`

- [ ] **Step 1: Write failing entity helper tests**

```ts
// frontend/src/utils/command-palette-entities.test.ts
import { describe, expect, it, vi } from 'vitest';
import {
  filterByNameQuery,
  issuesToPaletteItems,
  looksLikeIssueCode,
  projectsToPaletteItems,
  savedViewsToPaletteItems
} from './command-palette-entities';

describe('looksLikeIssueCode', () => {
  it('matches CODE-123 and ISSUE2026-32', () => {
    expect(looksLikeIssueCode('ABC-1')).toBe(true);
    expect(looksLikeIssueCode('ISSUE2026-32')).toBe(true);
    expect(looksLikeIssueCode('  ot-99  ')).toBe(true);
  });
  it('rejects free text', () => {
    expect(looksLikeIssueCode('fix')).toBe(false);
    expect(looksLikeIssueCode('ABC')).toBe(false);
    expect(looksLikeIssueCode('')).toBe(false);
  });
});

describe('entity mappers', () => {
  it('maps issues with subtitle code and navigates detail', () => {
    const nav = vi.fn();
    const items = issuesToPaletteItems(
      [{ id: 'i1', title: 'Fix login', issue_code: 'OT-1' } as Api.Issue.Issue],
      nav
    );
    expect(items[0]).toMatchObject({ id: 'issue.i1', kind: 'issue', title: 'Fix login', subtitle: 'OT-1' });
    items[0].run();
    expect(nav).toHaveBeenCalledWith({ path: '/issue/detail', query: { id: 'i1' } });
  });

  it('maps projects and saved views', () => {
    const nav = vi.fn();
    const apply = vi.fn();
    const projects = projectsToPaletteItems([{ id: 'p1', name: 'Alpha' } as Api.Project.Project], nav);
    projects[0].run();
    expect(nav).toHaveBeenCalledWith({ path: '/workflow/project-detail', query: { id: 'p1' } });
    const views = savedViewsToPaletteItems(
      [{ id: 'v1', name: 'My Open', isFavorite: true } as import('@/service/api/saved-views').SavedView],
      apply
    );
    expect(views[0].kind).toBe('saved_view');
    views[0].run();
    expect(apply).toHaveBeenCalledWith('v1');
  });

  it('filterByNameQuery is case-insensitive includes', () => {
    expect(filterByNameQuery([{ name: 'Alpha' }, { name: 'Beta' }], 'alp').map(x => x.name)).toEqual(['Alpha']);
    expect(filterByNameQuery([{ name: 'Alpha' }], '')).toEqual([]);
  });
});
```

- [ ] **Step 2: Run — expect FAIL missing module**

Run: `cd frontend && npm test -- --run src/utils/command-palette-entities.test.ts`

- [ ] **Step 3: Implement helpers**

```ts
// frontend/src/utils/command-palette-entities.ts
import type { PaletteItem } from './command-palette';
import type { SavedView } from '@/service/api/saved-views';

const ISSUE_CODE_RE = /^[A-Za-z][A-Za-z0-9]*-\d+$/;

export function looksLikeIssueCode(query: string): boolean {
  return ISSUE_CODE_RE.test(query.trim());
}

export type NavigateTo = (to: string | { path: string; query?: Record<string, string> }) => void;

export function issuesToPaletteItems(issues: Api.Issue.Issue[], navigate: NavigateTo): PaletteItem[] {
  return issues.map(issue => ({
    id: `issue.${issue.id}`,
    kind: 'issue' as const,
    title: issue.title,
    subtitle: issue.issue_code,
    keywords: [issue.issue_code, issue.title],
    run: () => navigate({ path: '/issue/detail', query: { id: issue.id } })
  }));
}

export function projectsToPaletteItems(projects: Api.Project.Project[], navigate: NavigateTo): PaletteItem[] {
  return projects.map(p => ({
    id: `project.${p.id}`,
    kind: 'project' as const,
    title: p.name,
    keywords: [p.name],
    run: () => navigate({ path: '/workflow/project-detail', query: { id: p.id } })
  }));
}

export function savedViewsToPaletteItems(views: SavedView[], applyView: (id: string) => void): PaletteItem[] {
  return views.map(v => ({
    id: `view.${v.id}`,
    kind: 'saved_view' as const,
    title: v.name,
    subtitle: v.isFavorite ? '★' : undefined,
    keywords: [v.name],
    run: () => applyView(v.id)
  }));
}

export function filterByNameQuery<T extends { name: string }>(items: T[], query: string): T[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  return items.filter(i => i.name.toLowerCase().includes(q));
}
```

- [ ] **Step 4: Tests PASS for entities**

- [ ] **Step 5: Write failing apply-saved-view + extended groups tests**

```ts
// frontend/src/utils/apply-saved-view.test.ts
import { describe, expect, it } from 'vitest';
import { deriveListStateFromSavedView } from './apply-saved-view';
import type { SavedView } from '@/service/api/saved-views';

describe('deriveListStateFromSavedView', () => {
  it('maps filter/tab/display', () => {
    const view = {
      id: 'v1',
      name: 'Open bugs',
      filter: { type: 'bug', status: 'open', search: 'login', tab: 'open', priority: 'high', project_id: 'p1' },
      display: { view_mode: 'board', group_by: 'priority' }
    } as SavedView;
    const state = deriveListStateFromSavedView(view);
    expect(state.filters).toEqual({
      type: 'bug',
      status: 'open',
      search: 'login',
      priority: 'high',
      project_id: 'p1'
    });
    expect(state.tab).toBe('open');
    expect(state.viewMode).toBe('board');
    expect(state.groupBy).toBe('priority');
    expect(state.activeSavedViewId).toBe('v1');
  });

  it('infers tab from status when tab missing; defaults groupBy none', () => {
    const view = {
      id: 'v2',
      name: 'Closed',
      filter: { status: 'closed' },
      display: null
    } as SavedView;
    const state = deriveListStateFromSavedView(view);
    expect(state.tab).toBe('closed');
    expect(state.groupBy).toBe('none');
    expect(state.viewMode).toBeUndefined();
  });
});
```

Extend `command-palette.test.ts`:

```ts
it('appends entity groups when query non-empty', () => {
  const groups = buildPaletteGroups({
    actions: [{ id: 'nav.issues', kind: 'action', title: 'Issues', run: () => undefined }],
    menus: [],
    query: 'fix',
    groupLabels: { actions: 'Actions', menus: 'Menus', issues: 'Issues', projects: 'Projects', views: 'Views' },
    issues: [{ id: 'issue.1', kind: 'issue', title: 'Fix', run: () => undefined }],
    projects: [{ id: 'project.1', kind: 'project', title: 'Alpha', run: () => undefined }],
    savedViews: [{ id: 'view.1', kind: 'saved_view', title: 'Mine', run: () => undefined }]
  });
  expect(groups.map(g => g.id)).toEqual(['issues', 'projects', 'views']);
});

it('hides entity groups when query empty even if sources present', () => {
  const groups = buildPaletteGroups({
    actions: [{ id: 'nav.issues', kind: 'action', title: 'Issues', run: () => undefined }],
    menus: [],
    query: '',
    groupLabels: { actions: 'Actions', menus: 'Menus', issues: 'Issues', projects: 'Projects', views: 'Views' },
    issues: [{ id: 'issue.1', kind: 'issue', title: 'Fix', run: () => undefined }]
  });
  expect(groups.map(g => g.id)).toEqual(['actions']);
});
```

- [ ] **Step 6: Implement apply helper + extend buildPaletteGroups — tests PASS**

```ts
// frontend/src/utils/apply-saved-view.ts
import type { SavedView } from '@/service/api/saved-views';
import { type GroupByKey, isGroupByKey } from './groupIssuesBy';

export interface DerivedListStateFromSavedView {
  filters: {
    status?: Api.Issue.IssueStatus;
    type?: Api.Issue.IssueType;
    priority?: Api.Issue.IssuePriority;
    project_id?: string;
    search: string;
  };
  tab?: 'my_issues' | 'open' | 'closed' | 'all';
  viewMode?: 'list' | 'board';
  groupBy: GroupByKey;
  activeSavedViewId: string;
}

export function deriveListStateFromSavedView(view: SavedView): DerivedListStateFromSavedView {
  const f = view.filter || {};
  const filters = {
    type: (f.type as Api.Issue.IssueType | undefined) || undefined,
    priority: (f.priority as Api.Issue.IssuePriority | undefined) || undefined,
    project_id: (f.project_id as string | undefined) || undefined,
    status: (f.status as Api.Issue.IssueStatus | undefined) || undefined,
    search: (f.search as string | undefined) || ''
  };

  let tab = (f.tab as DerivedListStateFromSavedView['tab'] | undefined) || undefined;
  if (!tab && filters.status) {
    const openStatuses: Api.Issue.IssueStatus[] = ['open', 'in_progress', 'feedback'];
    const closedStatuses: Api.Issue.IssueStatus[] = ['closed', 'rejected', 'resolved'];
    if (openStatuses.includes(filters.status)) tab = 'open';
    else if (closedStatuses.includes(filters.status)) tab = 'closed';
  }

  let viewMode: 'list' | 'board' | undefined;
  if (view.display?.view_mode === 'board' || view.display?.view_mode === 'list') {
    viewMode = view.display.view_mode;
  }

  const groupBy: GroupByKey = isGroupByKey(view.display?.group_by) ? view.display.group_by : 'none';

  return { filters, tab, viewMode, groupBy, activeSavedViewId: view.id };
}
```

Update `buildPaletteGroups` to accept optional `issues` / `projects` / `savedViews` and labels; only push those groups when `query.trim()` is non-empty and items length > 0. Prefer entity groups after actions/menus when query matches neither action (still show matching actions first, then menus, then entities).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/utils/command-palette*.ts frontend/src/utils/apply-saved-view*.ts
git commit -m "test(E5-S2): entity palette helpers + apply-saved-view"
```

---

### Task 2: getIssue byCode + palette entity sources

**Files:**
- Modify: `frontend/src/service/api/issue.ts`
- Create: `frontend/src/service/api/issue-by-code.test.ts` (pure contract: assert params builder) OR test via small `buildGetIssueParams` — prefer exporting nothing extra: unit-test a tiny `buildIssueDetailParams(opts?: { byCode?: boolean })` colocated OR document in entities test that navigators use byCode path via a `resolveIssueSearchPlan(query)` helper.

Add:

```ts
export function resolveIssueSearchPlan(query: string): { search: string; fetchByCode: boolean; code?: string } {
  const q = query.trim();
  if (looksLikeIssueCode(q)) return { search: q, fetchByCode: true, code: q };
  return { search: q, fetchByCode: false };
}
```

Test that; implement `getIssue(id, opts?: { byCode?: boolean })` with `params: opts?.byCode ? { by_code: true } : undefined`.

**Modify** `use-command-palette.ts`:
- Add `issueSource`, `projectSource`, `viewSource`, `entityLoading` refs
- `setEntitySources({ issues, projects, savedViews })`
- `setGroupLabels` extends with issues/projects/views
- `groups` computed passes entity sources into `buildPaletteGroups`
- `resetCommandPaletteForTests` clears entities
- `setQuery` already resets activeIndex — also clear entity sources when query becomes empty (or host clears)

- [ ] **Step 1: Failing test for resolveIssueSearchPlan + composable entity groups**
- [ ] **Step 2: Implement getIssue byCode + composable — PASS**
- [ ] **Step 3: Commit** `feat(E5-S2): byCode getIssue + palette entity sources`

---

### Task 3: Host debounce search + list `?view=` + UI/i18n

**Files:**
- Modify: `frontend/src/layouts/modules/global-search/command-palette-host.vue`
- Modify: `frontend/src/layouts/modules/global-search/components/search-modal.vue`
- Modify: `frontend/src/views/issue/list/index.vue`
- Modify: `frontend/src/locales/langs/zh-cn.ts`, `en-us.ts`

Host:
- `watch(query)` → `useDebounceFn(300)` → if empty: `setEntitySources` empty + loading false; else parallel:
  - `issueApi.getIssues({ search: q, page: 1, page_size: 10 })`
  - if `looksLikeIssueCode(q)`: also `getIssue(q, { byCode: true })` — prepend/merge unique by id
  - `fetchProjectList()` then `filterByNameQuery`
  - `fetchSavedViews()` then filter rows by name
- Map to palette items; `navigate` via `router.push`; applyView → `router.push({ path:'/issue/list', query:{ view:id }})`

List:
- Refactor `applySavedView` to use `deriveListStateFromSavedView`
- `watch(() => route.query.view, ...)` / onMounted after loadSavedViews: if view id present, find & apply (clear query optional after apply to avoid re-apply loops — use `router.replace` strip or guard with applied id)

Modal:
- Show `item.subtitle` under title when present
- Show small loading text when `entityLoading && query`

i18n: `groupIssues`, `groupProjects`, `groupViews`, `searching`

- [ ] **Step 1: Wire host + list + modal + i18n**
- [ ] **Step 2: Focused vitest still green**
- [ ] **Step 3: Commit** `feat(E5-S2): debounced entity search + view query apply`

---

### Task 4: Gates + acceptance + roadmap

- [ ] `npm test -- --run` focused suite
- [ ] `npm run lint` → 0 errors
- [ ] `npm run build`
- [ ] `cd backend && uv run pytest tests/ -q`
- [ ] Write `docs/superpowers/acceptances/2026-11-04-E5-S2-acceptance.md`
- [ ] Sprint frontmatter → closed; roadmap S2 → closed; Epic remains active
- [ ] Commit docs; **no push**

---

## Spec coverage self-check

| Spec requirement | Task |
|---|---|
| Issues search + by_code | T1/T2/T3 |
| Projects list filter | T1/T3 |
| Saved Views apply on list | T1/T3 |
| Grouped UI + keyboard across groups | T1 flatten + T3 modal |
| Empty query Actions only | T1 |
| Vitest helpers | T1/T2 |
| Gates + acceptance | T4 |
| No S3 / no push | Global constraints |
