import { describe, expect, it } from 'vitest';
import type { Api } from '@/typings/api';
import { groupIssuesBy, isGroupByKey } from './groupIssuesBy';

function makeIssue(partial: Partial<Api.Issue.Issue> & Pick<Api.Issue.Issue, 'id' | 'title'>): Api.Issue.Issue {
  return {
    issue_code: partial.issue_code || `ISS-${partial.id}`,
    type: (partial.type as Api.Issue.IssueType) || ('bug' as Api.Issue.IssueType),
    status: (partial.status as Api.Issue.IssueStatus) || ('open' as Api.Issue.IssueStatus),
    priority: (partial.priority as Api.Issue.IssuePriority) || ('medium' as Api.Issue.IssuePriority),
    reporter_id: partial.reporter_id || 'r1',
    view_count: 0,
    comment_count: 0,
    attachment_count: 0,
    is_deleted: false,
    created_at: '2026-11-04T00:00:00Z',
    updated_at: '2026-11-04T00:00:00Z',
    ...partial
  } as Api.Issue.Issue;
}

describe('groupIssuesBy', () => {
  const issues = [
    makeIssue({
      id: '1',
      title: 'A',
      priority: 'high' as Api.Issue.IssuePriority,
      status: 'open' as Api.Issue.IssueStatus,
      type: 'bug' as Api.Issue.IssueType,
      assignee_id: 'u1',
      assignee: { id: 'u1', name: 'Alice' }
    }),
    makeIssue({
      id: '2',
      title: 'B',
      priority: 'high' as Api.Issue.IssuePriority,
      status: 'in_progress' as Api.Issue.IssueStatus,
      type: 'feature' as Api.Issue.IssueType
    }),
    makeIssue({
      id: '3',
      title: 'C',
      priority: 'low' as Api.Issue.IssuePriority,
      status: 'open' as Api.Issue.IssueStatus,
      type: 'bug' as Api.Issue.IssueType,
      assignee_id: 'u2',
      assignee: { id: 'u2', name: 'Bob' }
    })
  ];

  it('returns empty buckets for none', () => {
    expect(groupIssuesBy(issues, 'none')).toEqual([]);
  });

  it('returns empty for empty input', () => {
    expect(groupIssuesBy([], 'priority')).toEqual([]);
  });

  it('groups by priority with labels and stable order', () => {
    const buckets = groupIssuesBy(issues, 'priority');
    expect(buckets.map(b => b.key)).toEqual(['low', 'high']);
    expect(buckets.find(b => b.key === 'high')?.issues).toHaveLength(2);
    expect(buckets.find(b => b.key === 'low')?.label).toBe('低');
    expect(buckets.find(b => b.key === 'high')?.label).toBe('高');
  });

  it('groups by assignee with 未分配 bucket first', () => {
    const buckets = groupIssuesBy(issues, 'assignee');
    expect(buckets[0]?.key).toBe('__unassigned__');
    expect(buckets[0]?.label).toBe('未分配');
    expect(buckets[0]?.issues.map(i => i.id)).toEqual(['2']);
    const alice = buckets.find(b => b.key === 'u1');
    expect(alice?.label).toBe('Alice');
    expect(alice?.issues).toHaveLength(1);
  });

  it('groups by type', () => {
    const buckets = groupIssuesBy(issues, 'type');
    expect(buckets.find(b => b.key === 'bug')?.issues).toHaveLength(2);
    expect(buckets.find(b => b.key === 'feature')?.label).toBe('功能');
  });

  it('groups by status', () => {
    const buckets = groupIssuesBy(issues, 'status');
    expect(buckets.find(b => b.key === 'open')?.issues).toHaveLength(2);
    expect(buckets.find(b => b.key === 'in_progress')?.label).toBe('进行中');
  });

  it('groups by label with multi-expand and __unlabelled__', () => {
    const labelled = [
      makeIssue({
        id: '1',
        title: 'A',
        tags: [
          { id: 1, name: 'bug', color: '#f00' },
          { id: 2, name: 'urgent', color: '#0f0' }
        ]
      } as any),
      makeIssue({
        id: '2',
        title: 'B',
        tags: [{ id: 1, name: 'bug', color: '#f00' }]
      } as any),
      makeIssue({ id: '3', title: 'C' })
    ];
    const buckets = groupIssuesBy(labelled, 'label');
    expect(buckets[0]?.key).toBe('__unlabelled__');
    expect(buckets[0]?.issues.map(i => i.id)).toEqual(['3']);
    const bug = buckets.find(b => b.key === '1');
    expect(bug?.label).toBe('bug');
    expect(bug?.issues.map(i => i.id).sort()).toEqual(['1', '2']);
    const urgent = buckets.find(b => b.key === '2');
    expect(urgent?.issues.map(i => i.id)).toEqual(['1']);
  });

  it('isGroupByKey validates', () => {
    expect(isGroupByKey('priority')).toBe(true);
    expect(isGroupByKey('label')).toBe(true);
    expect(isGroupByKey('foo')).toBe(false);
  });
});
