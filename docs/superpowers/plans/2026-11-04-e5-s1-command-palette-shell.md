# E5-S1 Command Palette Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or subagent-driven-development) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a Linear-style ⌘K/Ctrl+K Command Palette shell with Actions + Menus navigation, always-on hotkeys independent of `theme.header.globalSearch.visible`, without entity search (S2) or C/A/S/P/I focus (S3).

**Architecture:** Extract pure palette/hotkey helpers for Vitest; hold open/query/activeIndex/sources in a module-singleton `useCommandPalette`; mount a single modal host + `useAppHotkeys` from `base-layout`; header `GlobalSearch` button only calls `open()`. Upgrade soybean `global-search` UI to grouped Actions/Menus.

**Tech Stack:** Vue 3 + TypeScript + Naive UI `NModal` + `@vueuse/core` 14.1.0 (`useEventListener` / `onKeyStroke`) + Vitest (happy-dom). No new deps (no cmdk / hotkeys-js).

## Global Constraints

- Local worktree `/workspace/opentask-worktrees/E5-S1`, branch `sprint/E5-S1`; **no remote push**
- Zero new npm dependencies
- S1 only: no Issues/Projects/Views entity search; no single-letter C/A/S/P/I; no `useIssueFocus`
- `theme.header.globalSearch.visible` controls header icon only — never unmounts palette/hotkeys
- Single modal instance (no double NModal)
- Chinese comments OK sparingly; identifiers English
- Gates: focused vitest PASS; `npm run lint` 0 errors; `npm run build` ok; `uv run pytest tests/ -q` regression green (~621+)
- Do **not** set roadmap Epic status to local-complete (S2/S3 remain)

---

### Task 1: Pure helpers + Vitest (TDD)

**Files:**
- Create: `frontend/src/utils/command-palette.ts`
- Create: `frontend/src/utils/hotkeys.ts`
- Create: `frontend/src/utils/command-palette.test.ts`
- Create: `frontend/src/utils/hotkeys.test.ts`

**Interfaces:**
- Produces: `PaletteItem`, `PaletteGroup`, `itemMatchesQuery`, `buildNavActions`, `menusToPaletteItems`, `buildPaletteGroups`, `flattenGroupItems`, `clampActiveIndex`, `isModK`, `ignoreWhenEditable`

- [ ] **Step 1: Write failing hotkeys tests**

```ts
import { describe, expect, it } from 'vitest';
import { ignoreWhenEditable, isModK } from './hotkeys';

describe('isModK', () => {
  it('matches Meta+K', () => {
    expect(isModK({ key: 'k', metaKey: true, ctrlKey: false })).toBe(true);
    expect(isModK({ key: 'K', metaKey: true, ctrlKey: false })).toBe(true);
  });
  it('matches Ctrl+K', () => {
    expect(isModK({ key: 'k', metaKey: false, ctrlKey: true })).toBe(true);
  });
  it('rejects K without modifier and other keys', () => {
    expect(isModK({ key: 'k', metaKey: false, ctrlKey: false })).toBe(false);
    expect(isModK({ key: 'Escape', metaKey: true, ctrlKey: false })).toBe(false);
  });
});

describe('ignoreWhenEditable', () => {
  it('is true for input/textarea/select', () => {
    const input = document.createElement('input');
    expect(ignoreWhenEditable(input)).toBe(true);
    expect(ignoreWhenEditable(document.createElement('textarea'))).toBe(true);
    expect(ignoreWhenEditable(document.createElement('select'))).toBe(true);
  });
  it('is true for contenteditable ancestor', () => {
    const wrap = document.createElement('div');
    wrap.setAttribute('contenteditable', 'true');
    const child = document.createElement('span');
    wrap.appendChild(child);
    document.body.appendChild(wrap);
    expect(ignoreWhenEditable(child)).toBe(true);
    wrap.remove();
  });
  it('is false for plain div', () => {
    expect(ignoreWhenEditable(document.createElement('div'))).toBe(false);
    expect(ignoreWhenEditable(null)).toBe(false);
  });
});
```

