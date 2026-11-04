import { describe, expect, it } from 'vitest';
import {
  getCustomFieldCondition,
  parseAutomationJson,
  summarizeAutomationRule,
  withCustomFieldCondition
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
});
