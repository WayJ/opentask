import { describe, expect, it } from 'vitest';
import { formatCustomFieldValue } from './custom-fields';

describe('custom-fields helpers', () => {
  it('formatCustomFieldValue handles empty and boolean', () => {
    expect(formatCustomFieldValue('text', null)).toBe('—');
    expect(formatCustomFieldValue('boolean', true)).toBe('是');
    expect(formatCustomFieldValue('boolean', false)).toBe('否');
  });

  it('formatCustomFieldValue joins multi_select', () => {
    expect(formatCustomFieldValue('multi_select', ['a', 'b'])).toBe('a, b');
    expect(formatCustomFieldValue('number', 3)).toBe('3');
  });
});