- [ ] **Step 2: Run tests — expect FAIL (module missing)**

Run: `cd frontend && npm test -- --run src/utils/hotkeys.test.ts`
Expected: FAIL cannot find module `./hotkeys`

- [ ] **Step 3: Minimal hotkeys implementation**

```ts
// frontend/src/utils/hotkeys.ts
export function isModK(event: { key: string; metaKey: boolean; ctrlKey: boolean }): boolean {
  return (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k';
}

const EDITABLE_SELECTOR = 'input, textarea, select, [contenteditable="true"], .n-input, .n-base-selection-input';

export function ignoreWhenEditable(target: EventTarget | null): boolean {
  if (!target || !(target instanceof Element)) return false;
  if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement) {
    return true;
  }
  if (target.closest(EDITABLE_SELECTOR)) return true;
  return false;
}
```

- [ ] **Step 4: Run hotkeys tests — expect PASS**

- [ ] **Step 5: Write failing command-palette tests**

```ts
import { describe, expect, it, vi } from 'vitest';
import {
  buildNavActions,
  buildPaletteGroups,
  clampActiveIndex,
  flattenGroupItems,
  itemMatchesQuery,
  menusToPaletteItems
} from './command-palette';

describe('itemMatchesQuery', () => {
  const item = { id: 'a', kind: 'action' as const, title: 'Create Issue', keywords: ['new', 'c'], run: () => undefined };
  it('matches empty query', () => expect(itemMatchesQuery(item, '')).toBe(true));
  it('matches title case-insensitive', () => expect(itemMatchesQuery(item, 'create')).toBe(true));
  it('matches keywords', () => expect(itemMatchesQuery(item, 'new')).toBe(true));
  it('rejects non-match', () => expect(itemMatchesQuery(item, 'zzz')).toBe(false));
});

describe('buildNavActions + groups', () => {
  it('builds four nav actions and filters by query', () => {
    const nav = vi.fn();
    const actions = buildNavActions(nav, {
      issues: 'Issues',
      createIssue: 'Create Issue',
      projects: 'Projects',
      inbox: 'Inbox'
    });
    expect(actions.map(a => a.id)).toEqual(['nav.issues', 'nav.create_issue', 'nav.projects', 'nav.inbox']);
    actions[0].run();
    expect(nav).toHaveBeenCalledWith('/issue/list');
    const groupsEmpty = buildPaletteGroups({
      actions,
      menus: [],
      query: '',
      groupLabels: { actions: 'Actions', menus: 'Menus' }
    });
    expect(groupsEmpty).toHaveLength(1);
    expect(groupsEmpty[0].items).toHaveLength(4);
    const filtered = buildPaletteGroups({
      actions,
      menus: [],
      query: 'inbox',
      groupLabels: { actions: 'Actions', menus: 'Menus' }
    });
    expect(filtered[0].items.map(i => i.id)).toEqual(['nav.inbox']);
  });

  it('includes Menus group when menus match', () => {
    const nav = vi.fn();
    const menus = menusToPaletteItems(
      [{ routePath: '/workflow/projects', label: 'Projects Menu', i18nKey: null }],
      m => m.label,
      nav
    );
    const groups = buildPaletteGroups({
      actions: [],
      menus,
      query: 'projects',
      groupLabels: { actions: 'Actions', menus: 'Menus' }
    });
    expect(groups.map(g => g.id)).toEqual(['menus']);
    expect(groups[0].items[0].id).toBe('menu./workflow/projects');
  });
});

describe('flatten + clamp', () => {
  it('flattens and clamps active index', () => {
    const flat = flattenGroupItems([
      { id: 'a', label: 'A', items: [{ id: '1', kind: 'action', title: '1', run: () => undefined }] },
      { id: 'b', label: 'B', items: [{ id: '2', kind: 'action', title: '2', run: () => undefined }] }
    ]);
    expect(flat.map(i => i.id)).toEqual(['1', '2']);
    expect(clampActiveIndex(5, 2)).toBe(1);
    expect(clampActiveIndex(-1, 2)).toBe(0);
    expect(clampActiveIndex(0, 0)).toBe(0);
  });
});
```

