import { request } from '../request';

export type AutomationTrigger =
  | 'issue.created'
  | 'issue.status_changed'
  | 'issue.assignee_changed'
  | 'label_added'
  | 'custom_field_changed';

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


export const MAX_CUSTOM_FIELD_CONDITIONS = 5;

export type CustomFieldCondition = {
  key?: string;
  fieldId?: string;
  op: CustomFieldConditionOp;
  value?: unknown;
};

/** 读取多条 CF 条件（customFields[] 优先；否则单 customField 包成数组） */
export function getCustomFieldConditions(
  condition: Record<string, unknown> | null | undefined
): CustomFieldCondition[] {
  if (!condition) return [];
  const list = (condition.customFields ?? condition.custom_fields) as unknown;
  if (Array.isArray(list)) {
    return list
      .filter(x => x && typeof x === 'object')
      .map(raw => {
        const r = raw as Record<string, unknown>;
        return {
          key: r.key != null ? String(r.key) : undefined,
          fieldId:
            r.fieldId != null
              ? String(r.fieldId)
              : r.field_id != null
                ? String(r.field_id)
                : undefined,
          op: String(r.op || 'eq') as CustomFieldConditionOp,
          value: r.value
        };
      });
  }
  const single = getCustomFieldCondition(condition);
  return single ? [single] : [];
}

/** 写入多条 CF 条件；>5 抛错；空数组清除 CF 条件键 */
export function withCustomFieldConditions(
  condition: Record<string, unknown> | null | undefined,
  cfs: CustomFieldCondition[] | null
): Record<string, unknown> | null {
  const base: Record<string, unknown> = { ...(condition || {}) };
  delete base.custom_field;
  delete base.customField;
  delete base.custom_fields;
  delete base.customFields;
  if (!cfs || cfs.length === 0) {
    return Object.keys(base).length ? base : null;
  }
  if (cfs.length > MAX_CUSTOM_FIELD_CONDITIONS) {
    throw new Error(`customFields 最多 ${MAX_CUSTOM_FIELD_CONDITIONS} 条`);
  }
  base.customFields = cfs.map(cf => {
    const block: Record<string, unknown> = { key: cf.key, op: cf.op };
    if (cf.fieldId) block.fieldId = cf.fieldId;
    if (cf.op !== 'is_set' && cf.op !== 'is_empty') {
      block.value = cf.value;
    }
    return block;
  });
  return base;
}

export const MAX_DELAY_MINUTES = 10080;

/** Read delay_minutes / delayMinutes from actionConfig; 0 if missing. */
export function getDelayMinutes(cfg: Record<string, unknown> | null | undefined): number {
  if (!cfg) return 0;
  const raw = cfg.delay_minutes ?? cfg.delayMinutes;
  if (raw == null) return 0;
  const n = typeof raw === 'number' ? raw : Number(raw);
  if (!Number.isFinite(n) || n < 0) return 0;
  return Math.min(Math.floor(n), MAX_DELAY_MINUTES);
}

/** Merge delay into actionConfig. delay<=0 strips keys. */
export function withDelayMinutes(
  cfg: Record<string, unknown> | null | undefined,
  delay: number
): Record<string, unknown> {
  const base = { ...(cfg || {}) };
  delete base.delay_minutes;
  delete base.delayMinutes;
  const n = Number(delay);
  if (!Number.isFinite(n) || n <= 0) return base;
  const clamped = Math.min(Math.max(Math.floor(n), 1), MAX_DELAY_MINUTES);
  base.delay_minutes = clamped;
  return base;
}

/** Format delay for summary: 90 → "delay 1h30m", 60 → "delay 1h", 5 → "delay 5m" */
export function formatDelaySummary(minutes: number): string {
  const m = Math.floor(minutes);
  if (m <= 0) return '';
  if (m % 60 === 0) return `delay ${m / 60}h`;
  if (m > 60) {
    const h = Math.floor(m / 60);
    const r = m % 60;
    return `delay ${h}h${r}m`;
  }
  return `delay ${m}m`;
}

/** triggerConfig 摘要：custom_field_changed 字段过滤 */
export function summarizeCfChangedTrigger(cfg: Record<string, unknown> | null | undefined): string {
  if (!cfg) return '';
  const key = cfg.field_key ?? cfg.key ?? cfg.fieldId ?? cfg.field_id;
  const parts: string[] = [];
  if (key != null) parts.push(`field:${key}`);
  if (cfg.from !== undefined) parts.push(`from=${JSON.stringify(cfg.from)}`);
  if (cfg.to !== undefined) parts.push(`to=${JSON.stringify(cfg.to)}`);
  return parts.join(' ');
}

export function summarizeAutomationRule(
  row: Pick<AutomationRuleRow, 'condition' | 'actionType' | 'actionConfig'> & {
    triggerType?: string;
    triggerConfig?: Record<string, unknown>;
  }
): string {
  const parts: string[] = [];
  if (row.triggerType === 'custom_field_changed') {
    const t = summarizeCfChangedTrigger(row.triggerConfig);
    if (t) parts.push(`on ${t}`);
    else parts.push('on cf-changed');
  }
  const cfs = getCustomFieldConditions(row.condition);
  for (const cf of cfs) {
    const ref = cf.key || cf.fieldId || '?';
    if (cf.op === 'is_set' || cf.op === 'is_empty') {
      parts.push(`cf:${ref} ${cf.op}`);
    } else {
      parts.push(`cf:${ref} ${cf.op} ${JSON.stringify(cf.value)}`);
    }
  }
  const delay = getDelayMinutes(row.actionConfig);
  const delayPrefix = delay > 0 ? `${formatDelaySummary(delay)} → ` : '';
  if (row.actionType === 'set_custom_field') {
    const cfg = row.actionConfig || {};
    const ref = cfg.key ?? cfg.fieldId ?? cfg.field_id ?? '?';
    parts.push(`${delayPrefix}set cf:${ref}=${JSON.stringify(cfg.value)}`);
  } else if (delay > 0) {
    parts.push(`${formatDelaySummary(delay)} → ${row.actionType}`);
  }
  return parts.join(' · ') || '—';
}
