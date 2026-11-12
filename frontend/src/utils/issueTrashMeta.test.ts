import { afterEach, describe, expect, it } from 'vitest';
import { setLocale } from '@/locales';
import { deletedReadonlyBanner, restoreSuccessMessage, trashEmptyHint } from './issueTrashMeta';

afterEach(() => setLocale('zh-CN'));
describe('issueTrashMeta', () => {
  it('empty hint', () => {
    setLocale('zh-CN');
    expect(trashEmptyHint()).toBe('回收站为空');
    setLocale('en-US');
    expect(trashEmptyHint()).toBe('Trash is empty');
  });
  it('restore success includes code', () => {
    expect(restoreSuccessMessage('WAY-12')).toBe('已恢复 WAY-12');
    expect(restoreSuccessMessage('')).toBe('已恢复');
  });
  it('deleted banner', () => {
    expect(deletedReadonlyBanner()).toContain('回收站');
  });
});
