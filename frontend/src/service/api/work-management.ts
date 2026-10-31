/**
 * 工作管理 API
 * 包含研发组、成本项目、工作安排、工作反馈等接口
 */
import { request } from '../request';

/** 研发组成员 */
export interface RdGroupMember {
  id: string;
  group_id: string;
  user_id: string;
  role: string;
  joined_at: string;
}

/** 研发组 */
export interface RdGroup {
  id: string;
  name: string;
  director_id: string;
  leader_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  members?: RdGroupMember[];
}

/** 成本项目 */
export interface CostProject {
  id: string;
  name: string;
  code: string;
  description?: string;
  manager_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  total_estimated_hours?: number;
  completed_hours?: number;
  completion_rate?: number;
  high_quality_rate?: number;
}

/** 工作安排 */
export interface WorkAssignment {
  id: string;
  title: string;
  assignee_id: string;
  assigner_id: string;
  group_id: string;
  cost_project_id: string;
  deadline: string;
  estimated_hours: number;
  week_start: string;
  status: string;
  related_type?: string;
  related_id?: string;
  quality: string;
  created_at: string;
  updated_at: string;
  is_overdue?: boolean;
  overdue_days?: number;
}

/** 工作反馈 */
export interface WorkFeedback {
  id: string;
  assignment_id?: string;
  user_id: string;
  feedback_date: string;
  content?: string;
  status: string;
  is_planned: boolean;
  unplanned_type?: string;
  unplanned_related_id?: string;
  created_at?: string;
}

/** 我的周工作汇总 */
export interface MyWeeklyWorkSummary {
  total_estimated_hours: number;
  completed_count: number;
  pending_count: number;
  overdue_count: number;
}

/** 我的周工作响应 */
export interface MyWeeklyWorkResponse {
  current_week: WorkAssignment[];
  overdue: WorkAssignment[];
  summary: MyWeeklyWorkSummary;
}

/** 计划外工作项 */
export interface UnplannedWorkItem {
  id: string;
  title: string;
  type: string;
}

/** 计划外工作响应 */
export interface UnplannedWorkResponse {
  resolved_issues: UnplannedWorkItem[];
  created_issues: UnplannedWorkItem[];
  completed_reqs: UnplannedWorkItem[];
  created_reqs: UnplannedWorkItem[];
}

/**
 * 清理请求参数，移除空值、null 和 undefined
 */
function cleanParams(params: Record<string, any>): Record<string, any> {
  return Object.fromEntries(Object.entries(params).filter(([_, v]) => v !== '' && v !== null && v !== undefined));
}

// ============ 研发组管理 ============

/** 创建研发组 */
export function createRdGroup(data: { name: string; director_id: string; leader_id: string }) {
  return request<RdGroup>({
    url: '/api/work-management/rd-groups',
    method: 'post',
    data
  });
}

/** 获取研发组列表 */
export function getRdGroups(director_id?: string) {
  const params = director_id ? { director_id } : undefined;
  return request<RdGroup[]>({
    url: '/api/work-management/rd-groups',
    method: 'get',
    params
  });
}

/** 获取研发组详情 */
export function getRdGroup(id: string) {
  return request<RdGroup>({
    url: `/api/work-management/rd-groups/${id}`,
    method: 'get'
  });
}

/** 更新研发组 */
export function updateRdGroup(id: string, data: Partial<RdGroup>) {
  return request<RdGroup>({
    url: `/api/work-management/rd-groups/${id}`,
    method: 'put',
    data
  });
}

/** 删除研发组 */
export function deleteRdGroup(id: string) {
  return request({
    url: `/api/work-management/rd-groups/${id}`,
    method: 'delete'
  });
}

/** 添加组成员 */
export function addGroupMember(groupId: string, userId: string, role: string = 'member') {
  return request<RdGroupMember>({
    url: `/api/work-management/rd-groups/${groupId}/members`,
    method: 'post',
    params: { user_id: userId, role }
  });
}

/** 移除组成员 */
export function removeGroupMember(groupId: string, userId: string) {
  return request({
    url: `/api/work-management/rd-groups/${groupId}/members/${userId}`,
    method: 'delete'
  });
}

// ============ 成本项目管理 ============

/** 创建成本项目 */
export function createCostProject(data: { name: string; code: string; description?: string; manager_id: string }) {
  return request<CostProject>({
    url: '/api/work-management/cost-projects',
    method: 'post',
    data
  });
}

/** 获取成本项目列表 */
export function getCostProjects(manager_id?: string) {
  const params = manager_id ? { manager_id } : undefined;
  return request<CostProject[]>({
    url: '/api/work-management/cost-projects',
    method: 'get',
    params
  });
}

