/**
 * E4-S2：对当前筛选结果做客户端分组（泳道）。
 * E37：支持 cf:<field_key> 按自定义字段分桶。
 * 列表泳道仅展示，不负责跨泳道拖拽改字段。
 */
import { issuePriorityOptions, issueStatusOptions, issueTypeOptions } from '@/constants/issue';
import { type LabelTable, lookupLabel } from '@/locales/display-label';
import type { Api } from '@/typings/api';

export interface GroupLabels {
  status?: LabelTable;
  priority?: LabelTable;
  type?: LabelTable;
}

export type SystemGroupByKey = 'none' | 'status' | 'assignee' | 'priority' | 'type' | 'label';
export type GroupByKey = SystemGroupByKey | `cf:${string}`;

export interface IssueGroupBucket {
  /** 稳定桶键（assignee 未分配为 __unassigned__） */
  key: string;
  /** 展示文案 */
  label: string;
  issues: Api.Issue.Issue[];
}

const UNASSIGNED_KEY = '__unassigned__';
const UNASSIGNED_LABEL = '未分配';

export const UNLABELLED_KEY = '__unlabelled__';
const UNLABELLED_LABEL = '无标签';

export const EMPTY_CF_KEY = '__empty__';
const EMPTY_CF_LABEL = '空';

export const ERROR_CF_KEY = '__error__';
const ERROR_CF_LABEL = '计算错误';

const STATUS_LABEL = Object.fromEntries(issueStatusOptions.map(o => [o.value, o.label]));
const PRIORITY_LABEL = Object.fromEntries(issuePriorityOptions.map(o => [o.value, o.label]));
const TYPE_LABEL = Object.fromEntries(issueTypeOptions.map(o => [o.value, o.label]));

/** 已知枚举的稳定顺序（其余未知键追加在后） */
const STATUS_ORDER = issueStatusOptions.map(o => o.value as string);
const PRIORITY_ORDER = issuePriorityOptions.map(o => o.value as string);
const TYPE_ORDER = issueTypeOptions.map(o => o.value as string);

const CF_DIM_RE = /^cf:([a-z][a-z0-9_-]{0,63})$/;

export const GROUPING_CF_TYPES = new Set([
  'single_select',
  'boolean',
  'text',
  'number',
  'date'
]);

const FORMULA_GROUPING_RESULT_TYPES = new Set(['number', 'text', 'boolean']);

export function isGroupingCfType(
  type: string | undefined | null,
  formulaResultType?: string | null
): boolean {
  if (type === 'formula') {
    const rt = (formulaResultType || 'number').trim() || 'number';
    return FORMULA_GROUPING_RESULT_TYPES.has(rt);
  }
  return Boolean(type && GROUPING_CF_TYPES.has(type));
}

/** Formula dims are display-only; never write CF value on drag. */
export function isFormulaCfReadonly(type: string | undefined | null): boolean {
  return type === 'formula';
}

export function parseCfDim(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const m = CF_DIM_RE.exec(value.trim());
  return m ? m[1] : null;
}

export function isCfDim(value: unknown): value is `cf:${string}` {
  return parseCfDim(value) !== null;
}

function assigneeKey(issue: Api.Issue.Issue): string {
  return issue.assignee_id || UNASSIGNED_KEY;
}

function assigneeLabel(issue: Api.Issue.Issue): string {
  if (!issue.assignee_id) return UNASSIGNED_LABEL;
  if (issue.assignee?.name) return issue.assignee.name;
  if (issue.assignee?.sso_name) return issue.assignee.sso_name;
  return issue.assignee_id.slice(0, 8);
}

function namedLabel(table: LabelTable | undefined, fallback: Record<string, string>, key: string) {
  if (table) return lookupLabel(table, key);
  return fallback[key] || key;
}

function resolveKeyAndLabel(
  issue: Api.Issue.Issue,
  groupBy: Exclude<SystemGroupByKey, 'none'>,
  labels?: GroupLabels
): { key: string; label: string } {
  switch (groupBy) {
    case 'status': {
      const key = String(issue.status || 'unknown');
      return { key, label: namedLabel(labels?.status, STATUS_LABEL, key) };
    }
    case 'priority': {
      const key = String(issue.priority || 'unknown');
      return { key, label: namedLabel(labels?.priority, PRIORITY_LABEL, key) };
    }
    case 'type': {
      const key = String(issue.type || 'unknown');
      return { key, label: namedLabel(labels?.type, TYPE_LABEL, key) };
    }
    case 'assignee':
      return { key: assigneeKey(issue), label: assigneeLabel(issue) };
    default:
      return { key: 'unknown', label: 'unknown' };
  }
}