- [ ] **Step 6: Run — expect FAIL missing module**

- [ ] **Step 7: Implement `command-palette.ts`**

```ts
export type PaletteItemKind = 'action' | 'menu' | 'issue' | 'project' | 'saved_view';

export interface PaletteItem {
  id: string;
  kind: PaletteItemKind;
  title: string;
  subtitle?: string;
  keywords?: string[];
  icon?: string;
  run: () => void | Promise<void>;
}

export interface PaletteGroup {
  id: string;
  label: string;
  items: PaletteItem[];
}

export function itemMatchesQuery(item: PaletteItem, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  const hay = [item.title, item.subtitle ?? '', ...(item.keywords ?? [])].join(' ').toLowerCase();
  return hay.includes(q);
}

export function buildNavActions(
  navigate: (path: string) => void,
  titles: { issues: string; createIssue: string; projects: string; inbox: string }
): PaletteItem[] {
  return [
    { id: 'nav.issues', kind: 'action', title: titles.issues, keywords: ['issues', 'list', 'issue'], run: () => navigate('/issue/list') },
    { id: 'nav.create_issue', kind: 'action', title: titles.createIssue, keywords: ['create', 'new', 'issue'], run: () => navigate('/issue/create') },
    { id: 'nav.projects', kind: 'action', title: titles.projects, keywords: ['projects', 'project'], run: () => navigate('/workflow/projects') },
    { id: 'nav.inbox', kind: 'action', title: titles.inbox, keywords: ['inbox', '通知'], run: () => navigate('/inbox') }
  ];
}

export function menusToPaletteItems(
  menus: Array<{ routePath: string; label: string; i18nKey?: string | null }>,
  resolveTitle: (m: { routePath: string; label: string; i18nKey?: string | null }) => string,
  navigate: (path: string) => void
): PaletteItem[] {
  return menus.map(m => ({
    id: `menu.${m.routePath}`,
    kind: 'menu' as const,
    title: resolveTitle(m),
    keywords: [m.label, m.routePath],
    run: () => navigate(m.routePath)
  }));
}

export function buildPaletteGroups(opts: {
  actions: PaletteItem[];
  menus: PaletteItem[];
  query: string;
  groupLabels: { actions: string; menus: string };
}): PaletteGroup[] {
  const groups: PaletteGroup[] = [];
  const actionItems = opts.actions.filter(i => itemMatchesQuery(i, opts.query));
  if (actionItems.length) groups.push({ id: 'actions', label: opts.groupLabels.actions, items: actionItems });
  const menuItems = opts.menus.filter(i => itemMatchesQuery(i, opts.query));
  // Menus: empty query → hide (soybean legacy required keyword); non-empty → show matches
  // S1 decision: empty query shows Actions only; with query also filter Menus (and Actions)
  if (opts.query.trim() && menuItems.length) {
    groups.push({ id: 'menus', label: opts.groupLabels.menus, items: menuItems });
  }
  return groups;
}

export function flattenGroupItems(groups: PaletteGroup[]): PaletteItem[] {
  return groups.flatMap(g => g.items);
}

export function clampActiveIndex(index: number, length: number): number {
  if (length <= 0) return 0;
  if (index < 0) return 0;
  if (index >= length) return length - 1;
  return index;
}
```

**Note on Menus empty-query:** Legacy modal only searched when keyword non-empty. S1 keeps that for Menus; Actions always show (empty or filtered).

- [ ] **Step 8: Run both test files — PASS**

- [ ] **Step 9: Commit**

```bash
git add frontend/src/utils/command-palette.ts frontend/src/utils/command-palette.test.ts frontend/src/utils/hotkeys.ts frontend/src/utils/hotkeys.test.ts docs/superpowers/plans/2026-11-04-e5-s1-command-palette-shell.md
git commit -m "docs(E5-S1): plan + feat: palette/hotkeys pure helpers with vitest"
```

