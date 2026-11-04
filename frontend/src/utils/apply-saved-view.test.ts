import { describe, expect, it } from 'vitest';
import type { SavedView } from '@/service/api/saved-views';
import { deriveListStateFromSavedView } from './apply-saved-view';

describe('deriveListStateFromSavedView', () => {
  it('maps filter/tab/display including swimlane and fields', () => {
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
      display: {
        view_mode: 'board',
        group_by: 'priority',
        swimlane_by: 'assignee',
        hide_empty_lanes: true,
        fields: { priority: false, assignee: true }
      }
    } as SavedView;
    const state = deriveListStateFromSavedView(view);
    expect(state.filters).toEqual({
      type: 'bug',
      status: 'open',
      search: 'login',
      priority: 'high',
      project_id: 'p1',
      cycle_id: undefined
    });
    expect(state.tab).toBe('open');
    expect(state.viewMode).toBe('board');
    expect(state.groupBy).toBe('priority');
    expect(state.swimlaneBy).toBe('assignee');
    expect(state.hideEmptyLanes).toBe(true);
    expect(state.fields.priority).toBe(false);
    expect(state.fields.assignee).toBe(true);
    expect(state.fields.issue_code).toBe(true);
    expect(state.activeSavedViewId).toBe('v1');
  });

  it('infers tab from status when tab missing; defaults groupBy/swimlane none', () => {
    const view = {
      id: 'v2',
      name: 'Closed',
      filter: { status: 'closed' },
      display: null
    } as SavedView;
    const state = deriveListStateFromSavedView(view);
    expect(state.tab).toBe('closed');
    expect(state.groupBy).toBe('none');
    expect(state.swimlaneBy).toBe('none');
    expect(state.hideEmptyLanes).toBe(false);
    expect(state.viewMode).toBeUndefined();
  });
});
