import { describe, expect, it } from 'vitest';
import { buildDocHref, buildSearchPagePath, flattenSearchResults, moveActiveIndex } from './global-search';

describe('flattenSearchResults', () => {
  it('flattens groups in order with hrefs', () => {
    const flat = flattenSearchResults({
      issues: [{ id: 'i1', issueCode: 'OT-1', title: 'Login', status: 'open' }],
      projects: [{ id: 'p1', name: 'Alpha' }],
      docs: [
        { id: 'd1', title: 'Spec', parentType: 'project', parentId: 'p1', snippet: 'hi' },
        { id: 'd2', title: 'Issue note', parentType: 'issue', parentId: 'i1' },
        { id: 'd3', title: 'Init note', parentType: 'initiative', parentId: 'n1' }
      ],
      members: [{ userId: 'u1', name: 'Way', role: 'owner' }]
    });
    expect(flat.map(f => f.group)).toEqual(['issues', 'projects', 'docs', 'docs', 'docs', 'members']);
    expect(flat[0].href).toEqual({ path: '/issue/detail', query: { id: 'i1' } });
    expect(flat[1].href).toEqual({ path: '/workflow/project-detail', query: { id: 'p1' } });
    expect(flat[2].href).toEqual({ path: '/workflow/project-detail', query: { id: 'p1', doc: 'd1' } });
    expect(flat[3].href).toEqual({ path: '/issue/detail', query: { id: 'i1', doc: 'd2' } });
    expect(flat[4].href).toEqual({ path: '/initiatives/detail', query: { id: 'n1', doc: 'd3' } });
  });

  it('buildDocHref covers parent types', () => {
    expect(buildDocHref('project', 'p', 'd')).toEqual({
      path: '/workflow/project-detail',
      query: { id: 'p', doc: 'd' }
    });
    expect(buildDocHref('issue', 'i', 'd')).toEqual({ path: '/issue/detail', query: { id: 'i', doc: 'd' } });
    expect(buildDocHref('initiative', 'n', 'd')).toEqual({ path: '/initiatives/detail', query: { id: 'n', doc: 'd' } });
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
