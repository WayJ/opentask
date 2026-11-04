import { ref } from 'vue';
import { type ListBoardMode, toggleListBoardMode } from '@/utils/issue-hotkeys';

const viewMode = ref<ListBoardMode>('list');

/** Test-only reset. */
export function resetIssueListViewModeForTests() {
  viewMode.value = 'list';
}

/**
 * Shared list↔board mode for Issue list page UI buttons and ⌘B hotkey.
 */
export function useIssueListViewMode() {
  function setMode(mode: ListBoardMode) {
    viewMode.value = mode;
  }

  function toggle() {
    viewMode.value = toggleListBoardMode(viewMode.value);
  }

  return {
    viewMode,
    setMode,
    toggle
  };
}
