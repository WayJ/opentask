import { describe, expect, it } from 'vitest';
import {
  defaultIssueDisplay,
  displayStateToJson,
  interpolateScaleColor,
  normalizeIssueDisplay,
  resolveCellIcon,
  resolveRowBackground,
  resolveRowTint
} from './display-prefs';

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

describe('E49 colorScales + iconSets', () => {
  it('normalizes scales/icons and drops invalid', () => {
    const d = normalizeIssueDisplay({
      colorScales: [
        {
          id: 'cs1',
          field: 'cf:score',
          domain: { min: 0, max: 10 },
          palette: 'blue_red',
          target: 'row'
        },
        {
          id: 'bad',
          field: 'priority',
          domain: { min: 0, max: 1 },
          palette: 'blue_red',
          target: 'row'
        },
        {
          id: 'badp',
          field: 'cf:x',
          domain: { min: 0, max: 1 },
          palette: 'neon',
          target: 'row'
        }
      ],
      iconSets: [
        {
          id: 'is1',
          field: 'cf:risk',
          rules: [
            { op: 'gte', value: 8, icon: 'arrow_up' },
            { op: 'lt', value: 3, icon: 'url_http' }
          ]
        }
      ]
    });
    expect(d.colorScales).toHaveLength(1);
    expect(d.colorScales[0].palette).toBe('blue_red');
    expect(d.iconSets).toHaveLength(1);
    expect(d.iconSets[0].rules).toHaveLength(1);
    expect(d.iconSets[0].rules[0].icon).toBe('arrow_up');
    const json = displayStateToJson(d);
    expect(json.color_scales).toHaveLength(1);
    expect(json.icon_sets).toHaveLength(1);
  });

  it('interpolateScaleColor endpoints and midpoint', () => {
    expect(interpolateScaleColor('blue_red', 0).toLowerCase()).toBe('#2080f0');
    expect(interpolateScaleColor('blue_red', 1).toLowerCase()).toBe('#d03050');
    const mid = interpolateScaleColor('blue_red', 0.5).toLowerCase();
    expect(mid).toMatch(/^#[0-9a-f]{6}$/);
    expect(mid).not.toBe('#2080f0');
    expect(mid).not.toBe('#d03050');
  });

  it('resolveRowBackground prefers tint over scale', () => {
    const tintRules = [
      {
        id: 'a',
        when: { field: 'priority', op: 'eq' as const, value: 'high' },
        style: { rowTint: 'warning' as const },
        target: 'row' as const
      }
    ];
    const scales = [
      {
        id: 'cs1',
        field: 'estimate_points',
        domain: { min: 0, max: 10 },
        palette: 'blue_red' as const,
        target: 'row' as const
      }
    ];
    const hit = resolveRowBackground(
      { priority: 'high', estimate_points: 5 },
      { conditionalFormats: tintRules, colorScales: scales }
    );
    expect(hit).toEqual({ kind: 'tint', value: 'warning' });
    const scaleOnly = resolveRowBackground(
      { priority: 'low', estimate_points: 5 },
      { conditionalFormats: tintRules, colorScales: scales }
    );
    expect(scaleOnly?.kind).toBe('scale');
    expect(scaleOnly?.value).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it('resolveCellIcon first-match-wins', () => {
    const sets = [
      {
        id: 'is1',
        field: 'cf:risk',
        rules: [
          { op: 'gte' as const, value: 8, icon: 'arrow_up' as const },
          { op: 'gte' as const, value: 5, icon: 'arrow_flat' as const }
        ]
      }
    ];
    expect(
      resolveCellIcon({ customFields: [{ key: 'risk', value: 9 }] }, sets, 'cf:risk')
    ).toBe('arrow_up');
    expect(
      resolveCellIcon({ customFields: [{ key: 'risk', value: 6 }] }, sets, 'cf:risk')
    ).toBe('arrow_flat');
    expect(
      resolveCellIcon({ customFields: [{ key: 'risk', value: 1 }] }, sets, 'cf:risk')
    ).toBeNull();
  });
});
