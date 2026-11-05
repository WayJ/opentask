import { describe, expect, it } from 'vitest';
import {
  formatMilestoneIssueCount,
  milestoneDeleteConfirmText
} from './formatMilestoneIssueCount';

describe('formatMilestoneIssueCount', () => {
  it('formats non-negative integers', () => {
    expect(formatMilestoneIssueCount(0)).toBe('0');
    expect(formatMilestoneIssueCount(2)).toBe('2');
    expect(formatMilestoneIssueCount(2.9)).toBe('2');
  });

  it('treats nullish / invalid as 0', () => {
    expect(formatMilestoneIssueCount(undefined)).toBe('0');
    expect(formatMilestoneIssueCount(null)).toBe('0');
    expect(formatMilestoneIssueCount(Number.NaN)).toBe('0');
    expect(formatMilestoneIssueCount(-1)).toBe('0');
  });
});

describe('milestoneDeleteConfirmText', () => {
  it('mentions occupancy when count > 0', () => {
    expect(milestoneDeleteConfirmText(3)).toContain('3');
    expect(milestoneDeleteConfirmText(3)).toContain('Issue');
  });

  it('uses plain confirm when empty', () => {
    expect(milestoneDeleteConfirmText(0)).toBe('确定删除此里程碑吗?');
    expect(milestoneDeleteConfirmText(undefined)).toBe('确定删除此里程碑吗?');
  });
});
