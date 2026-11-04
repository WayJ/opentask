/** Detect Meta+K / Ctrl+K (case-insensitive key). */
export function isModK(event: { key: string; metaKey: boolean; ctrlKey: boolean }): boolean {
  return (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k';
}

const EDITABLE_SELECTOR = 'input, textarea, select, [contenteditable="true"], .n-input, .n-base-selection-input';

/**
 * True when the event target is (or is inside) an editable control.
 * Used by S3 single-letter hotkeys; S1 exports for tests and ⌘K policy docs.
 */
export function ignoreWhenEditable(target: EventTarget | null): boolean {
  if (!target || !(target instanceof Element)) return false;
  if (
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    target instanceof HTMLSelectElement
  ) {
    return true;
  }
  return Boolean(target.closest(EDITABLE_SELECTOR));
}
