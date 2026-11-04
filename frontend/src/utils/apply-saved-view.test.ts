import { describe, expect, it } from 'vitest';
import type { SavedView } from '@/service/api/saved-views';
import { deriveListStateFromSavedView } from './apply-saved-view';

describe('deriveListStateFromSavedView', () => {
  it('maps filter/tab/display', () => {
    const view = {
      id: 'v1',
      name: 'Open bugs',
      filter: {
        type: 'bug',
        status: 'open',
        search: 'login',
        tab: 'open',
        priority: 'high',
        project_id: 'p1'
      },
      display: { view_mode: 'board', group_by: 'priority' }
    } as SavedView;
    const state = deriveListStateFromSavedView(view);
    expect(state.filters).toEqual({
      type: 'bug',
      status: 'open',
      search: 'login',
      priority: 'high',
      project_id: 'p1'
    });
    expect(state.tab).toBe('open');
    expect(state.viewMode).toBe('board');
    expect(state.groupBy).toBe('priority');
    expect(state.activeSavedViewId).toBe('v1');
  });

  it('infers tab from status when tab missing; defaults groupBy none', () => {
    const view = {
      id: 'v2',
      name: 'Closed',
      filter: { status: 'closed' },
      display: null
    } as SavedView;
    const state = deriveListStateFromSavedView(view);
    expect(state.tab).toBe('closed');
    expect(state.groupBy).toBe('none');
    expect(state.viewMode).toBeUndefined();
  });
});
