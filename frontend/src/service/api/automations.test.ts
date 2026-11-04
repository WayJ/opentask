import { describe, expect, it } from 'vitest';
import {
  getCustomFieldCondition,
  getCustomFieldConditions,
  MAX_CUSTOM_FIELD_CONDITIONS,
  parseAutomationJson,
  summarizeAutomationRule,
  summarizeCfChangedTrigger,
  withCustomFieldCondition,
  withCustomFieldConditions
} from './automations';

describe('automations helpers', () => {
  it('parseAutomationJson empty → fallback/{}', () => {
    expect(parseAutomationJson('')).toEqual({});
    expect(parseAutomationJson('  ', { a: 1 })).toEqual({ a: 1 });
  });

  it('parseAutomationJson object', () => {
    expect(parseAutomationJson('{"to":"in_progress"}')).toEqual({ to: 'in_progress' });
  });

  it('parseAutomationJson rejects array', () => {
    expect(() => parseAutomationJson('[1]')).toThrow();
  });

  it('withCustomFieldCondition merges AND keeps others', () => {
    const next = withCustomFieldCondition(
      { priorityIs: 'high' },
      { key: 'tier', op: 'eq', value: 'enterprise' }
    );
    expect(next).toEqual({
      priorityIs: 'high',
      customField: { key: 'tier', op: 'eq', value: 'enterprise' }
    });
  });

  it('withCustomFieldCondition clears CF', () => {
    expect(withCustomFieldCondition({ customField: { key: 'a', op: 'eq', value: 1 } }, null)).toBeNull();
  });

  it('getCustomFieldCondition reads snake alias', () => {
    expect(getCustomFieldCondition({ custom_field: { key: 'note', op: 'is_set' } })).toEqual({
      key: 'note',
      fieldId: undefined,
      op: 'is_set',
      value: undefined
    });
  });

  it('summarizeAutomationRule for CF condition + action', () => {
    expect(
      summarizeAutomationRule({
        condition: { customField: { key: 'tier', op: 'eq', value: 'pro' } },
        actionType: 'set_custom_field',
        actionConfig: { key: 'source', value: 'bot' }
      })
    ).toBe('cf:tier eq "pro" · set cf:source="bot"');
  });

  it('getCustomFieldConditions prefers array; wraps single', () => {
    expect(
      getCustomFieldConditions({
        customFields: [
          { key: 'a', op: 'eq', value: 1 },
          { key: 'b', op: 'is_set' }
        ]
      })
    ).toEqual([
      { key: 'a', fieldId: undefined, op: 'eq', value: 1 },
      { key: 'b', fieldId: undefined, op: 'is_set', value: undefined }
    ]);
    expect(getCustomFieldConditions({ customField: { key: 'x', op: 'neq', value: 'y' } })).toEqual([
      { key: 'x', fieldId: undefined, op: 'neq', value: 'y' }
    ]);
  });

  it('withCustomFieldConditions enforces max 5', () => {
    const many = Array.from({ length: MAX_CUSTOM_FIELD_CONDITIONS + 1 }, (_, i) => ({
      key: `k${i}`,
      op: 'is_set' as const
    }));
    expect(() => withCustomFieldConditions({}, many)).toThrow(/最多/);
  });

  it('withCustomFieldConditions writes customFields', () => {
    expect(
      withCustomFieldConditions({ priorityIs: 'high' }, [
        { key: 'tier', op: 'eq', value: 'pro' },
        { key: 'region', op: 'eq', value: 'us' }
      ])
    ).toEqual({
      priorityIs: 'high',
      customFields: [
        { key: 'tier', op: 'eq', value: 'pro' },
        { key: 'region', op: 'eq', value: 'us' }
      ]
    });
  });

  it('summarizeCfChangedTrigger + rule with trigger', () => {
    expect(summarizeCfChangedTrigger({ field_key: 'tier', from: 'free', to: 'pro' })).toBe(
      'field:tier from="free" to="pro"'
    );
    expect(
      summarizeAutomationRule({
        triggerType: 'custom_field_changed',
        triggerConfig: { key: 'tier' },
        condition: null,
        actionType: 'set_priority',
        actionConfig: { priority: 'high' }
      })
    ).toBe('on field:tier');
  });
});
