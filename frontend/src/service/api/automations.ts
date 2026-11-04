import { request } from '../request';

export type AutomationTrigger =
  | 'issue.created'
  | 'issue.status_changed'
  | 'issue.assignee_changed'
  | 'label_added';

export type AutomationAction =
  | 'set_status'
  | 'set_assignee'
  | 'add_label'
  | 'set_priority'
  | 'add_comment';

export interface AutomationRuleRow {
  id: string;
  workspaceId: string;
  name: string;
  enabled: boolean;
  triggerType: AutomationTrigger | string;
  triggerConfig: Record<string, unknown>;
  condition: Record<string, unknown> | null;
  actionType: AutomationAction | string;
  actionConfig: Record<string, unknown>;
  createdBy?: string | null;
  position: number;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface AutomationListResult {
  rows: AutomationRuleRow[];
  total: number;
}

export function fetchAutomations() {
  return request<AutomationListResult>({ url: '/api/automations', method: 'get' });
}

export function fetchCreateAutomation(body: {
  name: string;
  triggerType: string;
  actionType: string;
  triggerConfig?: Record<string, unknown>;
  condition?: Record<string, unknown> | null;
  actionConfig?: Record<string, unknown>;
  enabled?: boolean;
  position?: number;
}) {
  return request<AutomationRuleRow>({ url: '/api/automations', method: 'post', data: body });
}

export function fetchUpdateAutomation(
  id: string,
  body: Partial<{
    name: string;
    triggerType: string;
    triggerConfig: Record<string, unknown>;
    setTriggerConfig: boolean;
    condition: Record<string, unknown> | null;
    setCondition: boolean;
    actionType: string;
    actionConfig: Record<string, unknown>;
    setActionConfig: boolean;
    enabled: boolean;
    position: number;
  }>
) {
  return request<AutomationRuleRow>({ url: `/api/automations/${id}`, method: 'patch', data: body });
}

export function fetchEnableAutomation(id: string) {
  return request<AutomationRuleRow>({ url: `/api/automations/${id}/enable`, method: 'post' });
}

export function fetchDisableAutomation(id: string) {
  return request<AutomationRuleRow>({ url: `/api/automations/${id}/disable`, method: 'post' });
}

export function fetchDeleteAutomation(id: string) {
  return request<{ id: string }>({ url: `/api/automations/${id}`, method: 'delete' });
}

/** 解析表单里的 JSON 配置；空串 → {} */
export function parseAutomationJson(raw: string, fallback: Record<string, unknown> = {}): Record<string, unknown> {
  const t = (raw || '').trim();
  if (!t) return { ...fallback };
  const v = JSON.parse(t) as unknown;
  if (!v || typeof v !== 'object' || Array.isArray(v)) {
    throw new Error('配置须为 JSON 对象');
  }
  return v as Record<string, unknown>;
}
