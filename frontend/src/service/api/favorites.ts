import { request } from '../request';

export type FavoriteTargetType = 'project' | 'saved_view' | 'issue' | 'initiative';

export interface FavoriteTarget {
  id: string;
  type: FavoriteTargetType | string;
  name: string;
  code?: string | null;
}

export interface FavoriteItem {
  id: string;
  workspaceId: string;
  userId: string;
  targetType: FavoriteTargetType | string;
  targetId: string;
  position: number;
  createdAt: string;
  target: FavoriteTarget;
}

export interface FavoriteListResult {
  rows: FavoriteItem[];
  total: number;
}

export function fetchFavorites() {
  return request<FavoriteListResult>({
    url: '/api/favorites',
    method: 'get'
  });
}

export function fetchAddFavorite(body: { target_type: FavoriteTargetType; target_id: string }) {
  return request<FavoriteItem>({
    url: '/api/favorites',
    method: 'post',
    data: body
  });
}

export function fetchRemoveFavorite(id: string) {
  return request<{ id: string }>({
    url: `/api/favorites/${id}`,
    method: 'delete'
  });
}

export function fetchReorderFavorites(ordered_ids: string[]) {
  return request<FavoriteListResult>({
    url: '/api/favorites/reorder',
    method: 'put',
    data: { ordered_ids }
  });
}
