import { request } from '../request';

/**
 * 部门管理 API（后端 opentask/api/user_center/dept_router.py）
 *
 * - 树查询登录即可（管理端与选择器共用）；
 * - 写操作需 manage:dept:create / update / delete 权限码；
 * - 用户归属分配（PUT /api/users/{id}/depts）需 manage:user:update 权限码。
 * 响应统一蛇形命名（与后端 _dept_data 一致）。
 */

/** 部门树（children 嵌套；含禁用部门） */
export function fetchGetDeptTree() {
  return request<Api.SystemManage.Department[]>({
    url: '/api/departments',
    method: 'get'
  });
}

/** 创建部门（parent_id 空 = 根部门） */
export function fetchCreateDept(data: Api.SystemManage.DeptCreate) {
  return request<Api.SystemManage.Department>({
    url: '/api/departments',
    method: 'post',
    data
  });
}

/** 更新部门（仅传需要修改的字段；parent_id 显式 null = 移为根） */
export function fetchUpdateDept(deptId: string, data: Api.SystemManage.DeptUpdate) {
  return request<Api.SystemManage.Department>({
    url: `/api/departments/${deptId}`,
    method: 'put',
    data
  });
}

/** 启用 / 禁用部门（后端复用 manage:dept:update 权限码） */
export function fetchUpdateDeptStatus(deptId: string, status: 0 | 1) {
  return request<Api.SystemManage.Department>({
    url: `/api/departments/${deptId}/status`,
    method: 'put',
    data: { status }
  });
}

/** 删除部门（有子部门或有成员 → 后端 409） */
export function fetchDeleteDept(deptId: string) {
  return request<null>({
    url: `/api/departments/${deptId}`,
    method: 'delete'
  });
}

/** 覆盖式设置用户部门归属（items 空数组 = 清空；非空时恰一行 is_primary） */
export function fetchAssignUserDepts(userId: string, items: Api.SystemManage.DeptAssignment[]) {
  return request<{ assigned: number }>({
    url: `/api/users/${userId}/depts`,
    method: 'put',
    data: { items }
  });
}
