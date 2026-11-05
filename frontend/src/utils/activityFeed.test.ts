import { describe, expect, it } from 'vitest';
import {
  ACTIVITY_ACTION_OPTIONS,
  buildActivityQuery,
  emptyActivityDescription,
  formatActivityActor,
  formatActivityRow,
  formatUnreadBadge,
  toggleReactionSummary
} from './activityFeed';

describe('activityFeed', () => {
  it('serializes since presets and actionTypes', () => {
    const now = new Date('2026-11-05T10:00:00.000Z');
    const q = buildActivityQuery({
      sincePreset: '24h',
      actionTypes: ['status_changed', 'assigned'],
      limit: 50,
      now
    });
    expect(q.since).toBe('2026-11-04T10:00:00.000Z');
    expect(q.actionType).toEqual(['status_changed', 'assigned']);
    expect(q.limit).toBe('50');
  });

  it('serializes 7d and cursor', () => {
    const now = new Date('2026-11-05T10:00:00.000Z');
    const q = buildActivityQuery({ sincePreset: '7d', cursor: 'abc', now });
    expect(q.since).toBe('2026-10-29T10:00:00.000Z');
    expect(q.cursor).toBe('abc');
  });

  it('serializes watching=true (E52)', () => {
    const q = buildActivityQuery({ watching: true, limit: 20 });
    expect(q.watching).toBe('true');
    expect(q.limit).toBe('20');
    const q2 = buildActivityQuery({ watching: false });
    expect(q2.watching).toBeUndefined();
  });

  it('formats empty-ish row via timeline map', () => {
    expect(
      formatActivityRow({
        id: '1',
        issueId: 'i1',
        actionType: 'status_changed',
        payload: { from: 'open', to: 'closed' }
      })
    ).toContain('状态');
  });

  it('formats actor fallback', () => {
    expect(formatActivityActor({ id: '1', issueId: 'i', actionType: 'created' })).toBe('系统');
    expect(
      formatActivityActor({
        id: '1',
        issueId: 'i',
        actionType: 'created',
        actor: { id: 'u1', displayName: 'Way' }
      })
    ).toBe('Way');
  });

  it('exposes action options', () => {
    expect(ACTIVITY_ACTION_OPTIONS.length).toBeGreaterThan(5);
    expect(ACTIVITY_ACTION_OPTIONS.some(o => o.value === 'status_changed')).toBe(true);
  });

  it('empty copy distinguishes watching', () => {
    expect(emptyActivityDescription(false)).toBe('暂无活动');
    expect(emptyActivityDescription(true)).toContain('关注');
  });

  it('formats unread badge with 99+', () => {
    expect(formatUnreadBadge(0)).toBe('');
    expect(formatUnreadBadge(3)).toBe('3');
    expect(formatUnreadBadge(99)).toBe('99');
    expect(formatUnreadBadge(100)).toBe('99+');
    expect(formatUnreadBadge(50, true)).toBe('99+');
  });

  it('toggles reaction summary optimistically', () => {
    const next = toggleReactionSummary({ scope: 'issue', summary: [] }, '👍', true);
    expect(next.summary[0]).toEqual({ emoji: '👍', count: 1, myReacted: true });
    const off = toggleReactionSummary(next, '👍', false);
    expect(off.summary).toEqual([]);
  });
});
