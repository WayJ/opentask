import { request } from '../request';

/**
 * 角色管理 API（后端 opentask/api/user_center/role_router.py）
 *
 * - 列表 GET /api/roles 见 system-manage.ts 的 fetchGetRoles（旧结构兼容）；
 * - 写操作需 manage:role:create / update / delete / perm 权限码；
 * - 系统角色只许改 name/description，admin 角色权限不可改（后端 409）。
 */

/** 创建角色（code 唯一，冲突 409） */
export function fetchCreateRole(data: Api.SystemManage.RoleCreate) {
  return request<Api.SystemManage.RoleInfo>({
    url: '/api/roles',
    method: 'post',
    data
  });
}

/** 更新角色（仅传需要修改的字段；CUSTOM 档位由 dept_ids 覆盖自定义部门） */
export function fetchUpdateRole(roleId: string, data: Api.SystemManage.RoleUpdate) {
  return request<Api.SystemManage.RoleInfo>({
    url: `/api/roles/${roleId}`,
    method: 'put',
    data
  });
}

/** 删除角色（系统角色 409；仍有关联用户 409） */
export function fetchDeleteRole(roleId: string) {
  return request<null>({
    url: `/api/roles/${roleId}`,
    method: 'delete'
  });
}

/** 角色当前权限码集合 + CUSTOM 自定义部门回显（登录即可读） */
export function fetchGetRolePermissions(roleId: string) {
  return request<Api.SystemManage.RolePermissions>({
    url: `/api/roles/${roleId}/permissions`,
    method: 'get'
  });
}

/** 整组覆盖角色权限（codes 必须全部存在且启用；admin 角色 409） */
export function fetchSetRolePermissions(roleId: string, codes: string[]) {
  return request<Api.SystemManage.RoleInfo>({
    url: `/api/roles/${roleId}/permissions`,
    method: 'put',
    data: { codes }
  });
}
