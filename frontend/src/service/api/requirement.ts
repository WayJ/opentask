import type { Document } from '@/typings/api/document';
import { request } from '../request';

/**
 * Requirement API
 * 包含需求和需求任务拆解的所有接口
 */

/**
 * 清理请求参数，移除空值、null 和 undefined
 */
function cleanParams(params: Record<string, any>): Record<string, any> {
  return Object.fromEntries(Object.entries(params).filter(([_, v]) => v !== '' && v !== null && v !== undefined));
}

/** Get requirement list */
export function fetchRequirementList(params?: {
  status?: Api.Requirement.RequirementStatus;
  priority?: Api.Requirement.Priority;
  assignee_id?: string;
  project_id?: string;
  page?: number;
  page_size?: number;
  search?: string;
}) {
  // 清理空值参数，避免 URL 中出现 ?priority=&page=1 这样的情况
  const cleanedParams = params ? cleanParams(params) : undefined;

  return request<Api.Requirement.RequirementList>({
    url: '/api/requirements',
    method: 'get',
    params: cleanedParams
  });
}

/** Get requirement detail */
export function fetchRequirementDetail(id: string) {
  return request<Api.Requirement.Requirement>({
    url: `/api/requirements/${id}`,
    method: 'get'
  });
}

/** Alias for fetchRequirementDetail - for backward compatibility */
export const getRequirementDetail = fetchRequirementDetail;

/** Get requirement with events */
export function fetchRequirementWithEvents(id: string) {
  return request<Api.Requirement.RequirementWithEvents>({
    url: `/api/requirements/${id}/with-events`,
    method: 'get'
  });
}

/** Get requirement timeline */
export function fetchRequirementTimeline(id: string) {
  return request<Api.Requirement.Timeline>({
    url: `/api/requirements/${id}/timeline`,
    method: 'get'
  });
}

/** Create requirement */
export function createRequirement(data: Api.Requirement.CreateRequirement) {
  return request<Api.Requirement.Requirement>({
    url: '/api/requirements',
    method: 'post',
    data
  });
}

/** Update requirement */
export function updateRequirement(id: string, data: Api.Requirement.UpdateRequirement) {
  return request<Api.Requirement.Requirement>({
    url: `/api/requirements/${id}`,
    method: 'put',
    data
  });
}

/** Delete requirement */
export function deleteRequirement(id: string) {
  return request({
    url: `/api/requirements/${id}`,
    method: 'delete'
  });
}

/** Assign requirement */
export function assignRequirement(id: string, data: Api.Requirement.AssignRequest) {
  return request<Api.Requirement.Requirement>({
    url: `/api/requirements/${id}/assign`,
    method: 'post',
    data
  });
}

/** Get requirement statistics */
export function fetchRequirementStats() {
  return request<Api.Requirement.Statistics>({
    url: '/api/requirements/stats',
    method: 'get'
  });
}

/** Search requirements */
export function searchRequirements(query: string, limit?: number) {
  return request<Api.Requirement.Requirement[]>({
    url: '/api/requirements/search',
    method: 'get',
    params: { q: query, limit }
  });
}

/** Get requirement detail by code (e.g., "需求2026-73") */
export function fetchRequirementByCode(code: string) {
  return request<Api.Requirement.Requirement>({
    url: `/api/requirements/by-code/${encodeURIComponent(code)}`,
    method: 'get'
  });
}

// ============================================================================
// 需求任务拆解 API (Requirement Task Breakdown)
// ============================================================================

/** 需求任务类型 */
export type TaskType = 'DESIGN' | 'IMPLEMENT' | 'TEST' | 'REVIEW' | 'DEPLOY' | 'DOCUMENT' | 'RESEARCH';

/** 需求任务状态 */
export type TaskStatus = 'PENDING' | 'ASSIGNED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'BLOCKED' | 'CANCELLED';

/** 需求任务 */
export interface Task {
  id: string;
  requirement_id: string;
  parent_id?: string | null;
  code?: string | null;
  title: string;
  description?: string;
  task_type: TaskType;
  status: TaskStatus;
  assigned_to?: string;
  started_at?: string;
  completed_at?: string;
  input_data?: Record<string, any>;
  output_data?: Record<string, any>;
  artifacts?: Record<string, any>;
  error_message?: string;
  retry_count: number;
  created_at: string;
  updated_at: string;
  dependencies?: string[];
  dependents?: string[];
  children?: Task[];
  /** 关联的设计文档（由后端任务列表接口返回） */
  documents?: Document.Response[];
}

/** 创建任务参数 */
export interface TaskCreateParams {
  requirement_id: string;
  title: string;
  description?: string;
  task_type?: TaskType;
  assigned_to?: string;
  parent_id?: string;
  input_data?: Record<string, any>;
  depends_on?: string[];
}

