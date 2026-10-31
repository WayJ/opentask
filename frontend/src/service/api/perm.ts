import { request } from '../request';

/**
 * 权限点管理 API（后端 opentask/api/user_center/perm_router.py）
 *
 * 权限点字典由代码定义（permission_defs.py，seed 幂等同步），
 * 管理端只读展示 + 启停；停用后 require_permission 即时 403。
 */

/** 全量权限点列表（登录即可；module 分组由前端按 code 前缀处理） */
export function fetchGetPermissions() {
  return request<Api.SystemManage.PermissionInfo[]>({
    url: '/api/permissions',
    method: 'get'
  });
}

/** 启用 / 停用权限点（需 manage:role:perm 权限码） */
export function fetchUpdatePermissionStatus(permissionId: string, status: 0 | 1) {
  return request<Api.SystemManage.PermissionInfo>({
    url: `/api/permissions/${permissionId}/status`,
    method: 'put',
    data: { status }
  });
}
