/**
 * E4-S3：在当前筛选结果内做 depth-1 嵌套排序。
 * - 有 parent 且父在集合内 → 紧跟父后，depth=1
 * - 父不在集合 → 作为顶层 depth=0
 * - 更深层级本轮不展开（仍 depth=1 展示）
 */
import type { Api } from '@/typings/api';

export interface NestedIssueRow {
  issue: Api.Issue.Issue;
  depth: 0 | 1;
}

export function nestIssuesDepth1(issues: Api.Issue.Issue[]): NestedIssueRow[] {
  if (!issues.length) return [];

  const byId = new Map(issues.map(i => [i.id, i]));
  const childrenOf = new Map<string, Api.Issue.Issue[]>();
  const roots: Api.Issue.Issue[] = [];

  for (const issue of issues) {
    const parentId = issue.parent_issue_id;
    if (parentId && byId.has(parentId)) {
      const list = childrenOf.get(parentId) || [];
      list.push(issue);
      childrenOf.set(parentId, list);
    } else {
      roots.push(issue);
    }
  }

  const rows: NestedIssueRow[] = [];
  const emitted = new Set<string>();

  for (const root of roots) {
    rows.push({ issue: root, depth: 0 });
    emitted.add(root.id);
    const kids = childrenOf.get(root.id) || [];
    for (const kid of kids) {
      rows.push({ issue: kid, depth: 1 });
      emitted.add(kid.id);
    }
  }

  // 防御：若某节点既被当作子又因环/遗漏未 emit（不应发生），追加为顶层
  for (const issue of issues) {
    if (!emitted.has(issue.id)) {
      rows.push({ issue, depth: 0 });
    }
  }

  return rows;
}
