/** E79: project lead + members display helpers (roster-only) */

export interface ProjectUserLike {
  id: string;
  name?: string | null;
  sso_name?: string | null;
  sso_account?: string | null;
}

export function leadLabel(u: ProjectUserLike | null | undefined): string {
  if (!u) return '未设置负责人';
  return u.sso_name || u.name || u.sso_account || u.id.slice(0, 8);
}

export function memberIds(members: ProjectUserLike[] | null | undefined): string[] {
  if (!Array.isArray(members)) return [];
  return members.filter(m => m && m.id).map(m => m.id);
}

export function formatMemberCount(count: number | null | undefined): string {
  const n = typeof count === 'number' && count >= 0 ? count : 0;
  return `${n} 名成员`;
}
