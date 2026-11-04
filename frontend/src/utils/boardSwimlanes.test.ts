import { describe, expect, it } from 'vitest';
import type { Api } from '@/typings/api';
import { buildBoardSwimlanes } from './boardSwimlanes';

function issue(partial: Partial<Api.Issue.Issue> & { id: string; title: string }): Api.Issue.Issue {
  return {
    status: 'open',
    priority: 'medium',
    type: 'task',
    issue_code: partial.id,
    ...partial
  } as Api.Issue.Issue;
}

describe('buildBoardSwimlanes', () => {
  const issues = [
    issue({ id: '1', title: 'A', status: 'open', assignee_id: 'u1', assignee: { name: 'Ann' } as any }),
    issue({ id: '2', title: 'B', status: 'in_progress', assignee_id: 'u1', assignee: { name: 'Ann' } as any }),
    issue({ id: '3', title: 'C', status: 'open', assignee_id: null as any }),
    issue({
      id: '4',
      title: 'D',
      status: 'open',
      priority: 'high',
      assignee_id: 'u2',
      assignee: { name: 'Bob' } as any
    })
  ];

  it('none yields single lane with status columns', () => {
    const lanes = buildBoardSwimlanes(issues, 'none', false);
    expect(lanes).toHaveLength(1);
    expect(lanes[0].key).toBe('__all__');
    expect(lanes[0].columns.open.map(i => i.id).sort()).toEqual(['1', '3', '4']);
    expect(lanes[0].columns.in_progress.map(i => i.id)).toEqual(['2']);
  });

  it('assignee swimlanes split rows; hideEmpty drops empty', () => {
    const lanes = buildBoardSwimlanes(issues, 'assignee', false);
    const keys = lanes.map(l => l.key);
    expect(keys).toContain('u1');
    expect(keys).toContain('u2');
    expect(keys).toContain('__unassigned__');
    const u1 = lanes.find(l => l.key === 'u1')!;
    expect(u1.columns.open.map(i => i.id)).toEqual(['1']);
    expect(u1.columns.in_progress.map(i => i.id)).toEqual(['2']);
  });

  it('hide_empty_lanes removes lanes with no cards', () => {
    const onlyU1 = issues.filter(i => i.assignee_id === 'u1');
    const lanes = buildBoardSwimlanes(onlyU1, 'assignee', true);
    expect(lanes.map(l => l.key)).toEqual(['u1']);
  });

  it('priority swimlane', () => {
    const lanes = buildBoardSwimlanes(issues, 'priority', false);
    expect(lanes.some(l => l.key === 'high')).toBe(true);
    expect(lanes.some(l => l.key === 'medium')).toBe(true);
  });
});
