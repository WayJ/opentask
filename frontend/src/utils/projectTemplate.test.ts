import { describe, expect, it } from 'vitest';
import {
  MAX_PROJECT_TEMPLATE_MILESTONES,
  addDaysIso,
  previewMilestones,
  validateMilestonePayload
} from './projectTemplate';

describe('E72 projectTemplate helpers', () => {
  it('addDaysIso null offset', () => {
    expect(addDaysIso('2026-01-01', null)).toBeNull();
    expect(addDaysIso('2026-01-01', undefined)).toBeNull();
  });

  it('addDaysIso adds days in UTC', () => {
    expect(addDaysIso('2026-01-01', 0)).toBe('2026-01-01');
    expect(addDaysIso('2026-01-01', 30)).toBe('2026-01-31');
  });

  it('validateMilestonePayload max 30', () => {
    expect(validateMilestonePayload([])).toBeNull();
    expect(validateMilestonePayload([{ name: 'A' }])).toBeNull();
    expect(validateMilestonePayload([{ name: '  ' }])).toBe('milestone name required');
    const many = Array.from({ length: 31 }, (_, i) => ({ name: `M${i}` }));
    expect(validateMilestonePayload(many)).toBe(`max ${MAX_PROJECT_TEMPLATE_MILESTONES} milestones`);
  });

  it('previewMilestones', () => {
    const out = previewMilestones(
      [
        { name: 'Kickoff', targetOffsetDays: 0 },
        { name: 'Beta', targetOffsetDays: 30 }
      ],
      '2026-03-01'
    );
    expect(out).toEqual([
      { name: 'Kickoff', targetDate: '2026-03-01' },
      { name: 'Beta', targetDate: '2026-03-31' }
    ]);
  });

  it('max constant', () => {
    expect(MAX_PROJECT_TEMPLATE_MILESTONES).toBe(30);
  });
});