function preferredOrder(groupBy: Exclude<SystemGroupByKey, 'none'>): string[] | null {
  if (groupBy === 'status') return STATUS_ORDER;
  if (groupBy === 'priority') return PRIORITY_ORDER;
  if (groupBy === 'type') return TYPE_ORDER;
  return null;
}

function orderKeys(groupBy: Exclude<SystemGroupByKey, 'none'> | 'cf', keys: string[]): string[] {
  if (groupBy === 'cf') {
    const rest = keys
      .filter(k => k !== EMPTY_CF_KEY && k !== ERROR_CF_KEY)
      .sort((a, b) => a.localeCompare(b));
    const tail: string[] = [];
    if (keys.includes(ERROR_CF_KEY)) tail.push(ERROR_CF_KEY);
    if (keys.includes(EMPTY_CF_KEY)) tail.push(EMPTY_CF_KEY);
    return [...rest, ...tail];
  }

  const preferred = preferredOrder(groupBy);

  if (!preferred) {
    if (groupBy === 'label') {
      const rest = keys.filter(k => k !== UNLABELLED_KEY).sort((a, b) => a.localeCompare(b));
      if (keys.includes(UNLABELLED_KEY)) {
        return [UNLABELLED_KEY, ...rest];
      }
      return rest;
    }
    // assignee：未分配置顶，其余按 key 字母序
    const rest = keys.filter(k => k !== UNASSIGNED_KEY).sort((a, b) => a.localeCompare(b));
    if (keys.includes(UNASSIGNED_KEY)) {
      return [UNASSIGNED_KEY, ...rest];
    }
    return rest;
  }

  const seen = new Set(keys);
  const ordered = preferred.filter(k => seen.has(k));
  const extras = keys.filter(k => !preferred.includes(k)).sort((a, b) => a.localeCompare(b));
  return [...ordered, ...extras];
}

/**
 * 将 issues 按属性分桶。`none` 返回空数组（由调用方渲染原列表）。
 */
function issueLabels(issue: Api.Issue.Issue): Array<{ id: string | number; name: string }> {
  const raw = (issue as Api.Issue.Issue & { tags?: Array<{ id?: number | string; name?: string }> }).tags;
  if (!Array.isArray(raw) || raw.length === 0) return [];
  return raw
    .filter(t => t && ((t.id !== undefined && t.id !== null) || Boolean(t.name)))
    .map(t => ({ id: t.id ?? t.name!, name: t.name || String(t.id) }));
}

function ensureBucket(map: Map<string, IssueGroupBucket>, key: string, label: string): IssueGroupBucket {
  let bucket = map.get(key);
  if (!bucket) {
    bucket = { key, label, issues: [] };
    map.set(key, bucket);
  } else if (bucket.label === UNLABELLED_LABEL && label && label !== UNLABELLED_LABEL) {
    bucket.label = label;
  } else if (bucket.label === EMPTY_CF_LABEL && label && label !== EMPTY_CF_LABEL) {
    bucket.label = label;
  }
  return bucket;
}

function groupByLabel(issues: Api.Issue.Issue[]): IssueGroupBucket[] {
  const map = new Map<string, IssueGroupBucket>();
  for (const issue of issues) {
    const labels = issueLabels(issue);
    if (!labels.length) {
      ensureBucket(map, UNLABELLED_KEY, UNLABELLED_LABEL).issues.push(issue);
    } else {
      for (const tag of labels) {
        ensureBucket(map, String(tag.id), tag.name).issues.push(issue);
      }
    }
  }
  return orderKeys('label', [...map.keys()]).map(k => map.get(k)!);
}

type IssueCfEntry = {
  key?: string;
  type?: string;
  value?: unknown;
  name?: string;
  options?: Array<{ value?: string; label?: string }>;
};

function issueCustomFields(issue: Api.Issue.Issue): IssueCfEntry[] {
  const anyIssue = issue as Api.Issue.Issue & {
    customFields?: IssueCfEntry[];
    custom_fields?: IssueCfEntry[];
  };
  const list = anyIssue.customFields || anyIssue.custom_fields || [];
  return Array.isArray(list) ? list : [];
}

function findCf(issue: Api.Issue.Issue, fieldKey: string): IssueCfEntry | undefined {
  return issueCustomFields(issue).find(x => x && x.key === fieldKey);
}

