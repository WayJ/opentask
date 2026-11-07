import { describe, expect, it } from 'vitest';
import { ISSUE_CODE_COLUMN_WIDTH, issueListColumnLayout } from './column-layout';

describe('issueListColumnLayout', () => {
  it('fits the whole title beside the code column on a phone table', () => {
    const layout = issueListColumnLayout(349);
    expect(layout.pinActions).toBe(false);
    expect(layout.titleWidth).toBeGreaterThanOrEqual(160);
    expect(ISSUE_CODE_COLUMN_WIDTH + layout.titleWidth).toBeLessThanOrEqual(349);
  });

  it('fits a 300px title on a tablet table without pinning actions', () => {
    const layout = issueListColumnLayout(522);
    expect(layout.pinActions).toBe(false);
    expect(layout.titleWidth).toBe(300);
    expect(ISSUE_CODE_COLUMN_WIDTH + layout.titleWidth).toBeLessThanOrEqual(522);
  });

  it('keeps the pinned action column on a desktop table', () => {
    const layout = issueListColumnLayout(1034);
    expect(layout.pinActions).toBe(true);
    expect(layout.titleWidth).toBe(300);
  });
});
