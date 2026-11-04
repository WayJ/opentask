import { describe, expect, it } from 'vitest';
import { defaultIssueDisplay, displayStateToJson, normalizeIssueDisplay, resolveRowTint } from './display-prefs';

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
    expect(d.fields.estimate_points).toBe(true);
    expect(d.customFieldKeys).toEqual([]);
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

  it('persists custom_field_keys', () => {
    const d = normalizeIssueDisplay({
      custom_field_keys: ['Severity', ' shipped ', '']
    });
    expect(d.customFieldKeys).toEqual(['severity', 'shipped']);
    const json = displayStateToJson(d);
    expect(json.custom_field_keys).toEqual(['severity', 'shipped']);
    expect(normalizeIssueDisplay(json).customFieldKeys).toEqual(['severity', 'shipped']);
  });
});

describe('E37 cf: swimlane/groupBy normalize', () => {
  it('accepts cf:severity for swimlane and groupBy', () => {
    const d = normalizeIssueDisplay({
      swimlane_by: 'cf:severity',
      group_by: 'cf:area'
    });
    expect(d.swimlaneBy).toBe('cf:severity');
    expect(d.groupBy).toBe('cf:area');
  });

  it('rejects malformed cf: and falls back to none', () => {
    const d = normalizeIssueDisplay({
      swimlane_by: 'cf:BadKey',
      group_by: 'cf:'
    });
    expect(d.swimlaneBy).toBe('none');
    expect(d.groupBy).toBe('none');
  });
});

describe('E46 conditionalFormats', () => {
  it('normalizes rules and drops invalid', () => {
    const d = normalizeIssueDisplay({
      conditional_formats: [
        {
          id: 'c1',
          when: { field: 'cf:risk', op: 'gte', value: 8 },
          style: { rowTint: 'danger' },
          target: 'row'
        },
        {
          id: 'bad',
          when: { field: 'cf:x', op: 'nope', value: 1 },
          style: { rowTint: 'danger' },
          target: 'row'
        }
      ]
    });
    expect(d.conditionalFormats).toHaveLength(1);
    expect(d.conditionalFormats[0].style.rowTint).toBe('danger');
    expect(displayStateToJson(d).conditional_formats).toHaveLength(1);
  });

  it('resolveRowTint first-match-wins', () => {
    const rules = [
      {
        id: 'a',
        when: { field: 'priority', op: 'eq' as const, value: 'high' },
        style: { rowTint: 'warning' as const },
        target: 'row' as const
      },
      {
        id: 'b',
        when: { field: 'priority', op: 'eq' as const, value: 'high' },
        style: { rowTint: 'danger' as const },
        target: 'row' as const
      }
    ];
    expect(resolveRowTint({ priority: 'high' }, rules)).toBe('warning');
    expect(resolveRowTint({ priority: 'low' }, rules)).toBeNull();
  });
});
