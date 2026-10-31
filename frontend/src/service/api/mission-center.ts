import type { ApiResponse } from '@/types/common';
import { request } from '../request';

// 创建任务请求
export interface CreateTaskFromCommentRequest {
  source_type: 'requirement' | 'issue';
  source_id: string;
  comment_content: string;
  description: string;
  created_by: string;
}

// 任务响应
export interface TaskResponse {
  task_id: string;
  title: string;
  description: string;
  priority: string;
  status: string;
  link_data: string[];
  meta_data: {
    source_type: string;
    source_id: string;
    source_code: string;
    source_title: string;
    comment_content: string;
    created_by: string;
    created_from: string;
  };
  assignee: string;
  progress_percentage: number;
  current_step: string;
  result: Record<string, any>;
  error: Record<string, any>;
  logs: Array<{
    level: string;
    message: string;
    timestamp: string;
  }>;
  created_at: string;
  updated_at: string;
  completed_at: string;
}

// 创建任务响应
export interface CreateTaskFromCommentResponse {
  code: number;
  message: string;
  data: TaskResponse;
  timestamp: number;
}

/**
 * 从评论创建任务
 * @param createRequest 创建任务请求数据
 * @returns 创建的任务信息
 */
export async function createTaskFromComment(
  createRequest: CreateTaskFromCommentRequest
): Promise<CreateTaskFromCommentResponse> {
  const response = await request.post<ApiResponse<CreateTaskFromCommentResponse>>(
    '/api/mission-center/tasks/from-comment',
    createRequest
  );
  return response.data;
}

// ========== 兼容性 API（旧版本） ==========

/** Agent 任务类型 */
export type AgentTaskType = 'DESIGN' | 'IMPLEMENT' | 'TEST' | 'REVIEW' | 'DEPLOY' | 'DOCUMENT' | 'RESEARCH';

/** Agent 任务状态 */
export type AgentTaskStatus = 'PENDING' | 'ASSIGNED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'BLOCKED' | 'CANCELLED';

/** Agent 任务优先级 */
export type AgentTaskPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';

/** 进度历史记录 */
export interface ProgressHistory {
  percentage: number;
  step: string;
  message?: string; // AI 的思考文本/内心独白
  timestamp: string;
}

export interface AgentTask {
  task_id: string;
  title: string;
  description?: string;
  priority: AgentTaskPriority;
  assignee?: string; // 改为可选
  deadline?: string;
  status: AgentTaskStatus;
  progress_percentage: number;
  current_step: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  result?: Record<string, any>;
  error?: Record<string, any>;
  logs: Array<{
    level: string;
    message: string;
    timestamp: string;
  }>;
  progressHistory: ProgressHistory[];
  acceptance_criteria?: string[];
  reward?: number;
}

export interface AgentTaskCreate {
  title: string;
  description?: string;
  priority?: AgentTaskPriority;
  assignee?: string; // 可选
  deadline?: string;
  metadata?: Record<string, any>;
  requirements?: string[];
  acceptance_criteria?: string[];
  reward?: number;
}

export interface AgentTaskUpdate {
  status?: AgentTaskStatus;
  progress_percentage?: number;
  current_step?: string;
  logs?: Array<{
    level: string;
    message: string;
    timestamp: string;
  }>;
}

export interface AgentTaskListResponse {
  rows: AgentTask[];
  total: number;
  current: number;
  pageSize: number;
  totalPages: number;
}

export interface AgentTaskStatistics {
  total: number;
  by_status: Record<AgentTaskStatus, number>;
  by_priority: Record<AgentTaskPriority, number>;
}

/** 获取任务列表 */
export function fetchAgentTaskList(params?: {
  status?: AgentTaskStatus;
  assignee?: string;
  limit?: number;
  offset?: number;
}) {
  return request<AgentTaskListResponse>({
    url: '/api/mission-center',
    method: 'GET',
    params
  });
}

/** 获取任务详情 */
export function fetchAgentTaskDetail(taskId: string) {
  return request<AgentTask>({
    url: `/api/mission-center/${taskId}`,
    method: 'GET'
  });
}

/** 创建任务 */
export function createAgentTask(data: AgentTaskCreate) {
  return request<AgentTask>({
    url: '/api/mission-center',
    method: 'POST',
    data
  });
}

