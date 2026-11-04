import type { SavedView } from '@/service/api/saved-views';
import { type GroupByKey, isGroupByKey } from './groupIssuesBy';
import {
  type IssueDisplayFields,
  type SwimlaneBy,
  defaultIssueDisplay,
  isSwimlaneByKey,
  normalizeIssueDisplay
} from './display-prefs';

export interface DerivedListStateFromSavedView {
  filters: {
    status?: Api.Issue.IssueStatus;
    type?: Api.Issue.IssueType;
    priority?: Api.Issue.IssuePriority;
    project_id?: string;
    cycle_id?: string;
    search: string;
  };
  tab?: 'my_issues' | 'open' | 'closed' | 'all';
  viewMode?: 'list' | 'board';
  groupBy: GroupByKey;
  swimlaneBy: SwimlaneBy;
  hideEmptyLanes: boolean;
  fields: IssueDisplayFields;
  activeSavedViewId: string;
}

type ListTab = DerivedListStateFromSavedView['tab'];

function pickFilters(f: Record<string, unknown>): DerivedListStateFromSavedView['filters'] {
  return {
    type: (f.type as Api.Issue.IssueType | undefined) || undefined,
    priority: (f.priority as Api.Issue.IssuePriority | undefined) || undefined,
    project_id: (f.project_id as string | undefined) || undefined,
    cycle_id: (f.cycle_id as string | undefined) || undefined,
    status: (f.status as Api.Issue.IssueStatus | undefined) || undefined,
    search: (f.search as string | undefined) || ''
  };
}

function inferTab(explicit: unknown, status?: Api.Issue.IssueStatus): ListTab {
  if (explicit === 'my_issues' || explicit === 'open' || explicit === 'closed' || explicit === 'all') {
    return explicit;
  }
  if (!status) return undefined;
  const openStatuses: Api.Issue.IssueStatus[] = ['open', 'in_progress', 'feedback'];
  const closedStatuses: Api.Issue.IssueStatus[] = ['closed', 'rejected', 'resolved'];
  if (openStatuses.includes(status)) return 'open';
  if (closedStatuses.includes(status)) return 'closed';
  return undefined;
}

function pickViewMode(display: SavedView['display']): 'list' | 'board' | undefined {
  if (display?.view_mode === 'board' || display?.view_mode === 'list') {
    return display.view_mode;
  }
  return undefined;
}

function pickGroupBy(display: SavedView['display']): GroupByKey {
  return isGroupByKey(display?.group_by) ? (display!.group_by as GroupByKey) : 'none';
}

function pickSwimlane(display: SavedView['display'], fallback: SwimlaneBy): SwimlaneBy {
  return isSwimlaneByKey(display?.swimlane_by) ? (display!.swimlane_by as SwimlaneBy) : fallback;
}

function pickHideEmpty(display: SavedView['display'], fallback: boolean): boolean {
  if (display && 'hide_empty_lanes' in display) {
    return Boolean(display.hide_empty_lanes);
  }
  return fallback;
}

function pickFields(display: SavedView['display'], normalized: IssueDisplayFields): IssueDisplayFields {
  if (display?.fields && typeof display.fields === 'object') {
    return normalized;
  }
  return defaultIssueDisplay().fields;
}

export function deriveListStateFromSavedView(view: SavedView): DerivedListStateFromSavedView {
  const f = view.filter || {};
  const filters = pickFilters(f as Record<string, unknown>);
  const tab = inferTab(f.tab, filters.status);
  const normalized = normalizeIssueDisplay(view.display || null);

  return {
    filters,
    tab,
    viewMode: pickViewMode(view.display),
    groupBy: pickGroupBy(view.display),
    swimlaneBy: pickSwimlane(view.display, normalized.swimlaneBy),
    hideEmptyLanes: pickHideEmpty(view.display, normalized.hideEmptyLanes),
    fields: pickFields(view.display, normalized.fields),
    activeSavedViewId: view.id
  };
}
