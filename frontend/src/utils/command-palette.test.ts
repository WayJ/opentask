import { describe, expect, it, vi } from 'vitest';
import {
  buildFocusIssueActions,
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
  it('builds nav actions and filters by query', () => {
    const nav = vi.fn();
    const actions = buildNavActions(nav, {
      issues: 'Issues',
      createIssue: 'Create Issue',
      projects: 'Projects',
      inbox: 'Inbox',
      triage: 'Triage'
    });
    expect(actions.map(a => a.id)).toEqual([
      'nav.issues',
      'nav.create_issue',
      'nav.projects',
      'nav.inbox',
      'nav.triage'
    ]);
    actions[0].run();
    expect(nav).toHaveBeenCalledWith('/issue/list');

    const groupsEmpty = buildPaletteGroups({
      actions,
      menus: [],
      query: '',
      groupLabels: { actions: 'Actions', menus: 'Menus' }
    });
    expect(groupsEmpty).toHaveLength(1);
    expect(groupsEmpty[0].items).toHaveLength(5);

    const filtered = buildPaletteGroups({
      actions,
      menus: [],
      query: 'inbox',
      groupLabels: { actions: 'Actions', menus: 'Menus' }
    });
    expect(filtered[0].items.map(i => i.id)).toEqual(['nav.inbox']);
  });

  it('includes initiatives nav when titled', () => {
    const nav = vi.fn();
    const actions = buildNavActions(nav, {
      issues: 'Issues',
      createIssue: 'Create Issue',
      projects: 'Projects',
      inbox: 'Inbox',
      initiatives: 'Initiatives'
    });
    const item = actions.find(a => a.id === 'nav.initiatives');
    expect(item).toBeTruthy();
    item!.run();
    expect(nav).toHaveBeenCalledWith('/initiatives');
  });

  it('includes create-from-template action when titled', () => {
    const nav = vi.fn();
    const actions = buildNavActions(nav, {
      issues: 'Issues',
      createIssue: 'Create Issue',
      createFromTemplate: 'Create from template',
      projects: 'Projects',
      inbox: 'Inbox'
    });
    const item = actions.find(a => a.id === 'nav.create_from_template');
    expect(item).toBeTruthy();
    item!.run();
    expect(nav).toHaveBeenCalledWith('/issue/create?pickTemplate=1');
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

describe('buildPaletteGroups entity sections', () => {
  it('appends entity groups when query non-empty', () => {
    const groups = buildPaletteGroups({
      actions: [{ id: 'nav.issues', kind: 'action', title: 'Issues', run: () => undefined }],
      menus: [],
      query: 'fix',
      groupLabels: {
        actions: 'Actions',
        menus: 'Menus',
        issues: 'Issues',
        projects: 'Projects',
        views: 'Views',
        cycles: 'Cycles'
      },
      issues: [{ id: 'issue.1', kind: 'issue', title: 'Fix', run: () => undefined }],
      projects: [{ id: 'project.1', kind: 'project', title: 'Alpha', run: () => undefined }],
      savedViews: [{ id: 'view.1', kind: 'saved_view', title: 'Mine', run: () => undefined }],
      cycles: [{ id: 'cycle.1', kind: 'cycle', title: 'Cycle 1', run: () => undefined }]
    });
    expect(groups.map(g => g.id)).toEqual(['issues', 'projects', 'views', 'cycles']);
  });

  it('hides entity groups when query empty even if sources present', () => {
    const groups = buildPaletteGroups({
      actions: [{ id: 'nav.issues', kind: 'action', title: 'Issues', run: () => undefined }],
      menus: [],
      query: '',
      groupLabels: {
        actions: 'Actions',
        menus: 'Menus',
        issues: 'Issues',
        projects: 'Projects',
        views: 'Views'
      },
      issues: [{ id: 'issue.1', kind: 'issue', title: 'Fix', run: () => undefined }]
    });
    expect(groups.map(g => g.id)).toEqual(['actions']);
  });
});

describe('buildFocusIssueActions', () => {
  it('returns empty without focus', () => {
    expect(buildFocusIssueActions({ hasFocusedIssue: false, openLabels: () => {} })).toEqual([]);
  });

  it('returns Add label action when focused', () => {
    const openLabels = vi.fn();
    const items = buildFocusIssueActions({ hasFocusedIssue: true, openLabels, title: '添加标签…' });
    expect(items).toHaveLength(1);
    expect(items[0]?.id).toBe('action.labels');
    items[0]?.run();
    expect(openLabels).toHaveBeenCalled();
  });
});