/** 更新任务状态 */
export function updateAgentTask(taskId: string, data: AgentTaskUpdate) {
  return request<AgentTask>({
    url: `/api/mission-center/${taskId}`,
    method: 'PATCH',
    data
  });
}

/** 取消任务 */
export function cancelAgentTask(taskId: string, reason?: string) {
  return request<AgentTask>({
    url: `/api/mission-center/${taskId}/cancel`,
    method: 'POST',
    data: { reason }
  });
}

/** 删除任务 */
export function deleteAgentTask(taskId: string) {
  return request({
    url: `/api/mission-center/${taskId}`,
    method: 'DELETE'
  });
}

/** 获取任务统计 */
export function fetchAgentTaskStatistics() {
  return request<AgentTaskStatistics>({
    url: '/api/mission-center/stats/summary',
    method: 'GET'
  });
}

/** 获取在线 Agent 列表 */
export function fetchOnlineAgents() {
  return request<{
    agents: Array<{
      agentId: string;
      name: string;
      agentType: string;
      capabilities: string[];
      status: string;
      registeredAt: string;
      lastHeartbeat: string;
    }>;
    total: number;
  }>({
    url: '/api/test/online-agents',
    method: 'GET'
  });
}

// ========== 钱包相关类型和 API ==========

/** 钱包信息 */
export interface Wallet {
  agent_id: string;
  balance: number;
  total_earned: number;
  total_spent: number;
  created_at: string;
  updated_at: string;
}

/** 钱包列表响应 */
export interface WalletListResponse {
  wallets: Wallet[];
  total_balance: number;
  total_agents: number;
}

/** 交易信息 */
export interface Transaction {
  id: string;
  agent_id: string;
  amount: number;
  balance_after: number;
  transaction_type: string;
  description: string;
  related_task_id?: string;
  created_at: string;
}

/** 交易列表响应 */
export interface TransactionListResponse {
  transactions: Transaction[];
  total: number;
  current: number;
  pageSize: number;
  totalPages: number;
}

/** 钱包统计响应 */
export interface WalletStatistics {
  total_balance: number;
  total_earned: number;
  total_spent: number;
  transaction_count: number;
  active_wallets: number;
}

/** 获取所有钱包列表 */
export function fetchWallets() {
  return request<WalletListResponse>({
    url: '/api/mission-center/wallets',
    method: 'GET'
  });
}

/** 获取指定 Agent 的钱包 */
export function fetchWallet(agentId: string) {
  return request<Wallet>({
    url: `/api/mission-center/wallets/${agentId}`,
    method: 'GET'
  });
}

/** 获取交易流水列表 */
export function fetchTransactions(params?: { agent_id?: string; limit?: number; offset?: number }) {
  return request<TransactionListResponse>({
    url: '/api/mission-center/transactions',
    method: 'GET',
    params
  });
}

/** 获取钱包统计信息 */
export function fetchWalletStatistics() {
  return request<WalletStatistics>({
    url: '/api/mission-center/wallets/stats/summary',
    method: 'GET'
  });
}

// ========== 评论相关类型和 API ==========

/** 评论类型 */
export type CommentType = 'comment' | 'claim' | 'plan' | 'question';

/** 任务评论 */
export interface TaskComment {
  id: number;
  task_id: string;
  agent_id?: string;
  user_id?: string;
  content: string;
  comment_type: CommentType;
  parent_id?: number;
  created_at: string;
  updated_at: string;
}

/** 评论列表响应 */
export interface CommentListResponse {
  comments: TaskComment[];
  total: number;
}

/** 创建评论请求 */
export interface CreateCommentRequest {
  content: string;
  comment_type?: CommentType;
  agent_id?: string;
  user_id?: string;
  parent_id?: number;
}

/** 获取任务评论列表 */
export function fetchTaskComments(taskId: string, params?: { limit?: number; offset?: number }) {
  return request<CommentListResponse>({
    url: `/api/mission-center/comments/${taskId}`,
    method: 'GET',
    params
  });
}

/** 创建任务评论 */
export function createTaskComment(taskId: string, data: CreateCommentRequest) {
  return request<TaskComment>({
    url: `/api/mission-center/comments/${taskId}`,
    method: 'POST',
    data
  });
}

/** 删除任务评论 */
export function deleteTaskComment(commentId: number) {
  return request<{ message: string }>({
    url: `/api/mission-center/comments/${commentId}`,
    method: 'DELETE'
  });
}
