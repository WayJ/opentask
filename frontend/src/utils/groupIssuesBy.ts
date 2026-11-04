/**
 * E4-S2：对当前筛选结果做客户端分组（泳道）。
 * 列表泳道仅展示，不负责跨泳道拖拽改字段。
 */
import { issuePriorityOptions, issueStatusOptions, issueTypeOptions } from '@/constants/issue';
import type { Api } from '@/typings/api';

export type GroupByKey = 'none' | 'status' | 'assignee' | 'priority' | 'type';

export interface IssueGroupBucket {
  /** 稳定桶键（assignee 未分配为 __unassigned__） */
  key: string;
  /** 展示文案 */
  label: string;
  issues: Api.Issue.Issue[];
}

const UNASSIGNED_KEY = '__unassigned__';
const UNASSIGNED_LABEL = '未分配';

const STATUS_LABEL = Object.fromEntries(issueStatusOptions.map(o => [o.value, o.label]));
const PRIORITY_LABEL = Object.fromEntries(issuePriorityOptions.map(o => [o.value, o.label]));
const TYPE_LABEL = Object.fromEntries(issueTypeOptions.map(o => [o.value, o.label]));

/** 已知枚举的稳定顺序（其余未知键追加在后） */
const STATUS_ORDER = issueStatusOptions.map(o => o.value as string);
const PRIORITY_ORDER = issuePriorityOptions.map(o => o.value as string);
const TYPE_ORDER = issueTypeOptions.map(o => o.value as string);

function assigneeKey(issue: Api.Issue.Issue): string {
  return issue.assignee_id || UNASSIGNED_KEY;
}

function assigneeLabel(issue: Api.Issue.Issue): string {
  if (!issue.assignee_id) return UNASSIGNED_LABEL;
  if (issue.assignee?.name) return issue.assignee.name;
  if (issue.assignee?.sso_name) return issue.assignee.sso_name;
  return issue.assignee_id.slice(0, 8);
}

function resolveKeyAndLabel(
  issue: Api.Issue.Issue,
  groupBy: Exclude<GroupByKey, 'none'>
): { key: string; label: string } {
  switch (groupBy) {
    case 'status': {
      const key = String(issue.status || 'unknown');
      return { key, label: STATUS_LABEL[key] || key };
    }
    case 'priority': {
      const key = String(issue.priority || 'unknown');
      return { key, label: PRIORITY_LABEL[key] || key };
    }
    case 'type': {
      const key = String(issue.type || 'unknown');
      return { key, label: TYPE_LABEL[key] || key };
    }
    case 'assignee':
      return { key: assigneeKey(issue), label: assigneeLabel(issue) };
    default:
      return { key: 'unknown', label: 'unknown' };
  }
}

function preferredOrder(groupBy: Exclude<GroupByKey, 'none'>): string[] | null {
  if (groupBy === 'status') return STATUS_ORDER;
  if (groupBy === 'priority') return PRIORITY_ORDER;
  if (groupBy === 'type') return TYPE_ORDER;
  return null;
}

function orderKeys(groupBy: Exclude<GroupByKey, 'none'>, keys: string[]): string[] {
  const preferred = preferredOrder(groupBy);

  if (!preferred) {
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
export function groupIssuesBy(issues: Api.Issue.Issue[], groupBy: GroupByKey): IssueGroupBucket[] {
  if (groupBy === 'none' || !issues?.length) {
    return [];
  }

  const map = new Map<string, IssueGroupBucket>();

  for (const issue of issues) {
    const { key, label } = resolveKeyAndLabel(issue, groupBy);
    let bucket = map.get(key);
    if (!bucket) {
      bucket = { key, label, issues: [] };
      map.set(key, bucket);
    } else if (groupBy === 'assignee' && bucket.label === UNASSIGNED_LABEL && label !== UNASSIGNED_LABEL) {
      // 同 key 时保留更可读的人名（理论上同 id）
      bucket.label = label;
    }
    bucket.issues.push(issue);
  }

  return orderKeys(groupBy, [...map.keys()]).map(k => map.get(k)!);
}

export const GROUP_BY_OPTIONS: { label: string; value: GroupByKey }[] = [
  { label: '不分组', value: 'none' },
  { label: '状态', value: 'status' },
  { label: '负责人', value: 'assignee' },
  { label: '优先级', value: 'priority' },
  { label: '类型', value: 'type' }
];

export function isGroupByKey(value: unknown): value is GroupByKey {
  return value === 'none' || value === 'status' || value === 'assignee' || value === 'priority' || value === 'type';
}
