import { request } from '../request';
import type { SavedViewDisplay } from './saved-views';

export interface IssueDisplayPrefsResult {
  display: SavedViewDisplay | null;
}

export function fetchIssueDisplayPrefs() {
  return request<IssueDisplayPrefsResult>({
    url: '/api/display-prefs/issue',
    method: 'get'
  });
}

export function fetchPutIssueDisplayPrefs(display: SavedViewDisplay) {
  return request<IssueDisplayPrefsResult>({
    url: '/api/display-prefs/issue',
    method: 'put',
    data: { display }
  });
}
