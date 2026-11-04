import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  debounceFn,
  resetWorkspaceRealtimeForTests,
  __testBuildWsUrl
} from './use-workspace-realtime';

vi.mock('@/store/modules/auth/shared', () => ({
  getToken: vi.fn(() => 'tok')
}));

vi.mock('@/utils/storage', () => ({
  localStg: {
    get: vi.fn((k: string) => (k === 'workspaceId' ? 'ws-1' : null)),
    set: vi.fn(),
    remove: vi.fn()
  }
}));

describe('useWorkspaceRealtime helpers', () => {
  beforeEach(() => {
    resetWorkspaceRealtimeForTests();
  });

  it('buildWsUrl uses ws protocol and query', () => {
    const url = __testBuildWsUrl('ws-1', 'abc');
    expect(url).toContain('/ws/workspace?');
    expect(url).toContain('token=abc');
    expect(url).toContain('workspace_id=ws-1');
    expect(url.startsWith('ws')).toBe(true);
  });

  it('debounceFn delays calls', async () => {
    vi.useFakeTimers();
    const fn = vi.fn();
    const d = debounceFn(fn, 400);
    d();
    d();
    d();
    expect(fn).not.toHaveBeenCalled();
    vi.advanceTimersByTime(400);
    expect(fn).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });
});
