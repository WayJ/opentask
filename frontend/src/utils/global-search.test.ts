import { describe, expect, it } from 'vitest';
import { buildSearchPagePath, flattenSearchResults, moveActiveIndex } from './global-search';

describe('flattenSearchResults', () => {
  it('flattens groups in order with hrefs', () => {
    const flat = flattenSearchResults({
      issues: [{ id: 'i1', issueCode: 'OT-1', title: 'Login', status: 'open' }],
      projects: [{ id: 'p1', name: 'Alpha' }],
      docs: [{ id: 'd1', title: 'Spec', parentType: 'project', parentId: 'p1', snippet: 'hi' }],
      members: [{ userId: 'u1', name: 'Way', role: 'owner' }]
    });
    expect(flat.map(f => f.group)).toEqual(['issues', 'projects', 'docs', 'members']);
    expect(flat[0].href).toEqual({ path: '/issue/detail', query: { id: 'i1' } });
    expect(flat[1].href).toEqual({ path: '/workflow/project-detail', query: { id: 'p1' } });
  });
});

describe('moveActiveIndex', () => {
  it('wraps around', () => {
    expect(moveActiveIndex(0, -1, 3)).toBe(2);
    expect(moveActiveIndex(2, 1, 3)).toBe(0);
    expect(moveActiveIndex(-1, 1, 3)).toBe(0);
    expect(moveActiveIndex(1, 0, 0)).toBe(-1);
  });
});

describe('buildSearchPagePath', () => {
  it('omits query when empty', () => {
    expect(buildSearchPagePath('')).toBe('/search');
    expect(buildSearchPagePath('  OT-1 ')).toEqual({ path: '/search', query: { q: 'OT-1' } });
  });
});
