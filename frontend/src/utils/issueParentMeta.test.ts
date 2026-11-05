import { describe, expect, it } from 'vitest';
import {
  canPromoteToRoot,
  excludeSelfFromPicker,
  setParentSuccessMessage
} from './issueParentMeta';

describe('issueParentMeta', () => {
  it('excludes self from picker rows', () => {
    const rows = [
      { id: 'a', title: 'A' },
      { id: 'b', title: 'B' },
      { id: 'c', title: 'C' }
    ];
    expect(excludeSelfFromPicker(rows, 'b').map(r => r.id)).toEqual(['a', 'c']);
    expect(excludeSelfFromPicker(rows, '').map(r => r.id)).toEqual(['a', 'b', 'c']);
  });

  it('canPromoteToRoot only when has parent', () => {
    expect(canPromoteToRoot('p1')).toBe(true);
    expect(canPromoteToRoot(null)).toBe(false);
    expect(canPromoteToRoot(undefined)).toBe(false);
    expect(canPromoteToRoot('')).toBe(false);
  });

  it('success messages', () => {
    expect(setParentSuccessMessage(null)).toBe('已提升为根');
    expect(setParentSuccessMessage('')).toBe('已提升为根');
    expect(setParentSuccessMessage('WAY-12')).toBe('已设为 WAY-12 的子项');
  });
});
