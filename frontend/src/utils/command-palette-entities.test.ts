import { describe, expect, it, vi } from 'vitest';
import type { SavedView } from '@/service/api/saved-views';
import {
  filterByNameQuery,
  issuesToPaletteItems,
  looksLikeIssueCode,
  projectsToPaletteItems,
  resolveIssueSearchPlan,
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

describe('resolveIssueSearchPlan', () => {
  it('flags by-code when query looks like an issue code', () => {
    expect(resolveIssueSearchPlan('OT-12')).toEqual({ search: 'OT-12', fetchByCode: true, code: 'OT-12' });
  });

  it('uses plain search otherwise', () => {
    expect(resolveIssueSearchPlan('  login  ')).toEqual({ search: 'login', fetchByCode: false });
  });
});

describe('entity mappers', () => {
  it('maps issues with subtitle code and navigates detail', () => {
    const nav = vi.fn();
    const items = issuesToPaletteItems([{ id: 'i1', title: 'Fix login', issue_code: 'OT-1' } as Api.Issue.Issue], nav);
    expect(items[0]).toMatchObject({
      id: 'issue.i1',
      kind: 'issue',
      title: 'Fix login',
      subtitle: 'OT-1'
    });
    items[0].run();
    expect(nav).toHaveBeenCalledWith({ path: '/issue/detail', query: { id: 'i1' } });
  });

  it('maps projects and saved views', () => {
    const nav = vi.fn();
    const apply = vi.fn();
    const projects = projectsToPaletteItems([{ id: 'p1', name: 'Alpha' } as Api.Project.Project], nav);
    expect(projects[0].kind).toBe('project');
    projects[0].run();
    expect(nav).toHaveBeenCalledWith({ path: '/workflow/project-detail', query: { id: 'p1' } });

    const views = savedViewsToPaletteItems([{ id: 'v1', name: 'My Open', isFavorite: true } as SavedView], apply);
    expect(views[0].kind).toBe('saved_view');
    views[0].run();
    expect(apply).toHaveBeenCalledWith('v1');
  });

  it('filterByNameQuery is case-insensitive includes; empty query yields none', () => {
    expect(filterByNameQuery([{ name: 'Alpha' }, { name: 'Beta' }], 'alp').map(x => x.name)).toEqual(['Alpha']);
    expect(filterByNameQuery([{ name: 'Alpha' }], '')).toEqual([]);
  });
});
