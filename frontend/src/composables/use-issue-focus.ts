import { computed, ref } from 'vue';

export interface FocusedIssueSummary {
  id?: string;
  title?: string;
  status?: string;
  priority?: string;
  assigneeId?: string | null;
}

const focusedIssueId = ref<string | null>(null);
const focusedIssue = ref<FocusedIssueSummary | null>(null);

/** Test-only reset of module singleton state. */
export function resetIssueFocusForTests() {
  focusedIssueId.value = null;
  focusedIssue.value = null;
}

/** Shared issue focus for list/board/detail + A/S/P/I hotkeys. */
export function useIssueFocus() {
  function setFocus(id: string, summary?: Omit<FocusedIssueSummary, 'id'>) {
    focusedIssueId.value = id;
    focusedIssue.value = { id, ...(summary || {}) };
  }

  function clearFocus() {
    focusedIssueId.value = null;
    focusedIssue.value = null;
  }

  function ensureDetailFocus(id: string | null | undefined) {
    const next = (id || '').trim();
    if (!next) {
      clearFocus();
      return;
    }
    if (focusedIssueId.value === next) return;
    setFocus(next);
  }

  const hasFocus = computed(() => Boolean(focusedIssueId.value));

  return {
    focusedIssueId,
    focusedIssue,
    hasFocus,
    setFocus,
    clearFocus,
    ensureDetailFocus
  };
}
