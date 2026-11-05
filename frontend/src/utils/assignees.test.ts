import { describe, expect, it } from 'vitest';
import {
  assigneeLabel,
  formatAssigneesStack,
  primaryAssigneeId
} from './assignees';

describe('E71 assignees helpers', () => {
  it('formatAssigneesStack empty', () => {
    expect(formatAssigneesStack([])).toEqual({
      visible: [],
      overflow: 0,
      primaryId: null
    });
    expect(formatAssigneesStack(null).primaryId).toBeNull();
  });

  it('formatAssigneesStack overflow', () => {
    const list = [
      { id: 'a', name: 'A' },
      { id: 'b', name: 'B' },
      { id: 'c', name: 'C' },
      { id: 'd', name: 'D' }
    ];
    const out = formatAssigneesStack(list, 3);
    expect(out.visible.map(x => x.id)).toEqual(['a', 'b', 'c']);
    expect(out.overflow).toBe(1);
    expect(out.primaryId).toBe('a');
  });

  it('primaryAssigneeId falls back', () => {
    expect(primaryAssigneeId([], 'x')).toBe('x');
    expect(primaryAssigneeId([{ id: 'a' }], 'x')).toBe('a');
  });

  it('assigneeLabel prefers sso_name', () => {
    expect(assigneeLabel({ id: '1', sso_name: 'Wei', name: 'W' })).toBe('Wei');
    expect(assigneeLabel(null)).toBe('未分配');
  });
});
