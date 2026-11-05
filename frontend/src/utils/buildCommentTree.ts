/**
 * E74: flat comments (+ parent_id) → depth-1 tree for FE rendering.
 * Orphan / depth>1 dirty rows become defensive roots (depth 0).
 */

export interface CommentLike {
  id: string;
  parent_id?: string | null;
  [key: string]: unknown;
}

export interface CommentTreeNode<T extends CommentLike = CommentLike> {
  comment: T;
  depth: 0 | 1;
  replies: T[];
}

export function buildCommentTree<T extends CommentLike>(comments: T[]): CommentTreeNode<T>[] {
  if (!comments.length) return [];

  const byId = new Map(comments.map(c => [c.id, c]));
  const childrenOf = new Map<string, T[]>();
  const roots: T[] = [];
  const deferred: T[] = [];

  for (const c of comments) {
    const pid = c.parent_id ?? null;
    if (!pid) {
      roots.push(c);
      continue;
    }
    const parent = byId.get(pid);
    // Only nest under a present root (parent_id IS NULL). Else defensive root.
    if (parent && (parent.parent_id == null || parent.parent_id === '')) {
      const list = childrenOf.get(pid) || [];
      list.push(c);
      childrenOf.set(pid, list);
    } else {
      deferred.push(c);
    }
  }

  const nodes: CommentTreeNode<T>[] = [];
  const emitted = new Set<string>();

  for (const root of roots) {
    const replies = childrenOf.get(root.id) || [];
    nodes.push({ comment: root, depth: 0, replies });
    emitted.add(root.id);
    for (const r of replies) emitted.add(r.id);
  }

  for (const orphan of deferred) {
    if (!emitted.has(orphan.id)) {
      nodes.push({ comment: orphan, depth: 0, replies: [] });
      emitted.add(orphan.id);
    }
  }

  for (const c of comments) {
    if (!emitted.has(c.id)) {
      nodes.push({ comment: c, depth: 0, replies: [] });
    }
  }

  return nodes;
}
