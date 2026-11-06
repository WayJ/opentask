import { describe, expect, it } from 'vitest';
import { LEGACY_DEFAULT_WORKSPACE_ID, resolveWorkspaceSelection, workspaceRequestHeader } from '../workspace-selection';

describe('resolveWorkspaceSelection', () => {
  const own = { id: 'ws-own' };
  const other = { id: 'ws-other' };

  it('keeps a stored id that is in the usable list', () => {
    expect(resolveWorkspaceSelection('ws-other', [own, other])).toEqual({
      gate: 'ready',
      workspaceId: 'ws-other'
    });
  });

  it('replaces a foreign or stale id with the earliest usable workspace', () => {
    expect(resolveWorkspaceSelection('foreign', [own, other])).toEqual({
      gate: 'ready',
      workspaceId: 'ws-own'
    });
  });

  it('does not keep the legacy default workspace', () => {
    expect(resolveWorkspaceSelection(LEGACY_DEFAULT_WORKSPACE_ID, [{ id: LEGACY_DEFAULT_WORKSPACE_ID }])).toEqual({
      gate: 'onboarding',
      workspaceId: null
    });
  });

  it('asks for onboarding when the usable list is empty', () => {
    expect(resolveWorkspaceSelection('ws-own', [])).toEqual({ gate: 'onboarding', workspaceId: null });
  });
});

describe('workspaceRequestHeader', () => {
  it('omits the header when no workspace is selected', () => {
    expect(workspaceRequestHeader(null)).toEqual({});
    expect(workspaceRequestHeader('')).toEqual({});
    expect(workspaceRequestHeader(undefined)).toEqual({});
  });

  it('sends only the resolved id', () => {
    expect(workspaceRequestHeader('ws-own')).toEqual({ 'X-Workspace-Id': 'ws-own' });
  });
});
