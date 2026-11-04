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

export function deriveListStateFromSavedView(view: SavedView): DerivedListStateFromSavedView {
  const f = view.filter || {};
  const filters = {
    type: (f.type as Api.Issue.IssueType | undefined) || undefined,
    priority: (f.priority as Api.Issue.IssuePriority | undefined) || undefined,
    project_id: (f.project_id as string | undefined) || undefined,
    cycle_id: (f.cycle_id as string | undefined) || undefined,
    status: (f.status as Api.Issue.IssueStatus | undefined) || undefined,
    search: (f.search as string | undefined) || ''
  };

  let tab = (f.tab as DerivedListStateFromSavedView['tab'] | undefined) || undefined;
  if (!tab && filters.status) {
    const openStatuses: Api.Issue.IssueStatus[] = ['open', 'in_progress', 'feedback'];
    const closedStatuses: Api.Issue.IssueStatus[] = ['closed', 'rejected', 'resolved'];
    if (openStatuses.includes(filters.status)) tab = 'open';
    else if (closedStatuses.includes(filters.status)) tab = 'closed';
  }

  const normalized = normalizeIssueDisplay(view.display || null);

  let viewMode: 'list' | 'board' | undefined;
  if (view.display?.view_mode === 'board' || view.display?.view_mode === 'list') {
    viewMode = view.display.view_mode;
  }

  const groupBy: GroupByKey = isGroupByKey(view.display?.group_by)
    ? (view.display!.group_by as GroupByKey)
    : 'none';

  const swimlaneBy: SwimlaneBy = isSwimlaneByKey(view.display?.swimlane_by)
    ? (view.display!.swimlane_by as SwimlaneBy)
    : normalized.swimlaneBy;

  const hideEmptyLanes =
    view.display && 'hide_empty_lanes' in view.display
      ? Boolean(view.display.hide_empty_lanes)
      : normalized.hideEmptyLanes;

  const fields =
    view.display && view.display.fields && typeof view.display.fields === 'object'
      ? normalized.fields
      : defaultIssueDisplay().fields;

  return {
    filters,
    tab,
    viewMode,
    groupBy,
    swimlaneBy,
    hideEmptyLanes,
    fields,
    activeSavedViewId: view.id
  };
}
