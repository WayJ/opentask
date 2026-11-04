import { request } from '../request';

export interface SavedViewFilter {
  status?: string;
  type?: string;
  priority?: string;
  project_id?: string;
  cycle_id?: string;
  assignee_id?: string;
  reporter_id?: string;
  search?: string;
  tab?: string;
  [key: string]: unknown;
}

export interface SavedViewSort {
  sort_by?: string;
  sort_order?: 'asc' | 'desc' | string;
}

export interface SavedViewDisplay {
  view_mode?: string;
  group_by?: string;
  swimlane_by?: string;
  hide_empty_lanes?: boolean;
  fields?: Record<string, boolean>;
  [key: string]: unknown;
}

export interface SavedView {
  id: string;
  workspaceId: string;
  ownerUserId: string;
  name: string;
  isFavorite: boolean;
  isShared: boolean;
  filter: SavedViewFilter;
  sort?: SavedViewSort | null;
  display?: SavedViewDisplay | null;
  createdAt: string;
  updatedAt: string;
}

export interface SavedViewListResult {
  personal: SavedView[];
  shared: SavedView[];
  rows: SavedView[];
  total: number;
}

export function fetchSavedViews() {
  return request<SavedViewListResult>({
    url: '/api/saved-views',
    method: 'get'
  });
}

export function fetchCreateSavedView(body: {
  name: string;
  filter: SavedViewFilter;
  sort?: SavedViewSort | null;
  display?: SavedViewDisplay | null;
  is_favorite?: boolean;
  is_shared?: boolean;
}) {
  return request<SavedView>({
    url: '/api/saved-views',
    method: 'post',
    data: body
  });
}

export function fetchUpdateSavedView(
  id: string,
  body: {
    name?: string;
    filter?: SavedViewFilter;
    sort?: SavedViewSort | null;
    display?: SavedViewDisplay | null;
    is_favorite?: boolean;
    is_shared?: boolean;
  }
) {
  return request<SavedView>({
    url: `/api/saved-views/${id}`,
    method: 'patch',
    data: body
  });
}

export function fetchDeleteSavedView(id: string) {
  return request<{ id: string }>({
    url: `/api/saved-views/${id}`,
    method: 'delete'
  });
}

export function fetchSetSavedViewFavorite(id: string, isFavorite: boolean) {
  return request<SavedView>({
    url: `/api/saved-views/${id}/favorite`,
    method: 'post',
    data: { is_favorite: isFavorite }
  });
}

export function fetchSaveAsSavedView(id: string, name?: string) {
  return request<SavedView>({
    url: `/api/saved-views/${id}/save-as`,
    method: 'post',
    data: name ? { name } : {}
  });
}
