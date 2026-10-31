/** 任务相关 API */
import type { Document } from '@/typings/api/document';
import { request } from '../request';

export interface Task {
  id: string;
  requirement_id: string;
  parent_id?: string | null;
  code?: string | null;
  title: string;
  description?: string;
  task_type:
    | 'DESIGN'
    | 'IMPLEMENT'
    | 'TEST'
    | 'REVIEW'
    | 'DEPLOY'
    | 'DOCUMENT'
    | 'RESEARCH'
    | 'PGE_PLAN'
    | 'PGE_GENERATION'
    | 'PGE_EVALUATION';
  status: 'PENDING' | 'ASSIGNED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'BLOCKED' | 'CANCELLED';
  framework?: 'PGE' | null;
  assigned_to?: string;
  started_at?: string;
  completed_at?: string;
  input_data?: Record<string, any>;
  output_data?: Record<string, any>;
  artifacts?: Record<string, any>;
  error_message?: string;
  retry_count: number;
  required_skills?: { skills: string[] };
  created_at: string;
  updated_at: string;
  dependencies?: string[];
  dependents?: string[];
  children?: Task[];
  /** 关联的设计文档（由后端任务列表接口返回） */
  documents?: Document.Response[];
}

export interface TaskCreateParams {
  requirement_id: string;
  title: string;
  description?: string;
  task_type?: Task['task_type'];
  assigned_to?: string;
  parent_id?: string;
  input_data?: Record<string, any>;
  depends_on?: string[];
}

export interface TaskUpdateParams {
  title?: string;
  description?: string;
  status?: Task['status'];
  assigned_to?: string;
  parent_id?: string;
  output_data?: Record<string, any>;
  artifacts?: Record<string, any>;
  error_message?: string;
}

export interface PGETaskCreateParams {
  requirement_id: string;
  title: string;
  description?: string;
  framework: 'PGE';
  required_skills: string[];
}

export interface TaskPromptResponse {
  task_id: string;
  prompt: string;
}

export interface TaskListResponse {
  rows: Task[];
  total: number;
  current: number;
  pageSize: number;
  totalPages: number;
}

/** 获取任务列表 */
export function getTaskList(
  requirementId: string,
  params?: {
    status?: Task['status'];
    assigned_to?: string;
    page?: number;
    page_size?: number;
  }
) {
  return request<TaskListResponse>({
    url: '/api/tasks',
    method: 'GET',
    params: {
      requirement_id: requirementId,
      ...params
    }
  });
}

/** 获取任务详情 */
export function getTaskDetail(taskId: string) {
  return request<Task>({
    url: `/api/tasks/${taskId}`,
    method: 'GET'
  });
}

/** 创建任务 */
export function createTask(data: TaskCreateParams) {
  return request<Task>({
    url: '/api/tasks',
    method: 'POST',
    data
  });
}

/** 创建Agent任务 */
export function createPGETask(data: PGETaskCreateParams) {
  return request<Task>({
    url: '/api/tasks',
    method: 'POST',
    data
  });
}

/** 获取任务提示词 */
export function getTaskPrompt(taskId: string) {
  return request<TaskPromptResponse>({
    url: `/api/tasks/${taskId}/prompt`,
    method: 'GET'
  });
}

/** 预览任务提示词（不需要创建任务） */
export interface PGETaskPreviewParams {
  requirement_title: string;
  requirement_id: string;
  description?: string;
  required_skills?: string[];
}

export function previewPGETaskPrompt(data: PGETaskPreviewParams) {
  return request<TaskPromptResponse>({
    url: '/api/tasks/preview-prompt',
    method: 'POST',
    data
  });
}

/** 更新任务 */
export function updateTask(taskId: string, data: TaskUpdateParams) {
  return request<Task>({
    url: `/api/tasks/${taskId}`,
    method: 'PUT',
    data
  });
}

/** 删除任务 */
export function deleteTask(taskId: string) {
  return request({
    url: `/api/tasks/${taskId}`,
    method: 'DELETE'
  });
}

/** 开始任务 */
export function startTask(taskId: string) {
  return request<Task>({
    url: `/api/tasks/${taskId}/start`,
    method: 'POST'
  });
}

/** 完成任务 */
export function completeTask(
  taskId: string,
  data?: {
    output_data?: Record<string, any>;
    artifacts?: Record<string, any>;
  }
) {
  return request<Task>({
    url: `/api/tasks/${taskId}/complete`,
    method: 'POST',
    data
  });
}

/** 标记任务失败 */
export function failTask(taskId: string, errorMessage: string) {
  return request<Task>({
    url: `/api/tasks/${taskId}/fail`,
    method: 'POST',
    data: { error_message: errorMessage }
  });
}

/** 任务类型映射 */
export const TaskTypeMap: Record<Task['task_type'], string> = {
  DESIGN: '设计',
  IMPLEMENT: '实现',
  TEST: '测试',
  REVIEW: '审查',
  DEPLOY: '部署',
  DOCUMENT: '文档',
  RESEARCH: '研究',
  PGE_PLAN: '规划',
  PGE_GENERATION: '生成',
  PGE_EVALUATION: '评估'
};

/** 任务状态映射 */
export const TaskStatusMap: Record<Task['status'], string> = {
  PENDING: '待处理',
  ASSIGNED: '已分配',
  RUNNING: '进行中',
  COMPLETED: '已完成',
  FAILED: '失败',
  BLOCKED: '已阻塞',
  CANCELLED: '已取消'
};

/** 任务状态颜色 */
export const TaskStatusColorMap: Record<
  Task['status'],
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

/** 批量导入任务响应 */
export interface TaskImportResponse {
  requirement_id: string;
  imported_count: number;
  failed_count: number;
  tasks: Task[];
  errors: string[];
}

/** 批量导入任务 */
export function importTasks(requirementId: string, file: File) {
  const formData = new FormData();
  formData.append('file', file);

  return request<TaskImportResponse>({
    url: `/api/tasks/import/${requirementId}`,
    method: 'POST',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
}
