import { beforeEach, describe, expect, it } from 'vitest';
import { resetIssueFocusForTests, useIssueFocus } from './use-issue-focus';

describe('useIssueFocus', () => {
  beforeEach(() => {
    resetIssueFocusForTests();
  });

  it('setFocus and clearFocus', () => {
    const focus = useIssueFocus();
    expect(focus.focusedIssueId.value).toBeNull();
    focus.setFocus('iss-1', { title: 'Hello' });
    expect(focus.focusedIssueId.value).toBe('iss-1');
    expect(focus.focusedIssue.value?.title).toBe('Hello');
    focus.clearFocus();
    expect(focus.focusedIssueId.value).toBeNull();
    expect(focus.focusedIssue.value).toBeNull();
  });

  it('ensureDetailFocus sets id from route', () => {
    const focus = useIssueFocus();
    focus.ensureDetailFocus('detail-9');
    expect(focus.focusedIssueId.value).toBe('detail-9');
    focus.ensureDetailFocus('');
    expect(focus.focusedIssueId.value).toBeNull();
  });

  it('shares singleton state across calls', () => {
    const a = useIssueFocus();
    const b = useIssueFocus();
    a.setFocus('shared');
    expect(b.focusedIssueId.value).toBe('shared');
  });
});
