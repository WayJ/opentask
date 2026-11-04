import { describe, expect, it } from 'vitest';
import { formatCustomFieldValue, formatFormulaDisplay } from './custom-fields';
import { isGroupingCfType } from '@/utils/groupIssuesBy';

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

  it('formatFormulaDisplay shows dash on error', () => {
    expect(formatFormulaDisplay({ value: 12, error: 'div_zero' })).toBe('—');
    expect(formatFormulaDisplay({ value: 12, formulaResultType: 'number' })).toBe('12');
  });

  it('formula type is not grouping/swimlane eligible', () => {
    expect(isGroupingCfType('formula')).toBe(false);
    expect(isGroupingCfType('single_select')).toBe(true);
  });
});
