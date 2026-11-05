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

  it('tolerates missing rank and clips snippet to 120', () => {
    const long = 'x'.repeat(200);
    const flat = flattenSearchResults({
      issues: [{ id: 'i1', issueCode: 'OT-1', title: 'T', snippet: long }],
      projects: [{ id: 'p1', name: 'P', snippet: long, rank: 0.5 }],
      docs: [{ id: 'd1', title: 'D', parentType: 'project', parentId: 'p1', snippet: long, rank: 1 }],
      members: []
    });
    expect(flat[0].rank).toBeUndefined();
    expect(flat[0].subtitle?.includes('x'.repeat(120))).toBe(true);
    expect(flat[0].subtitle?.includes('x'.repeat(121))).toBe(false);
    expect(flat[1].rank).toBe(0.5);
    expect((flat[1].subtitle || '').length).toBeLessThanOrEqual(120);
    expect(flat[2].rank).toBe(1);
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


describe('E62 comments group', () => {
  it('flattens comments with issue deep-link (Q5a)', () => {
    const flat = flattenSearchResults({
      issues: [],
      projects: [],
      docs: [],
      members: [],
      comments: [
        {
          id: 'c1',
          issueId: 'i1',
          issueCode: 'OT-9',
          snippet: 'found in discussion',
          rank: 0.8
        }
      ]
    });
    expect(flat).toHaveLength(1);
    expect(flat[0].group).toBe('comments');
    expect(flat[0].href).toEqual({ path: '/issue/detail', query: { id: 'i1' } });
    expect(flat[0].subtitle).toContain('OT-9');
    expect(flat[0].rank).toBe(0.8);
  });

  it('tolerates missing comments key', () => {
    const flat = flattenSearchResults({
      issues: [{ id: 'i1', issueCode: 'OT-1', title: 'T' }],
      projects: [],
      docs: [],
      members: []
    } as any);
    expect(flat.map(f => f.group)).toEqual(['issues']);
  });
});
