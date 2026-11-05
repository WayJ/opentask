/** E71: multi-assignee display helpers */

export interface AssigneeLike {
  id: string;
  name?: string | null;
  sso_name?: string | null;
  sso_account?: string | null;
}

export function assigneeLabel(u: AssigneeLike | null | undefined): string {
  if (!u) return '未分配';
  return u.sso_name || u.name || u.sso_account || u.id.slice(0, 8);
}

export function formatAssigneesStack(
  assignees: AssigneeLike[] | null | undefined,
  maxVisible = 3
): { visible: AssigneeLike[]; overflow: number; primaryId: string | null } {
  const list = Array.isArray(assignees) ? assignees.filter(a => a && a.id) : [];
  const visible = list.slice(0, Math.max(0, maxVisible));
  const overflow = Math.max(0, list.length - visible.length);
  return {
    visible,
    overflow,
    primaryId: list[0]?.id ?? null
  };
}

export function primaryAssigneeId(
  assignees: AssigneeLike[] | null | undefined,
  fallback?: string | null
): string | null {
  if (Array.isArray(assignees) && assignees.length > 0) return assignees[0].id;
  return fallback ?? null;
}
