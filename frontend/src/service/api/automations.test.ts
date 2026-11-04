import { describe, expect, it } from 'vitest';
import { parseAutomationJson } from './automations';

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
});
