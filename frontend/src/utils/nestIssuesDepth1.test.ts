import { describe, expect, it } from 'vitest';
import type { Api } from '@/typings/api';
import { nestIssuesDepth1 } from './nestIssuesDepth1';

function issue(partial: Partial<Api.Issue.Issue> & { id: string; title: string }): Api.Issue.Issue {
  return {
    type: 'feature',
    status: 'open',
    priority: 'medium',
    reporter_id: 'u1',
    issue_code: `ISSUE-${partial.id}`,
    view_count: 0,
    comment_count: 0,
    attachment_count: 0,
    is_deleted: false,
    created_at: '2026-11-04T00:00:00Z',
    updated_at: '2026-11-04T00:00:00Z',
    ...partial
  } as Api.Issue.Issue;
}

describe('nestIssuesDepth1', () => {
  it('returns empty for empty input', () => {
    expect(nestIssuesDepth1([])).toEqual([]);
  });

  it('keeps flat list when no parents', () => {
    const a = issue({ id: 'a', title: 'A' });
    const b = issue({ id: 'b', title: 'B' });
    const rows = nestIssuesDepth1([a, b]);
    expect(rows.map(r => [r.issue.id, r.depth])).toEqual([
      ['a', 0],
      ['b', 0]
    ]);
  });

  it('nests child under parent when both present', () => {
    const p = issue({ id: 'p', title: 'Parent' });
    const c = issue({ id: 'c', title: 'Child', parent_issue_id: 'p' });
    const other = issue({ id: 'o', title: 'Other' });
    const rows = nestIssuesDepth1([c, other, p]);
    expect(rows.map(r => [r.issue.id, r.depth])).toEqual([
      ['o', 0],
      ['p', 0],
      ['c', 1]
    ]);
  });

  it('treats orphan child as root when parent missing from set', () => {
    const c = issue({ id: 'c', title: 'Child', parent_issue_id: 'missing' });
    const rows = nestIssuesDepth1([c]);
    expect(rows).toEqual([{ issue: c, depth: 0 }]);
  });
});
