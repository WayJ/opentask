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
  | 'add_comment'
  | 'set_custom_field';

export type CustomFieldConditionOp = 'eq' | 'neq' | 'contains' | 'is_set' | 'is_empty';

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

export const CF_CONDITION_OPS: Array<{ label: string; value: CustomFieldConditionOp }> = [
  { label: 'eq', value: 'eq' },
  { label: 'neq', value: 'neq' },
  { label: 'contains', value: 'contains' },
  { label: 'is_set', value: 'is_set' },
  { label: 'is_empty', value: 'is_empty' }
];

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

/** 从 condition 抽出 customField 块（camel / snake） */
export function getCustomFieldCondition(
  condition: Record<string, unknown> | null | undefined
): { key?: string; fieldId?: string; op: CustomFieldConditionOp; value?: unknown } | null {
  if (!condition) return null;
  const raw = (condition.customField ?? condition.custom_field) as Record<string, unknown> | undefined;
  if (!raw || typeof raw !== 'object') return null;
  const op = String(raw.op || 'eq') as CustomFieldConditionOp;
  return {
    key: raw.key != null ? String(raw.key) : undefined,
    fieldId: raw.fieldId != null ? String(raw.fieldId) : raw.field_id != null ? String(raw.field_id) : undefined,
    op,
    value: raw.value
  };
}

/** 合并/写入 customField 条件（保留其它 AND 条件） */
export function withCustomFieldCondition(
  condition: Record<string, unknown> | null | undefined,
  cf: { key: string; op: CustomFieldConditionOp; value?: unknown } | null
): Record<string, unknown> | null {
  const base: Record<string, unknown> = { ...(condition || {}) };
  delete base.custom_field;
  if (!cf || !cf.key) {
    delete base.customField;
    return Object.keys(base).length ? base : null;
  }
  const block: Record<string, unknown> = { key: cf.key, op: cf.op };
  if (cf.op !== 'is_set' && cf.op !== 'is_empty') {
    block.value = cf.value;
  }
  base.customField = block;
  return base;
}

export function summarizeAutomationRule(row: Pick<AutomationRuleRow, 'condition' | 'actionType' | 'actionConfig'>): string {
  const parts: string[] = [];
  const cf = getCustomFieldCondition(row.condition);
  if (cf) {
    const ref = cf.key || cf.fieldId || '?';
    if (cf.op === 'is_set' || cf.op === 'is_empty') {
      parts.push(`cf:${ref} ${cf.op}`);
    } else {
      parts.push(`cf:${ref} ${cf.op} ${JSON.stringify(cf.value)}`);
    }
  }
  if (row.actionType === 'set_custom_field') {
    const cfg = row.actionConfig || {};
    const ref = cfg.key ?? cfg.fieldId ?? cfg.field_id ?? '?';
    parts.push(`set cf:${ref}=${JSON.stringify(cfg.value)}`);
  }
  return parts.join(' · ') || '—';
}
