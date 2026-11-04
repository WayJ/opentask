/** Meta+B / Ctrl+B (case-insensitive). */
export function isModB(event: { key: string; metaKey: boolean; ctrlKey: boolean }): boolean {
  return (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'b';
}

export type ListBoardMode = 'list' | 'board';

export function toggleListBoardMode(mode: ListBoardMode): ListBoardMode {
  return mode === 'list' ? 'board' : 'list';
}

export type IssueHotkeyAction =
  | { type: 'create' }
  | { type: 'status' }
  | { type: 'assignee' }
  | { type: 'priority' }
  | { type: 'assign_me' }
  | { type: 'labels' }
  | { type: 'toggle_view' }
  | { type: 'toggle_select' }
  | { type: 'range_select' }
  | { type: 'clear_selection' };

export interface ResolveIssueHotkeyInput {
  key: string;
  metaKey: boolean;
  ctrlKey: boolean;
  altKey?: boolean;
  shiftKey?: boolean;
  paletteOpen: boolean;
  editable: boolean;
  hasFocusedIssue: boolean;
  onIssueListRoute: boolean;
  hasSelection?: boolean;
}

/**
 * Pure hotkey router for E5-S3 single-letter + ⌘B.
 * ⌘K is handled separately by useAppHotkeys.
 */
export function resolveIssueHotkeyAction(input: ResolveIssueHotkeyInput): IssueHotkeyAction | null {
  if (isModB(input)) {
    return input.onIssueListRoute ? { type: 'toggle_view' } : null;
  }

  // Modifier chords other than handled ones: ignore single-letter path
  if (input.metaKey || input.ctrlKey || input.altKey) {
    return null;
  }

  // Esc clears multi-select when present (E20); editable still allows Esc clear outside inputs? no — ignore in inputs
  if (input.key === 'Escape') {
    if (input.editable) return null;
    if (input.hasSelection) return { type: 'clear_selection' };
    return null;
  }

  if (input.paletteOpen || input.editable) {
    return null;
  }

  const key = input.key.toLowerCase();
  if (key === 'c') return { type: 'create' };

  // X / Shift+X multi-select on list/board
  if (key === 'x' && input.onIssueListRoute && input.hasFocusedIssue) {
    return input.shiftKey ? { type: 'range_select' } : { type: 'toggle_select' };
  }

  if (!input.hasFocusedIssue) return null;

  if (key === 's') return { type: 'status' };
  if (key === 'a') return { type: 'assignee' };
  if (key === 'p') return { type: 'priority' };
  if (key === 'i') return { type: 'assign_me' };
  if (key === 'l') return { type: 'labels' };

  return null;
}