(If plan committed separately first, helpers alone is fine.)

---

### Task 2: `useCommandPalette` singleton composable (TDD)

**Files:**
- Create: `frontend/src/composables/use-command-palette.ts`
- Create: `frontend/src/composables/use-command-palette.test.ts`

**Interfaces:**
- Consumes: helpers from Task 1
- Produces: `useCommandPalette()`, `__resetCommandPaletteForTests()`

- [ ] **Step 1: Failing composable tests**

```ts
import { describe, expect, it, beforeEach, vi } from 'vitest';
import { useCommandPalette, __resetCommandPaletteForTests } from './use-command-palette';
import type { PaletteItem } from '@/utils/command-palette';

describe('useCommandPalette', () => {
  beforeEach(() => {
    __resetCommandPaletteForTests();
  });

  it('open/close/toggle and clears query on close', () => {
    const p = useCommandPalette();
    expect(p.isOpen.value).toBe(false);
    p.open();
    expect(p.isOpen.value).toBe(true);
    p.setQuery('abc');
    expect(p.query.value).toBe('abc');
    p.close();
    expect(p.isOpen.value).toBe(false);
    expect(p.query.value).toBe('');
    p.toggle();
    expect(p.isOpen.value).toBe(true);
    p.toggle();
    expect(p.isOpen.value).toBe(false);
  });

  it('groups actions and navigates on runActive', async () => {
    const run = vi.fn();
    const actions: PaletteItem[] = [
      { id: 'nav.issues', kind: 'action', title: 'Issues', run },
      { id: 'nav.inbox', kind: 'action', title: 'Inbox', keywords: ['inbox'], run: vi.fn() }
    ];
    const p = useCommandPalette();
    p.setSources({ actions, menus: [] });
    p.open();
    expect(p.groups.value[0].items).toHaveLength(2);
    p.setQuery('inbox');
    expect(p.flatItems.value.map(i => i.id)).toEqual(['nav.inbox']);
    expect(p.activeIndex.value).toBe(0);
    await p.runActive();
    expect(actions[1].run).toHaveBeenCalled();
    expect(p.isOpen.value).toBe(false);
  });

  it('moveDown/moveUp wraps', () => {
    const p = useCommandPalette();
    p.setSources({
      actions: [
        { id: 'a', kind: 'action', title: 'A', run: () => undefined },
        { id: 'b', kind: 'action', title: 'B', run: () => undefined }
      ],
      menus: []
    });
    p.open();
    p.moveDown();
    expect(p.activeIndex.value).toBe(1);
    p.moveDown();
    expect(p.activeIndex.value).toBe(0);
    p.moveUp();
    expect(p.activeIndex.value).toBe(1);
  });
});
```

- [ ] **Step 2: Run — FAIL missing composable**

- [ ] **Step 3: Implement composable**

