/** Agent API - Agent 管理相关接口 */
import { request } from '../request';

/** Agent 状态类型 */
export type AgentStatus = 'registered' | 'online' | 'idle' | 'busy' | 'offline' | 'retired' | 'error';

/** Agent 类型 */
export type AgentType = 'architecture' | 'entertainment' | 'coding';

/** Agent 信息 */
export interface Agent {
  agent_id: string;
  agent_type: AgentType;
  agent_name: string;
  capabilities: string[];
  model?: string;
  status: AgentStatus;
  previous_status?: AgentStatus;
  connected_at?: string;
  last_heartbeat?: string;
  disconnected_at?: string;
  total_tasks_handled: number;
  successful_tasks: number;
  failed_tasks: number;
  total_execution_time: number;
  current_task_id?: string;
  current_task_started_at?: string;
  heartbeat_misses: number;
  error_count: number;
  last_error?: string;
  last_error_at?: string;
  is_active: boolean;
  retired_at?: string;
  retired_by?: string;
  retire_reason?: string;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
}

/** Agent 统计摘要 */
export interface AgentStats {
  total_agents: number;
  online_agents: number;
  offline_agents: number;
  retired_agents: number;
  active_agents: number;
  total_tasks: number;
  successful_tasks: number;
  failed_tasks: number;
  success_rate: number;
}

/** Agent 列表查询参数 */
export interface AgentListParams {
  skip?: number;
  limit?: number;
  agent_type?: AgentType;
  status?: AgentStatus;
  is_active?: boolean;
}

/** 获取 Agent 列表 */
export function fetchAgents(params?: AgentListParams) {
  return request<Agent[]>({
    url: '/api/agents',
    method: 'get',
    params
  });
}

/** 获取 Agent 详情 */
export function fetchAgent(agentId: string) {
  return request<{ data: Agent }>({
    url: `/api/agents/${agentId}`,
    method: 'get'
  });
}

/** 退役 Agent */
export function retireAgent(agentId: string, retiredBy: string, reason: string) {
  return request<{ data: Agent }>({
    url: `/api/agents/${agentId}/retire`,
    method: 'post',
    params: {
      retired_by: retiredBy,
      reason
    }
  });
}

/** 重新激活 Agent */
export function reactivateAgent(agentId: string) {
  return request<{ data: Agent }>({
    url: `/api/agents/${agentId}/reactivate`,
    method: 'post'
  });
}

/** 获取 Agent 统计摘要 */
export function fetchAgentStats() {
  return request<{ data: AgentStats }>({
    url: '/api/agents/stats/summary',
    method: 'get'
  });
}
