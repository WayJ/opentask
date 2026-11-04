import { describe, expect, it } from 'vitest';
import { defaultIssueDisplay, displayStateToJson, normalizeIssueDisplay } from './display-prefs';

describe('normalizeIssueDisplay', () => {
  it('returns defaults for null/invalid', () => {
    const d = normalizeIssueDisplay(null);
    expect(d.viewMode).toBe('list');
    expect(d.groupBy).toBe('none');
    expect(d.swimlaneBy).toBe('none');
    expect(d.hideEmptyLanes).toBe(false);
    expect(d.fields.assignee).toBe(true);
    expect(d.fields.priority).toBe(true);
    expect(d.fields.issue_code).toBe(true);
    expect(d.fields.estimate_points).toBe(false);
  });

  it('merges known keys and ignores unknown', () => {
    const d = normalizeIssueDisplay({
      view_mode: 'board',
      group_by: 'label',
      swimlane_by: 'assignee',
      hide_empty_lanes: true,
      fields: { priority: false, weird: true },
      unknown_top: 1
    });
    expect(d.viewMode).toBe('board');
    expect(d.groupBy).toBe('label');
    expect(d.swimlaneBy).toBe('assignee');
    expect(d.hideEmptyLanes).toBe(true);
    expect(d.fields.priority).toBe(false);
    expect(d.fields.assignee).toBe(true);
    expect((d.fields as any).weird).toBeUndefined();
  });

  it('roundtrips via displayStateToJson', () => {
    const base = defaultIssueDisplay();
    base.swimlaneBy = 'priority';
    base.hideEmptyLanes = true;
    base.fields.type = true;
    const json = displayStateToJson(base);
    expect(json.swimlane_by).toBe('priority');
    expect(json.hide_empty_lanes).toBe(true);
    expect((json.fields as any).type).toBe(true);
    const again = normalizeIssueDisplay(json);
    expect(again.swimlaneBy).toBe('priority');
    expect(again.fields.type).toBe(true);
  });
});
