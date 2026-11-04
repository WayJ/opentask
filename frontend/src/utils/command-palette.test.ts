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
  const item = {
    id: 'a',
    kind: 'action' as const,
    title: 'Create Issue',
    keywords: ['new', 'c'],
    run: () => undefined
  };

  it('matches empty query', () => {
    expect(itemMatchesQuery(item, '')).toBe(true);
  });

  it('matches title case-insensitive', () => {
    expect(itemMatchesQuery(item, 'create')).toBe(true);
  });

  it('matches keywords', () => {
    expect(itemMatchesQuery(item, 'new')).toBe(true);
  });

  it('rejects non-match', () => {
    expect(itemMatchesQuery(item, 'zzz')).toBe(false);
  });
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
