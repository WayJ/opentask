import { $t } from '@/locales';

/** E77: trash/restore copy helpers; empty hint follows the active locale. */
export function trashEmptyHint(): string {
  return $t('page.issueTrash.empty');
}

export function restoreSuccessMessage(code: string): string {
  const c = (code || '').trim();
  return c ? `已恢复 ${c}` : '已恢复';
}

export function deletedReadonlyBanner(): string {
  return '此问题已在回收站中，只读。恢复后可继续编辑。';
}
