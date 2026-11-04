/**
 * user role constants
 */

export type UserRoleType = 'admin' | 'maintainer' | 'developer' | 'viewer';
export type WorkspaceRoleType = 'owner' | 'member' | 'viewer';
export type AnyRoleType = UserRoleType | WorkspaceRoleType;

export const USER_ROLES: ReadonlyArray<{
  value: UserRoleType;
  label: string;
  description: string;
  type: NaiveUI.ThemeColor;
}> = [
  { value: 'admin', label: '系统管理员', description: '拥有所有权限', type: 'error' },
  { value: 'maintainer', label: '维护者', description: '可以管理项目和资源', type: 'warning' },
  { value: 'developer', label: '开发者', description: '可以创建和编辑内容', type: 'primary' },
  { value: 'viewer', label: '查看者', description: '只读权限', type: 'default' }
] as const;

export const WORKSPACE_ROLES: ReadonlyArray<{
  value: WorkspaceRoleType;
  label: string;
  type: NaiveUI.ThemeColor;
}> = [
  { value: 'owner', label: '所有者', type: 'error' },
  { value: 'member', label: '成员', type: 'primary' },
  { value: 'viewer', label: '查看者', type: 'default' }
] as const;

export const roleRecord: Record<UserRoleType, App.I18n.I18nKey> = {
  admin: 'page.manage.user.role.admin',
  maintainer: 'page.manage.user.role.maintainer',
  developer: 'page.manage.user.role.developer',
  viewer: 'page.manage.user.role.viewer'
} as const;

export function getRoleLabel(role: AnyRoleType | string): string {
  const ws = WORKSPACE_ROLES.find(r => r.value === role);
  if (ws) return ws.label;
  return USER_ROLES.find(r => r.value === role)?.label || role;
}

export function getRoleType(role: AnyRoleType | string): NaiveUI.ThemeColor {
  const ws = WORKSPACE_ROLES.find(r => r.value === role);
  if (ws) return ws.type;
  return USER_ROLES.find(r => r.value === role)?.type || 'default';
}
