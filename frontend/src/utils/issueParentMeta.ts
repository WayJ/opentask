/** E78: set-parent / promote-to-root copy helpers (pure; vitest). */

export function excludeSelfFromPicker<T extends { id: string }>(
  rows: T[],
  selfId: string
): T[] {
  const sid = (selfId || '').trim();
  if (!sid) return rows.slice();
  return rows.filter(r => r.id !== sid);
}

export function canPromoteToRoot(parentIssueId: string | null | undefined): boolean {
  return Boolean(parentIssueId);
}

export function setParentSuccessMessage(parentCode: string | null | undefined): string {
  const code = (parentCode || '').trim();
  if (!code) return '已提升为根';
  return `已设为 ${code} 的子项`;
}
