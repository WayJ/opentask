import type { SavedView } from '@/service/api/saved-views';
import type { CycleItem } from '@/service/api/cycles';
import type { PaletteItem } from './command-palette';

const ISSUE_CODE_RE = /^[A-Za-z][A-Za-z0-9]*-\d+$/;

export function looksLikeIssueCode(query: string): boolean {
  return ISSUE_CODE_RE.test(query.trim());
}

export function resolveIssueSearchPlan(query: string): {
  search: string;
  fetchByCode: boolean;
  code?: string;
} {
  const search = query.trim();
  if (looksLikeIssueCode(search)) {
    return { search, fetchByCode: true, code: search };
  }
  return { search, fetchByCode: false };
}

export type NavigateTo = (to: string | { path: string; query?: Record<string, string> }) => void;

export function issuesToPaletteItems(issues: Api.Issue.Issue[], navigate: NavigateTo): PaletteItem[] {
  return issues.map(issue => ({
    id: `issue.${issue.id}`,
    kind: 'issue' as const,
    title: issue.title,
    subtitle: issue.issue_code,
    keywords: [issue.issue_code, issue.title],
    run: () => navigate({ path: '/issue/detail', query: { id: issue.id } })
  }));
}

export function projectsToPaletteItems(projects: Api.Project.Project[], navigate: NavigateTo): PaletteItem[] {
  return projects.map(p => ({
    id: `project.${p.id}`,
    kind: 'project' as const,
    title: p.name,
    keywords: [p.name],
    run: () => navigate({ path: '/workflow/project-detail', query: { id: p.id } })
  }));
}

export function savedViewsToPaletteItems(views: SavedView[], applyView: (id: string) => void): PaletteItem[] {
  return views.map(v => ({
    id: `view.${v.id}`,
    kind: 'saved_view' as const,
    title: v.name,
    subtitle: v.isFavorite ? '★' : undefined,
    keywords: [v.name],
    run: () => applyView(v.id)
  }));
}

export function filterByNameQuery<T extends { name: string }>(items: T[], query: string): T[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  return items.filter(i => i.name.toLowerCase().includes(q));
}

/** Merge issue lists by id, preferring earlier entries. */
export function mergeIssuesById(...lists: Api.Issue.Issue[][]): Api.Issue.Issue[] {
  const seen = new Set<string>();
  const out: Api.Issue.Issue[] = [];
  for (const list of lists) {
    for (const issue of list) {
      if (!seen.has(issue.id)) {
        seen.add(issue.id);
        out.push(issue);
      }
    }
  }
  return out;
}

export function cyclesToPaletteItems(cycles: CycleItem[], navigate: NavigateTo): PaletteItem[] {
  return cycles.map(c => ({
    id: `cycle.${c.id}`,
    kind: 'cycle' as const,
    title: c.name,
    subtitle: c.status,
    keywords: [c.name, c.status, 'cycle'],
    run: () => navigate({ path: '/issue/list', query: { cycle_id: c.id } })
  }));
}
