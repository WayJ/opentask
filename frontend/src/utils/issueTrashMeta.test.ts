import { describe, expect, it } from 'vitest';
import { deletedReadonlyBanner, restoreSuccessMessage, trashEmptyHint } from './issueTrashMeta';

describe('issueTrashMeta', () => {
  it('empty hint', () => {
    expect(trashEmptyHint()).toBe('回收站为空');
  });

  it('restore success includes code', () => {
    expect(restoreSuccessMessage('WAY-12')).toBe('已恢复 WAY-12');
    expect(restoreSuccessMessage('')).toBe('已恢复');
  });

  it('deleted banner', () => {
    expect(deletedReadonlyBanner()).toContain('回收站');
  });
});