```ts
import { computed, ref } from 'vue';
import {
  buildPaletteGroups,
  clampActiveIndex,
  flattenGroupItems,
  type PaletteGroup,
  type PaletteItem
} from '@/utils/command-palette';

const isOpen = ref(false);
const query = ref('');
const activeIndex = ref(0);
const actionSource = ref<PaletteItem[]>([]);
const menuSource = ref<PaletteItem[]>([]);
const groupLabels = ref({ actions: 'Actions', menus: 'Menus' });

export function __resetCommandPaletteForTests() {
  isOpen.value = false;
  query.value = '';
  activeIndex.value = 0;
  actionSource.value = [];
  menuSource.value = [];
  groupLabels.value = { actions: 'Actions', menus: 'Menus' };
}

export function useCommandPalette() {
  const groups = computed<PaletteGroup[]>(() =>
    buildPaletteGroups({
      actions: actionSource.value,
      menus: menuSource.value,
      query: query.value,
      groupLabels: groupLabels.value
    })
  );

  const flatItems = computed(() => flattenGroupItems(groups.value));
  const activeItem = computed(() => flatItems.value[activeIndex.value] ?? null);

  function open() {
    isOpen.value = true;
  }

  function close() {
    isOpen.value = false;
    query.value = '';
    activeIndex.value = 0;
  }

  function toggle() {
    if (isOpen.value) close();
    else open();
  }

  function setQuery(q: string) {
    query.value = q;
    activeIndex.value = 0;
  }

  function setSources(opts: { actions: PaletteItem[]; menus: PaletteItem[] }) {
    actionSource.value = opts.actions;
    menuSource.value = opts.menus;
    activeIndex.value = clampActiveIndex(activeIndex.value, flattenGroupItems(
      buildPaletteGroups({
        actions: opts.actions,
        menus: opts.menus,
        query: query.value,
        groupLabels: groupLabels.value
      })
    ).length);
  }

  function setGroupLabels(labels: { actions: string; menus: string }) {
    groupLabels.value = labels;
  }

  function moveDown() {
    const len = flatItems.value.length;
    if (!len) return;
    activeIndex.value = (activeIndex.value + 1) % len;
  }

  function moveUp() {
    const len = flatItems.value.length;
    if (!len) return;
    activeIndex.value = (activeIndex.value - 1 + len) % len;
  }

  async function run(item: PaletteItem) {
    close();
    await item.run();
  }

  async function runActive() {
    const item = activeItem.value;
    if (!item) return;
    await run(item);
  }

  return {
    isOpen,
    query,
    activeIndex,
    groups,
    flatItems,
    activeItem,
    open,
    close,
    toggle,
    setQuery,
    setSources,
    setGroupLabels,
    moveUp,
    moveDown,
    run,
    runActive
  };
}
```

- [ ] **Step 4: Tests PASS**

- [ ] **Step 5: Commit** `feat(E5-S1): useCommandPalette singleton composable`

---

### Task 3: `useAppHotkeys` + host wiring

**Files:**
- Create: `frontend/src/composables/use-app-hotkeys.ts`
- Modify: `frontend/src/layouts/modules/global-search/components/search-modal.vue` (grouped UI bound to palette)
- Modify: `frontend/src/layouts/modules/global-search/components/search-result.vue` (accept PaletteItem rows / grouped)
- Modify: `frontend/src/layouts/modules/global-search/index.vue` (button → `open()` only; **no** local modal)
- Create: `frontend/src/layouts/modules/global-search/command-palette-host.vue` (modal + hotkeys + source wiring)
- Modify: `frontend/src/layouts/base-layout/index.vue` (unconditional host mount)
- Modify: i18n `zh-cn.ts` / `en-us.ts` + `app.d.ts` Schema for `common.commandPalette.*`

**Interfaces:**
- Consumes: `useCommandPalette`, `isModK`, `buildNavActions`, `menusToPaletteItems`, `$t`, `useRouter`, `useRouteStore`

- [ ] **Step 1: Implement `useAppHotkeys`**

```ts
import { useEventListener } from '@vueuse/core';
import { isModK } from '@/utils/hotkeys';
import { useCommandPalette } from './use-command-palette';

/** S1: Meta/Ctrl+K toggle; Esc closes. Single-letter keys deferred to S3. */
export function useAppHotkeys() {
  const palette = useCommandPalette();

  useEventListener(window, 'keydown', (event: KeyboardEvent) => {
    if (isModK(event)) {
      event.preventDefault();
      palette.toggle();
      return;
    }
    if (event.key === 'Escape' && palette.isOpen.value) {
      event.preventDefault();
      palette.close();
    }
  });
}
```

- [ ] **Step 2: `command-palette-host.vue`**

- On setup: `useAppHotkeys()`; `watchEffect`/`watch` to `setSources` from `buildNavActions(router.push)` + `menusToPaletteItems(routeStore.searchMenus, …)`; `setGroupLabels` from `$t`
- Render upgraded `SearchModal` bound to `palette.isOpen` (v-model via computed get/set) OR inline modal using palette API
- Prefer: refactor `search-modal.vue` to read/write `useCommandPalette()` directly (no props show), host just mounts `<SearchModal />` + hotkeys

