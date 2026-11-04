/** Sidebar Favorites helpers (E8-S3) — distinct from Saved View is_favorite */

export type FavoriteTargetType = 'project' | 'saved_view' | 'issue' | 'initiative';

export interface FavoriteLike {
  id: string;
  targetType: string;
  targetId: string;
  position: number;
  target?: { id: string; type: string; name: string; code?: string | null };
}

export function sortFavoritesByPosition<T extends { position: number }>(rows: T[]): T[] {
  return [...rows].sort((a, b) => a.position - b.position);
}

export function groupFavoritesByType<T extends { targetType: string }>(rows: T[]): Record<FavoriteTargetType, T[]> {
  const out: Record<FavoriteTargetType, T[]> = {
    project: [],
    saved_view: [],
    issue: [],
    initiative: []
  };
  for (const row of rows) {
    if (
      row.targetType === 'project' ||
      row.targetType === 'saved_view' ||
      row.targetType === 'issue' ||
      row.targetType === 'initiative'
    ) {
      out[row.targetType].push(row);
    }
  }
  return out;
}

export function findFavoriteId(rows: FavoriteLike[], targetType: FavoriteTargetType, targetId: string): string | null {
  const hit = rows.find(r => r.targetType === targetType && r.targetId === targetId);
  return hit?.id ?? null;
}

/** Navigation target for a favorite row (router.push arg). */
export function favoriteNavTarget(fav: FavoriteLike): { path: string; query?: Record<string, string> } {
  const type = fav.targetType;
  const id = fav.targetId;
  if (type === 'project') {
    return { path: '/workflow/project-detail', query: { id } };
  }
  if (type === 'issue') {
    return { path: '/issue/detail', query: { id } };
  }
  if (type === 'initiative') {
    return { path: '/initiatives/detail', query: { id } };
  }
  // saved_view → issue list with view query
  return { path: '/issue/list', query: { view: id } };
}

export function favoriteLabel(fav: FavoriteLike): string {
  const name = fav.target?.name?.trim();
  if (name) return name;
  if (fav.target?.code) return fav.target.code;
  return fav.targetId.slice(0, 8);
}

export const FAVORITE_TYPE_LABEL: Record<FavoriteTargetType, string> = {
  project: '项目',
  saved_view: '视图',
  issue: 'Issue',
  initiative: 'Initiative'
};
