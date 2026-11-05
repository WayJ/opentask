import { describe, expect, it } from 'vitest';
import {
  favoriteLabel,
  favoriteNavTarget,
  findFavoriteId,
  groupFavoritesByType,
  sortFavoritesByPosition
} from './favorites';

describe('sortFavoritesByPosition', () => {
  it('orders ascending by position', () => {
    const rows = [
      { id: 'a', position: 2 },
      { id: 'b', position: 0 },
      { id: 'c', position: 1 }
    ];
    expect(sortFavoritesByPosition(rows).map(r => r.id)).toEqual(['b', 'c', 'a']);
  });
});

describe('groupFavoritesByType', () => {
  it('buckets by targetType', () => {
    const grouped = groupFavoritesByType([
      { targetType: 'issue', id: '1' },
      { targetType: 'project', id: '2' },
      { targetType: 'saved_view', id: '3' },
      { targetType: 'project', id: '4' }
    ]);
    expect(grouped.project.map(r => r.id)).toEqual(['2', '4']);
    expect(grouped.issue.map(r => r.id)).toEqual(['1']);
    expect(grouped.saved_view.map(r => r.id)).toEqual(['3']);
  });
});

describe('findFavoriteId', () => {
  it('returns id when pinned', () => {
    const id = findFavoriteId([{ id: 'f1', targetType: 'project', targetId: 'p1', position: 0 }], 'project', 'p1');
    expect(id).toBe('f1');
  });

  it('returns null when not pinned', () => {
    expect(findFavoriteId([], 'issue', 'x')).toBeNull();
  });
});

describe('favoriteNavTarget', () => {
  it('routes project / issue / saved_view', () => {
    expect(favoriteNavTarget({ id: '1', targetType: 'project', targetId: 'p', position: 0 })).toEqual({
      path: '/workflow/project-detail',
      query: { id: 'p' }
    });
    expect(favoriteNavTarget({ id: '1', targetType: 'issue', targetId: 'i', position: 0 })).toEqual({
      path: '/issue/detail',
      query: { id: 'i' }
    });
    expect(favoriteNavTarget({ id: '1', targetType: 'saved_view', targetId: 'v', position: 0 })).toEqual({
      path: '/issue/list',
      query: { view: 'v' }
    });
  });
});

describe('favoriteLabel', () => {
  it('prefers name then code', () => {
    expect(
      favoriteLabel({
        id: '1',
        targetType: 'issue',
        targetId: 'abcdefgh',
        position: 0,
        target: { id: 'abcdefgh', type: 'issue', name: 'Hello', code: 'OT-1' }
      })
    ).toBe('Hello');
    expect(
      favoriteLabel({
        id: '1',
        targetType: 'issue',
        targetId: 'abcdefgh',
        position: 0,
        target: { id: 'abcdefgh', type: 'issue', name: '', code: 'OT-1' }
      })
    ).toBe('OT-1');
  });
});
