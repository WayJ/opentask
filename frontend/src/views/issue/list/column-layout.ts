/** Code column stays put so the title can be sized against the visible table. */
export const ISSUE_CODE_COLUMN_WIDTH = 120;

/** Desktop title width. Narrow tables shrink toward the visible remainder. */
export const ISSUE_TITLE_COLUMN_MAX = 300;

/**
 * Tables at least this wide match the 1280 layout, where a pinned action
 * column sits beside the title instead of covering it.
 */
export const ISSUE_ACTIONS_PIN_MIN = 900;

const TITLE_GUTTER = 24;

export function issueListColumnLayout(tableWidth: number) {
  const pinActions = tableWidth >= ISSUE_ACTIONS_PIN_MIN;
  const available = tableWidth - ISSUE_CODE_COLUMN_WIDTH - TITLE_GUTTER;
  const titleWidth = pinActions ? ISSUE_TITLE_COLUMN_MAX : Math.min(ISSUE_TITLE_COLUMN_MAX, Math.max(160, available));
  return { pinActions, titleWidth };
}
