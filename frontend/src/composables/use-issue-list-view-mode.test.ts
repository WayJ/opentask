import { beforeEach, describe, expect, it } from 'vitest';
import { resetIssueListViewModeForTests, useIssueListViewMode } from './use-issue-list-view-mode';

describe('useIssueListViewMode', () => {
  beforeEach(() => {
    resetIssueListViewModeForTests();
  });

  it('defaults to list and toggles', () => {
    const vm = useIssueListViewMode();
    expect(vm.viewMode.value).toBe('list');
    vm.toggle();
    expect(vm.viewMode.value).toBe('board');
    vm.toggle();
    expect(vm.viewMode.value).toBe('list');
  });

  it('setMode writes explicitly', () => {
    const vm = useIssueListViewMode();
    vm.setMode('board');
    expect(vm.viewMode.value).toBe('board');
  });
});
