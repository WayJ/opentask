/**
 * user role constants
 */

/**
 * user role type
 */
export type UserRoleType = 'admin' | 'maintainer' | 'developer' | 'viewer';

/**
 * user role list
 */
export const USER_ROLES: ReadonlyArray<{
  value: UserRoleType;
  label: string;
  description: string;
  type: NaiveUI.ThemeColor;
}> = [
  {
    value: 'admin',
    label: '系统管理员',
    description: '拥有所有权限',
    type: 'error'
  },
  {
    value: 'maintainer',
    label: '维护者',
    description: '可以管理项目和资源',
    type: 'warning'
  },
  {
    value: 'developer',
    label: '开发者',
    description: '可以创建和编辑内容',
    type: 'primary'
  },
  {
    value: 'viewer',
    label: '查看者',
    description: '只读权限',
    type: 'default'
  }
] as const;

/**
 * role record for i18n
 */
export const roleRecord: Record<UserRoleType, App.I18n.I18nKey> = {
  admin: 'page.manage.user.role.admin',
  maintainer: 'page.manage.user.role.maintainer',
  developer: 'page.manage.user.role.developer',
  viewer: 'page.manage.user.role.viewer'
} as const;

/**
 * get role label by value
 */
export function getRoleLabel(role: UserRoleType): string {
  return USER_ROLES.find(r => r.value === role)?.label || role;
}

/**
 * get role type for tag
 */
export function getRoleType(role: UserRoleType): NaiveUI.ThemeColor {
  return USER_ROLES.find(r => r.value === role)?.type || 'default';
}
