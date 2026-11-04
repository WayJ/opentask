import { beforeEach, describe, expect, it } from 'vitest';
import { resetIssueSelectionForTests, useIssueSelection } from './use-issue-selection';

describe('useIssueSelection', () => {
  beforeEach(() => {
    resetIssueSelectionForTests();
  });

  it('toggle adds and removes', () => {
    const sel = useIssueSelection();
    sel.toggle('a');
    expect(sel.selectedIds.value).toEqual(['a']);
    expect(sel.hasSelection.value).toBe(true);
    sel.toggle('a');
    expect(sel.selectedIds.value).toEqual([]);
    expect(sel.hasSelection.value).toBe(false);
  });

  it('selectRange inclusive from anchor', () => {
    const sel = useIssueSelection();
    const order = ['a', 'b', 'c', 'd'];
    sel.toggle('b');
    sel.selectRange('d', order);
    expect(sel.selectedIds.value).toEqual(['b', 'c', 'd']);
  });

  it('clear empties selection', () => {
    const sel = useIssueSelection();
    sel.setMany(['x', 'y']);
    sel.clear();
    expect(sel.count.value).toBe(0);
    expect(sel.anchorId.value).toBeNull();
  });

  it('shares singleton state', () => {
    const a = useIssueSelection();
    const b = useIssueSelection();
    a.toggle('shared');
    expect(b.isSelected('shared')).toBe(true);
  });
});
