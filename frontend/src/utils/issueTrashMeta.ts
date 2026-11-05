/** E77: trash/restore copy helpers (pure; vitest). */

export function trashEmptyHint(): string {
  return '回收站为空';
}

export function restoreSuccessMessage(code: string): string {
  const c = (code || '').trim();
  return c ? `已恢复 ${c}` : '已恢复';
}

export function deletedReadonlyBanner(): string {
  return '此 Issue 已在回收站中，只读。恢复后可继续编辑。';
}