function resolveCfBucket(
  issue: Api.Issue.Issue,
  fieldKey: string
): { key: string; label: string } {
  const entry = findCf(issue, fieldKey);
  if (!entry) {
    return { key: EMPTY_CF_KEY, label: EMPTY_CF_LABEL };
  }
  const anyEntry = entry as IssueCfEntry & { error?: string | null; formulaResultType?: string };
  if (entry.type === 'formula' && anyEntry.error) {
    return { key: ERROR_CF_KEY, label: ERROR_CF_LABEL };
  }
  if (entry.value === null || entry.value === undefined) {
    return { key: EMPTY_CF_KEY, label: EMPTY_CF_LABEL };
  }
  const t =
    entry.type === 'formula'
      ? (anyEntry.formulaResultType || 'number')
      : entry.type || 'text';
  if (t === 'single_select') {
    const raw = entry.value;
    if (typeof raw !== 'string' || raw === '') {
      return { key: EMPTY_CF_KEY, label: EMPTY_CF_LABEL };
    }
    const opt = (entry.options || []).find(o => o && o.value === raw);
    return { key: raw, label: (opt?.label && String(opt.label)) || raw };
  }
  if (t === 'boolean') {
    if (entry.value === true) return { key: 'true', label: '是' };
    if (entry.value === false) return { key: 'false', label: '否' };
    return { key: EMPTY_CF_KEY, label: EMPTY_CF_LABEL };
  }
  // text | number | date | fallback
  if (typeof entry.value === 'string' && entry.value.trim() === '') {
    return { key: EMPTY_CF_KEY, label: EMPTY_CF_LABEL };
  }
  if (Array.isArray(entry.value)) {
    // multi_select should not reach here as grouping dim; treat as empty
    return { key: EMPTY_CF_KEY, label: EMPTY_CF_LABEL };
  }
  const key = String(entry.value);
  if (!key) return { key: EMPTY_CF_KEY, label: EMPTY_CF_LABEL };
  return { key, label: key };
}

function groupByCustomField(issues: Api.Issue.Issue[], fieldKey: string): IssueGroupBucket[] {
  const map = new Map<string, IssueGroupBucket>();
  for (const issue of issues) {
    const { key, label } = resolveCfBucket(issue, fieldKey);
    ensureBucket(map, key, label).issues.push(issue);
  }
  return orderKeys('cf', [...map.keys()]).map(k => map.get(k)!);
}

export function groupIssuesBy(
  issues: Api.Issue.Issue[],
  groupBy: GroupByKey,
  labels?: GroupLabels
): IssueGroupBucket[] {
  if (groupBy === 'none' || !issues?.length) {
    return [];
  }

  const cfKey = parseCfDim(groupBy);
  if (cfKey) {
    return groupByCustomField(issues, cfKey);
  }

  const map = new Map<string, IssueGroupBucket>();

  if (groupBy === 'label') {
    return groupByLabel(issues);
  }

  const systemKey = groupBy as Exclude<SystemGroupByKey, 'none'>;

  for (const issue of issues) {
    const { key, label } = resolveKeyAndLabel(issue, systemKey, labels);
    let bucket = map.get(key);
    if (!bucket) {
      bucket = { key, label, issues: [] };
      map.set(key, bucket);
    } else if (systemKey === 'assignee' && bucket.label === UNASSIGNED_LABEL && label !== UNASSIGNED_LABEL) {
      // 同 key 时保留更可读的人名（理论上同 id）
      bucket.label = label;
    }
    bucket.issues.push(issue);
  }

  return orderKeys(systemKey, [...map.keys()]).map(k => map.get(k)!);
}

export const GROUP_BY_OPTIONS: { label: string; value: GroupByKey }[] = [
  { label: '不分组', value: 'none' },
  { label: '状态', value: 'status' },
  { label: '负责人', value: 'assignee' },
  { label: '优先级', value: 'priority' },
  { label: '类型', value: 'type' },
  { label: '标签', value: 'label' }
];

export function buildGroupByOptions(
  customFields?: Array<{
    key: string;
    name: string;
    type: string;
    formulaResultType?: string | null;
  }>
): { label: string; value: GroupByKey }[] {
  const extras = (customFields || [])
    .filter(f => f && f.key && isGroupingCfType(f.type, f.formulaResultType))
    .map(f => ({
      label: f.type === 'formula' ? `${f.name || f.key}（计算值·只读）` : f.name || f.key,
      value: `cf:${f.key}` as GroupByKey
    }));
  return [...GROUP_BY_OPTIONS, ...extras];
}

export function isGroupByKey(value: unknown): value is GroupByKey {
  return (
    value === 'none' ||
    value === 'status' ||
    value === 'assignee' ||
    value === 'priority' ||
    value === 'type' ||
    value === 'label' ||
    isCfDim(value)
  );
}
