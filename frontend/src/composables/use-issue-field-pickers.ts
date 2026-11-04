import { ref } from 'vue';

export type IssueFieldPickerKind = 'status' | 'assignee' | 'priority' | null;

const activePicker = ref<IssueFieldPickerKind>(null);

/** Test-only reset. */
export function resetIssueFieldPickersForTests() {
  activePicker.value = null;
}

/** Which field picker modal is open for the focused issue (A/S/P). */
export function useIssueFieldPickers() {
  function openPicker(kind: Exclude<IssueFieldPickerKind, null>) {
    activePicker.value = kind;
  }

  function closePicker() {
    activePicker.value = null;
  }

  function openStatus() {
    openPicker('status');
  }

  function openAssignee() {
    openPicker('assignee');
  }

  function openPriority() {
    openPicker('priority');
  }

  return {
    activePicker,
    openPicker,
    closePicker,
    openStatus,
    openAssignee,
    openPriority
  };
}
