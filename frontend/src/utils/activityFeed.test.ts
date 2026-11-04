import { describe, expect, it } from 'vitest';
import {
  ACTIVITY_ACTION_OPTIONS,
  buildActivityQuery,
  formatActivityActor,
  formatActivityRow
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
});
