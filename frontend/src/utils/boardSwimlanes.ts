/**
 * E7-S3：看板行维泳道 × 列维 status（客户端矩阵；展示-only）。
 * E37：行维支持 cf:<field_key>。
 */
import { issueStatusOptions } from '@/constants/issue';
import type { Api } from '@/typings/api';
import { type GroupByKey, groupIssuesBy, isCfDim } from './groupIssuesBy';
import type { SwimlaneBy } from './display-prefs';

export type BoardStatus = Api.Issue.IssueStatus;

export interface BoardSwimlane {
  key: string;
  label: string;
  /** status → issues in that column within this lane */
  columns: Record<string, Api.Issue.Issue[]>;
}

const STATUS_KEYS = issueStatusOptions.map(o => o.value as string);

function emptyColumns(): Record<string, Api.Issue.Issue[]> {
  const cols: Record<string, Api.Issue.Issue[]> = {};
  for (const s of STATUS_KEYS) cols[s] = [];
  return cols;
}

function sortIssues(list: Api.Issue.Issue[]): Api.Issue.Issue[] {
  return [...list].sort((a, b) => {
    const pa = a.position ?? Number.MAX_SAFE_INTEGER;
    const pb = b.position ?? Number.MAX_SAFE_INTEGER;
    if (pa !== pb) return pa - pb;
    return String(a.created_at || '').localeCompare(String(b.created_at || ''));
  });
}

function fillByStatus(issues: Api.Issue.Issue[]): Record<string, Api.Issue.Issue[]> {
  const cols = emptyColumns();
  for (const issue of sortIssues(issues)) {
    const key = issue.status && issue.status in cols ? String(issue.status) : 'open';
    cols[key].push(issue);
  }
  return cols;
}

function laneIsEmpty(columns: Record<string, Api.Issue.Issue[]>): boolean {
  return STATUS_KEYS.every(s => (columns[s] || []).length === 0);
}

function swimlaneToGroupBy(swimlaneBy: Exclude<SwimlaneBy, 'none'>): Exclude<GroupByKey, 'none'> {
  if (isCfDim(swimlaneBy)) return swimlaneBy;
  return swimlaneBy;
}

/**
 * 构建看板泳道矩阵。`swimlaneBy=none` 时返回单泳道 `__all__`。
 */
export function buildBoardSwimlanes(
  issues: Api.Issue.Issue[],
  swimlaneBy: SwimlaneBy,
  hideEmptyLanes: boolean
): BoardSwimlane[] {
  const source = issues || [];

  if (swimlaneBy === 'none') {
    const lane: BoardSwimlane = {
      key: '__all__',
      label: '',
      columns: fillByStatus(source)
    };
    if (hideEmptyLanes && laneIsEmpty(lane.columns)) return [];
    return [lane];
  }

  const buckets = groupIssuesBy(source, swimlaneToGroupBy(swimlaneBy));
  const lanes: BoardSwimlane[] = buckets.map(b => ({
    key: b.key,
    label: b.label,
    columns: fillByStatus(b.issues)
  }));

  if (!hideEmptyLanes) return lanes;
  return lanes.filter(l => !laneIsEmpty(l.columns));
}

export const BOARD_STATUS_COLUMNS = issueStatusOptions.map(opt => ({
  status: opt.value as Api.Issue.IssueStatus,
  label: opt.label
}));