/** 更新任务参数 */
export interface TaskUpdateParams {
  title?: string;
  description?: string;
  status?: TaskStatus;
  assigned_to?: string;
  parent_id?: string;
  output_data?: Record<string, any>;
  artifacts?: Record<string, any>;
  error_message?: string;
}

/** 任务列表响应 */
export interface TaskListResponse {
  rows: Task[];
  total: number;
  current: number;
  pageSize: number;
  totalPages: number;
}

/** 批量导入任务响应 */
export interface TaskImportResponse {
  requirement_id: string;
  imported_count: number;
  failed_count: number;
  tasks: Task[];
  errors: string[];
}

/** 获取需求任务列表 */
export function fetchRequirementTaskList(
  requirementId: string,
  params?: {
    status?: TaskStatus;
    assigned_to?: string;
    page?: number;
    page_size?: number;
  }
) {
  return request<TaskListResponse>({
    url: `/api/requirements/${requirementId}/tasks`,
    method: 'get',
    params
  });
}

/** 获取任务详情 */
export function fetchRequirementTaskDetail(requirementId: string, taskId: string) {
  return request<Task>({
    url: `/api/requirements/${requirementId}/tasks/${taskId}`,
    method: 'get'
  });
}

/** 创建任务 */
export function createRequirementTask(requirementId: string, data: Omit<TaskCreateParams, 'requirement_id'>) {
  return request<Task>({
    url: `/api/requirements/${requirementId}/tasks`,
    method: 'post',
    data
  });
}

/** 更新任务 */
export function updateRequirementTask(requirementId: string, taskId: string, data: TaskUpdateParams) {
  return request<Task>({
    url: `/api/requirements/${requirementId}/tasks/${taskId}`,
    method: 'put',
    data
  });
}

/** 删除任务 */
export function deleteRequirementTask(requirementId: string, taskId: string) {
  return request({
    url: `/api/requirements/${requirementId}/tasks/${taskId}`,
    method: 'delete'
  });
}

/** 开始任务 */
export function startRequirementTask(requirementId: string, taskId: string) {
  return request<Task>({
    url: `/api/requirements/${requirementId}/tasks/${taskId}/start`,
    method: 'post'
  });
}

/** 完成任务 */
export function completeRequirementTask(
  requirementId: string,
  taskId: string,
  data?: {
    output_data?: Record<string, any>;
    artifacts?: Record<string, any>;
  }
) {
  return request<Task>({
    url: `/api/requirements/${requirementId}/tasks/${taskId}/complete`,
    method: 'post',
    data
  });
}

/** 标记任务失败 */
export function failRequirementTask(requirementId: string, taskId: string, errorMessage: string) {
  return request<Task>({
    url: `/api/requirements/${requirementId}/tasks/${taskId}/fail`,
    method: 'post',
    data: { error_message: errorMessage }
  });
}

/** 批量导入任务 */
export function importRequirementTasks(requirementId: string, file: File) {
  const formData = new FormData();
  formData.append('file', file);

  return request<TaskImportResponse>({
    url: `/api/requirements/${requirementId}/tasks/import`,
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
}

/** 任务类型映射 */
export const RequirementTaskTypeMap: Record<TaskType, string> = {
  DESIGN: '设计',
  IMPLEMENT: '实现',
  TEST: '测试',
  REVIEW: '审查',
  DEPLOY: '部署',
  DOCUMENT: '文档',
  RESEARCH: '研究'
};

/** 任务状态映射 */
export const RequirementTaskStatusMap: Record<TaskStatus, string> = {
  PENDING: '待处理',
  ASSIGNED: '已分配',
  RUNNING: '进行中',
  COMPLETED: '已完成',
  FAILED: '失败',
  BLOCKED: '已阻塞',
  CANCELLED: '已取消'
};

/** 任务状态颜色 */
export const RequirementTaskStatusColorMap: Record<
  TaskStatus,
  'default' | 'info' | 'success' | 'error' | 'warning' | 'primary'
> = {
  PENDING: 'default',
  ASSIGNED: 'info',
  RUNNING: 'primary',
  COMPLETED: 'success',
  FAILED: 'error',
  BLOCKED: 'warning',
  CANCELLED: 'default'
};

// ========================================================================
// 需求评论相关类型和接口
// ========================================================================

/** 需求评论 */
export interface RequirementComment {
  id: string;
  requirement_id: string;
  user_id: string;
  content: string;
  created_at: string;
  updated_at: string;
  user_info?: {
    sso_name?: string;
  };
}

/** 获取需求评论列表 */
export function fetchRequirementComments(requirementId: string) {
  return request<{ rows: RequirementComment[]; total: number }>({
    url: `/api/requirements/${requirementId}/comments`,
    method: 'get'
  });
}

/** 添加需求评论 */
export function addRequirementComment(requirementId: string, content: string) {
  const formData = new FormData();
  formData.append('content', content);

  return request<RequirementComment>({
    url: `/api/requirements/${requirementId}/comments`,
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
}
