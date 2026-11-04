import type { SavedView } from '@/service/api/saved-views';
import { type GroupByKey, isGroupByKey } from './groupIssuesBy';

export interface DerivedListStateFromSavedView {
  filters: {
    status?: Api.Issue.IssueStatus;
    type?: Api.Issue.IssueType;
    priority?: Api.Issue.IssuePriority;
    project_id?: string;
    search: string;
  };
  tab?: 'my_issues' | 'open' | 'closed' | 'all';
  viewMode?: 'list' | 'board';
  groupBy: GroupByKey;
  activeSavedViewId: string;
}

export function deriveListStateFromSavedView(view: SavedView): DerivedListStateFromSavedView {
  const f = view.filter || {};
  const filters = {
    type: (f.type as Api.Issue.IssueType | undefined) || undefined,
    priority: (f.priority as Api.Issue.IssuePriority | undefined) || undefined,
    project_id: (f.project_id as string | undefined) || undefined,
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

  let viewMode: 'list' | 'board' | undefined;
  if (view.display?.view_mode === 'board' || view.display?.view_mode === 'list') {
    viewMode = view.display.view_mode;
  }

  const groupBy: GroupByKey = isGroupByKey(view.display?.group_by) ? view.display.group_by : 'none';

  return { filters, tab, viewMode, groupBy, activeSavedViewId: view.id };
}
