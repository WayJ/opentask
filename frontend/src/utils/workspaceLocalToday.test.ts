import { describe, expect, it } from 'vitest';
import { localTodayIso, resolveWorkspaceTzClient } from './workspaceLocalToday';

describe('workspaceLocalToday', () => {
  it('empty/invalid → UTC', () => {
    expect(resolveWorkspaceTzClient(null)).toBe('UTC');
    expect(resolveWorkspaceTzClient('')).toBe('UTC');
    expect(resolveWorkspaceTzClient('Not/A_Zone')).toBe('UTC');
  });

  it('accepts Asia/Shanghai', () => {
    expect(resolveWorkspaceTzClient('Asia/Shanghai')).toBe('Asia/Shanghai');
  });

  it('Shanghai crosses UTC day', () => {
    const now = new Date(Date.UTC(2026, 10, 5, 16, 30, 0)); // Nov 5 16:30 UTC
    expect(localTodayIso('Asia/Shanghai', now)).toBe('2026-11-06');
    expect(localTodayIso(null, now)).toBe('2026-11-05');
    expect(localTodayIso('UTC', now)).toBe('2026-11-05');
  });
});
