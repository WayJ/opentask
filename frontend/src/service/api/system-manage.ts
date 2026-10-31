import { request } from '../request';

/**
 * 管理端用户 / 角色 API
 *
 * 全部对接真实后端（Phase 5）：
 * - /api/users：列表（keyword/role/status/dept_id 筛选）、建号、编辑、软删、
 *   状态启禁、重置密码（临时密码只返一次）、详情回显
 * - /api/roles：角色选项（value=code、label=name）
 * 部门相关见 department.ts。
 */

/** 用户列表（分页 + keyword/role/status/dept_id 筛选） */
export function fetchGetUsers(params: {
  current: number;
  pageSize: number;
  status?: number | null;
  keyword?: string | null;
  role?: string | null;
  dept_id?: string | null;
}) {
  return request<Api.SystemManage.UserList>({
    url: '/api/users',
    method: 'get',
    params
  });
}

/** 用户详情（编辑抽屉回显：role_codes + dept_assignments） */
export function fetchGetUserDetail(userId: string) {
  return request<Api.SystemManage.UserDetail>({
    url: `/api/users/${userId}`,
    method: 'get'
  });
}

/** 创建用户（password 留空 → 首次登录需改密） */
export function fetchCreateUser(data: Api.SystemManage.UserCreate) {
  return request<{
    id: string;
    username: string;
    name: string;
    role: string;
    must_change_password: boolean;
  }>({
    url: '/api/users',
    method: 'post',
    data
  });
}

/** 编辑用户（username 唯一标识不可改；role_codes/dept_assignments 覆盖式） */
export function fetchUpdateUser(userId: string, data: Api.SystemManage.UserUpdate) {
  return request<null>({
    url: `/api/users/${userId}`,
    method: 'put',
    data
  });
}

/** 软删用户（禁用 + token_version+1 + 吊销全部 refresh，等同强制下线） */
export function fetchDeleteUser(userId: string) {
  return request<null>({
    url: `/api/users/${userId}`,
    method: 'delete'
  });
}

/** 启用 / 禁用用户 */
export function fetchUpdateUserStatus(userId: string, data: Api.SystemManage.UserStatusUpdate) {
  return request<null>({
    url: `/api/users/${userId}/status`,
    method: 'put',
    data
  });
}

/**
 * 重置密码（生成 12 位临时密码）
 *
 * 明文 tempPassword 只在本次响应返回一次，不落盘；调用方需立即展示并提醒复制。
 */
export function fetchResetUserPassword(userId: string) {
  return request<{ tempPassword: string }>({
    url: `/api/users/${userId}/reset-password`,
    method: 'put'
  });
}

/** 角色选项列表（value=角色编码，label=角色名；含禁用与系统角色） */
export function fetchGetRoles() {
  return request<Api.SystemManage.RoleInfo[]>({
    url: '/api/roles',
    method: 'get'
  });
}
