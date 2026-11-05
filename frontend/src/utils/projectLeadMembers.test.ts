import { describe, expect, it } from 'vitest';
import { formatMemberCount, leadLabel, memberIds } from './projectLeadMembers';

describe('E79 projectLeadMembers helpers', () => {
  it('leadLabel prefers sso_name', () => {
    expect(leadLabel({ id: '1', sso_name: 'Wei', name: 'W' })).toBe('Wei');
    expect(leadLabel(null)).toBe('未设置负责人');
  });

  it('memberIds filters', () => {
    expect(memberIds([{ id: 'a' }, { id: 'b' }])).toEqual(['a', 'b']);
    expect(memberIds(null)).toEqual([]);
  });

  it('formatMemberCount', () => {
    expect(formatMemberCount(3)).toBe('3 名成员');
    expect(formatMemberCount(undefined)).toBe('0 名成员');
  });
});