**search-modal.vue behavior (S1):**
- `const palette = useCommandPalette()`
- `NModal v-model:show="palette.isOpen"` with `@update:show` calling close when false
- Input bound to `palette.query` / `setQuery`
- Render groups: for each group, small label + rows
- ↑↓ Enter: call `moveUp`/`moveDown`/`runActive` via `onKeyStroke` **only when open** (guard with `if (!palette.isOpen.value) return`)
- Click row → `run(item)`
- Footer unchanged

**search-result.vue:** change props to accept `{ id, title, active }` list or keep and pass flattened display; simplest: replace with inline rows in modal that highlight by `item.id === activeItem?.id`.

- [ ] **Step 3: GlobalSearch index — button only**

```vue
<script lang="ts" setup>
import { $t } from '@/locales';
import { useCommandPalette } from '@/composables/use-command-palette';
defineOptions({ name: 'GlobalSearch' });
const { open } = useCommandPalette();
</script>
<template>
  <ButtonIcon :tooltip-content="$t('common.search')" @click="open">
    <icon-uil-search />
  </ButtonIcon>
</template>
```

- [ ] **Step 4: base-layout mount host**

```vue
import CommandPaletteHost from '../modules/global-search/command-palette-host.vue';
// in template after ThemeDrawer:
<CommandPaletteHost />
```

- [ ] **Step 5: i18n keys**

Under `common.commandPalette`:
- `placeholder`, `groupActions`, `groupMenus`, `navIssues`, `navCreateIssue`, `navProjects`, `navInbox`

Add matching types in `App.I18n.Schema` `common.commandPalette`.

- [ ] **Step 6: Manual sanity** — ensure no second modal in header path

- [ ] **Step 7: Commit** `feat(E5-S1): ⌘K command palette host + Actions/Menus UI`

---

### Task 4: Gates + acceptance + sprint close

**Files:**
- Create: `docs/superpowers/acceptances/2026-11-04-E5-S1-acceptance.md`
- Modify: `docs/superpowers/sprints/2026-11-04-E5-S1-plan.md` → `state: closed`, acceptance-record, closed-at
- Modify: roadmap S1 state → closed (Epic remains `active`; S2/S3 planned)

- [ ] **Step 1: Focused vitest**

```bash
cd frontend && npm test -- --run src/utils/hotkeys.test.ts src/utils/command-palette.test.ts src/composables/use-command-palette.test.ts
```

Expected: all PASS

- [ ] **Step 2: lint**

```bash
cd frontend && npm run lint
```

Expected: 0 errors (warnings OK)

- [ ] **Step 3: build**

```bash
cd frontend && npm run build
```

Expected: success

- [ ] **Step 4: pytest regression**

```bash
cd backend && uv run pytest tests/ -q
```

Expected: ~621+ passed, 0 failed

- [ ] **Step 5: Write acceptance** (mirror E4-S3 format; fingerprint = impl SHA; browser R1–R3 optional blocked if no E2E)

- [ ] **Step 6: Update sprint frontmatter closed; roadmap S1 closed; Epic status stays active**

- [ ] **Step 7: Final commit** `docs(E5-S1): acceptance + close sprint` — **no push**

---

## Spec coverage self-check

| Spec / Sprint DoD | Task |
|---|---|
| useCommandPalette open/close/query/groups/run | T2 |
| Static Actions Issues/Create/Projects/Inbox | T1/T3 |
| Menus from searchMenus | T1/T3 |
| Grouped modal UI ↑↓ Enter Esc | T3 |
| Header button shared open | T3 |
| base-layout always mount + ⌘K | T3 |
| visible=false still ⌘K | T3 (host unconditional) |
| No entity search / no C/A/S/P/I | excluded |
| Vitest + lint + build + pytest | T4 |
| No push | T4 |

## Placeholder scan

None intentional. Menu empty-query behavior documented in Task 1.

## Type consistency

`PaletteItem` / `PaletteGroup` / `useCommandPalette` API names stable across tasks.
