import { describe, expect, it } from 'vitest';
import { buildCommentTree } from './buildCommentTree';

describe('buildCommentTree', () => {
  it('returns empty for empty input', () => {
    expect(buildCommentTree([])).toEqual([]);
  });

  it('keeps root-only flat as depth-0 nodes', () => {
    const tree = buildCommentTree([
      { id: 'a', parent_id: null, content: 'A' },
      { id: 'b', parent_id: null, content: 'B' },
    ]);
    expect(tree.map(n => n.comment.id)).toEqual(['a', 'b']);
    expect(tree.every(n => n.depth === 0)).toBe(true);
    expect(tree.every(n => n.replies.length === 0)).toBe(true);
  });

  it('nests depth-1 replies under root', () => {
    const tree = buildCommentTree([
      { id: 'root', parent_id: null, content: 'R' },
      { id: 'r1', parent_id: 'root', content: '1' },
      { id: 'r2', parent_id: 'root', content: '2' },
    ]);
    expect(tree).toHaveLength(1);
    expect(tree[0].comment.id).toBe('root');
    expect(tree[0].replies.map(c => c.id)).toEqual(['r1', 'r2']);
  });

  it('appends orphan / depth>1 as defensive roots', () => {
    const tree = buildCommentTree([
      { id: 'root', parent_id: null, content: 'R' },
      { id: 'deep', parent_id: 'missing-mid', content: 'D' },
      { id: 'orphan', parent_id: 'gone', content: 'O' },
    ]);
    const ids = tree.map(n => n.comment.id);
    expect(ids).toContain('root');
    expect(ids).toContain('deep');
    expect(ids).toContain('orphan');
    expect(tree.find(n => n.comment.id === 'deep')?.depth).toBe(0);
  });

  it('preserves root order and reply order', () => {
    const tree = buildCommentTree([
      { id: 'a', parent_id: null },
      { id: 'b', parent_id: null },
      { id: 'a1', parent_id: 'a' },
      { id: 'b1', parent_id: 'b' },
      { id: 'a2', parent_id: 'a' },
    ]);
    expect(tree.map(n => n.comment.id)).toEqual(['a', 'b']);
    expect(tree[0].replies.map(c => c.id)).toEqual(['a1', 'a2']);
    expect(tree[1].replies.map(c => c.id)).toEqual(['b1']);
  });
});
