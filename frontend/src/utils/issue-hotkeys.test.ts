import { describe, expect, it } from 'vitest';
import { isModB, resolveIssueHotkeyAction, toggleListBoardMode } from './issue-hotkeys';

describe('isModB', () => {
  it('matches Meta+B and Ctrl+B', () => {
    expect(isModB({ key: 'b', metaKey: true, ctrlKey: false })).toBe(true);
    expect(isModB({ key: 'B', metaKey: false, ctrlKey: true })).toBe(true);
  });

  it('rejects bare B and other mod keys', () => {
    expect(isModB({ key: 'b', metaKey: false, ctrlKey: false })).toBe(false);
    expect(isModB({ key: 'k', metaKey: true, ctrlKey: false })).toBe(false);
  });
});

describe('toggleListBoardMode', () => {
  it('flips list ↔ board', () => {
    expect(toggleListBoardMode('list')).toBe('board');
    expect(toggleListBoardMode('board')).toBe('list');
  });
});

describe('resolveIssueHotkeyAction', () => {
  const base = {
    key: 'c',
    metaKey: false,
    ctrlKey: false,
    paletteOpen: false,
    editable: false,
    hasFocusedIssue: true,
    onIssueListRoute: true
  };

  it('returns create for C when palette closed and not editable', () => {
    expect(resolveIssueHotkeyAction({ ...base, key: 'c' })).toEqual({ type: 'create' });
    expect(resolveIssueHotkeyAction({ ...base, key: 'C' })).toEqual({ type: 'create' });
  });

  it('maps S/A/P/I when focused', () => {
    expect(resolveIssueHotkeyAction({ ...base, key: 's' })).toEqual({ type: 'status' });
    expect(resolveIssueHotkeyAction({ ...base, key: 'a' })).toEqual({ type: 'assignee' });
    expect(resolveIssueHotkeyAction({ ...base, key: 'p' })).toEqual({ type: 'priority' });
    expect(resolveIssueHotkeyAction({ ...base, key: 'i' })).toEqual({ type: 'assign_me' });
  });

  it('returns null for A/S/P/I without focus', () => {
    expect(resolveIssueHotkeyAction({ ...base, key: 's', hasFocusedIssue: false })).toBeNull();
    expect(resolveIssueHotkeyAction({ ...base, key: 'a', hasFocusedIssue: false })).toBeNull();
  });

  it('ignores single letters when editable or palette open', () => {
    expect(resolveIssueHotkeyAction({ ...base, key: 'c', editable: true })).toBeNull();
    expect(resolveIssueHotkeyAction({ ...base, key: 'c', paletteOpen: true })).toBeNull();
    expect(resolveIssueHotkeyAction({ ...base, key: 's', editable: true })).toBeNull();
  });

  it('returns toggle_view for Mod+B on issue list even when editable', () => {
    expect(
      resolveIssueHotkeyAction({
        ...base,
        key: 'b',
        metaKey: true,
        editable: true,
        onIssueListRoute: true
      })
    ).toEqual({ type: 'toggle_view' });
  });

  it('returns null for Mod+B off issue list', () => {
    expect(
      resolveIssueHotkeyAction({
        ...base,
        key: 'b',
        metaKey: true,
        onIssueListRoute: false
      })
    ).toBeNull();
  });
});