/** 获取成本项目详情（含统计） */
export function getCostProject(id: string) {
  return request<{
    project: CostProject;
    stats: {
      total_estimated_hours: number;
      completed_hours: number;
      completion_rate: number;
      high_quality_rate: number;
    };
  }>({
    url: `/api/work-management/cost-projects/${id}`,
    method: 'get'
  });
}

/** 更新成本项目 */
export function updateCostProject(id: string, data: Partial<CostProject>) {
  return request<CostProject>({
    url: `/api/work-management/cost-projects/${id}`,
    method: 'put',
    data
  });
}

/** 删除成本项目 */
export function deleteCostProject(id: string) {
  return request({
    url: `/api/work-management/cost-projects/${id}`,
    method: 'delete'
  });
}

// ============ 工作安排 ============

/** 创建工作安排 */
export function createWorkAssignment(data: {
  title: string;
  assignee_id: string;
  group_id: string;
  cost_project_id: string;
  deadline: string;
  estimated_hours: number;
  week_start: string;
  related_type?: string;
  related_id?: string;
}) {
  return request<WorkAssignment>({
    url: '/api/work-management/work-assignments',
    method: 'post',
    data
  });
}

/** 获取工作安排列表 */
export function getWorkAssignments(params?: { assignee_id?: string; group_id?: string; week_start?: string }) {
  const cleanedParams = params ? cleanParams(params) : undefined;
  return request<WorkAssignment[]>({
    url: '/api/work-management/work-assignments',
    method: 'get',
    params: cleanedParams
  });
}

/** 获取工作安排详情 */
export function getWorkAssignment(id: string) {
  return request<WorkAssignment>({
    url: `/api/work-management/work-assignments/${id}`,
    method: 'get'
  });
}

/** 更新工作安排 */
export function updateWorkAssignment(id: string, data: Partial<WorkAssignment>) {
  return request<WorkAssignment>({
    url: `/api/work-management/work-assignments/${id}`,
    method: 'put',
    data
  });
}

/** 删除工作安排 */
export function deleteWorkAssignment(id: string) {
  return request({
    url: `/api/work-management/work-assignments/${id}`,
    method: 'delete'
  });
}

// ============ 工作反馈 ============

/** 提交工作反馈 */
export function createWorkFeedback(data: {
  assignment_id?: string;
  feedback_date: string;
  content?: string;
  status: string;
  is_planned: boolean;
  unplanned_type?: string;
  unplanned_related_id?: string;
}) {
  return request<WorkFeedback>({
    url: '/api/work-management/work-feedback',
    method: 'post',
    data
  });
}

/** 获取我的反馈历史 */
export function getWorkFeedback() {
  return request<WorkFeedback[]>({
    url: '/api/work-management/work-feedback',
    method: 'get'
  });
}

// ============ 我的周视图 ============

/** 获取我的周工作（计划+遗留） */
export function getMyWeeklyWork(weekStart: string) {
  return request<MyWeeklyWorkResponse>({
    url: '/api/work-management/my-weekly-work',
    method: 'get',
    params: { week_start: weekStart }
  });
}

/** 获取我的计划外工作 */
export function getMyUnplannedWork(weekStart: string) {
  return request<UnplannedWorkResponse>({
    url: '/api/work-management/my-weekly-work/unplanned',
    method: 'get',
    params: { week_start: weekStart }
  });
}

// ============ 附件管理 ============

/** 上传附件 */
export function uploadAttachment(assignmentId: string, file: File) {
  const formData = new FormData();
  formData.append('file', file);
  return request({
    url: `/api/work-management/work-assignments/${assignmentId}/attachments`,
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' }
  });
}

/** 获取附件列表 */
export function getAttachments(assignmentId: string) {
  return request({
    url: `/api/work-management/work-assignments/${assignmentId}/attachments`,
    method: 'get'
  });
}

/** 删除附件 */
export function deleteAttachment(assignmentId: string, attachmentId: string) {
  return request({
    url: `/api/work-management/work-assignments/${assignmentId}/attachments/${attachmentId}`,
    method: 'delete'
  });
}

/** 下载附件 */
export function downloadAttachment(assignmentId: string, attachmentId: string) {
  return request({
    url: `/api/work-management/work-assignments/${assignmentId}/attachments/${attachmentId}/download`,
    method: 'get',
    responseType: 'blob'
  });
}

// ============ 导出 ============

/** 导出成本项目报告 */
export function exportCostProject(projectId: string, format: string = 'xlsx', weekStart?: string) {
  return request({
    url: `/api/work-management/cost-projects/${projectId}/export`,
    method: 'post',
    params: { format, week_start: weekStart },
    responseType: 'blob'
  });
}
