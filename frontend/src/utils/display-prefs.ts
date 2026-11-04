/**
 * E7-S3：Issue 列表/看板 Display 契约（个人 prefs 与 Saved View display_json 共用键）。
 */
import { type GroupByKey, isGroupByKey } from './groupIssuesBy';

export type SwimlaneBy = 'none' | 'assignee' | 'priority' | 'type' | 'label';

export type DisplayFieldKey =
  | 'assignee'
  | 'priority'
  | 'labels'
  | 'estimate_points'
  | 'due_date'
  | 'project'
  | 'cycle'
  | 'issue_code'
  | 'type';

export type IssueDisplayFields = Record<DisplayFieldKey, boolean>;

export interface IssueDisplayState {
  viewMode: 'list' | 'board';
  groupBy: GroupByKey;
  swimlaneBy: SwimlaneBy;
  hideEmptyLanes: boolean;
  fields: IssueDisplayFields;
}

export const DISPLAY_FIELD_KEYS: DisplayFieldKey[] = [
  'issue_code',
  'assignee',
  'priority',
  'labels',
  'type',
  'estimate_points',
  'due_date',
  'project',
  'cycle'
];

export const DISPLAY_FIELD_LABELS: Record<DisplayFieldKey, string> = {
  issue_code: '编号',
  assignee: '负责人',
  priority: '优先级',
  labels: '标签',
  type: '类型',
  estimate_points: '估点',
  due_date: '截止日期',
  project: '项目',
  cycle: 'Cycle'
};

export const SWIMLANE_OPTIONS: { label: string; value: SwimlaneBy }[] = [
  { label: '无泳道', value: 'none' },
  { label: '负责人', value: 'assignee' },
  { label: '优先级', value: 'priority' },
  { label: '类型', value: 'type' },
  { label: '标签', value: 'label' }
];

const DEFAULT_FIELDS: IssueDisplayFields = {
  assignee: true,
  priority: true,
  labels: true,
  estimate_points: false,
  due_date: false,
  project: false,
  cycle: false,
  issue_code: true,
  type: false
};

function isSwimlaneBy(value: unknown): value is SwimlaneBy {
  return (
    value === 'none' ||
    value === 'assignee' ||
    value === 'priority' ||
    value === 'type' ||
    value === 'label'
  );
}

export function defaultIssueDisplay(): IssueDisplayState {
  return {
    viewMode: 'list',
    groupBy: 'none',
    swimlaneBy: 'none',
    hideEmptyLanes: false,
    fields: { ...DEFAULT_FIELDS }
  };
}

export function normalizeIssueDisplay(raw: unknown): IssueDisplayState {
  const out = defaultIssueDisplay();
  if (!raw || typeof raw !== 'object') return out;
  const obj = raw as Record<string, unknown>;

  if (obj.view_mode === 'list' || obj.view_mode === 'board') {
    out.viewMode = obj.view_mode;
  }
  if (isGroupByKey(obj.group_by)) {
    out.groupBy = obj.group_by;
  }
  if (isSwimlaneBy(obj.swimlane_by)) {
    out.swimlaneBy = obj.swimlane_by;
  }
  if ('hide_empty_lanes' in obj) {
    out.hideEmptyLanes = Boolean(obj.hide_empty_lanes);
  }
  const fieldsIn = obj.fields;
  if (fieldsIn && typeof fieldsIn === 'object') {
    const f = fieldsIn as Record<string, unknown>;
    for (const key of DISPLAY_FIELD_KEYS) {
      if (key in f) {
        out.fields[key] = Boolean(f[key]);
      }
    }
  }
  return out;
}

export function displayStateToJson(state: IssueDisplayState): Record<string, unknown> {
  return {
    view_mode: state.viewMode,
    group_by: state.groupBy,
    swimlane_by: state.swimlaneBy,
    hide_empty_lanes: state.hideEmptyLanes,
    fields: { ...state.fields }
  };
}

export function isSwimlaneByKey(value: unknown): value is SwimlaneBy {
  return isSwimlaneBy(value);
}
