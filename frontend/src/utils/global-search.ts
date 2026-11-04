/** Pure helpers for Linear-style global Search page (E17). */

export type SearchGroupId = 'issues' | 'projects' | 'docs' | 'members';

export interface SearchFlatItem {
  id: string;
  group: SearchGroupId;
  title: string;
  subtitle?: string;
  href: string | { path: string; query?: Record<string, string> };
}

export interface SearchGroupsInput {
  issues: Array<{ id: string; issueCode: string; title: string; status?: string }>;
  projects: Array<{ id: string; name: string; description?: string }>;
  docs: Array<{ id: string; title: string; parentType: string; parentId: string; snippet?: string }>;
  members: Array<{ userId: string; name?: string | null; username?: string | null; role: string }>;
}

/** Deep-link a short EntityDocument to its parent page + open doc query. */
export function buildDocHref(
  parentType: string,
  parentId: string,
  docId: string
): { path: string; query: Record<string, string> } {
  const query = { id: parentId, doc: docId };
  switch (parentType) {
    case 'issue':
      return { path: '/issue/detail', query };
    case 'initiative':
      return { path: '/initiatives/detail', query };
    case 'project':
    default:
      return { path: '/workflow/project-detail', query };
  }
}

export function flattenSearchResults(data: SearchGroupsInput): SearchFlatItem[] {
  const out: SearchFlatItem[] = [];
  for (const i of data.issues || []) {
    out.push({
      id: `issue:${i.id}`,
      group: 'issues',
      title: i.title,
      subtitle: [i.issueCode, i.status].filter(Boolean).join(' · '),
      href: { path: '/issue/detail', query: { id: i.id } }
    });
  }
  for (const p of data.projects || []) {
    out.push({
      id: `project:${p.id}`,
      group: 'projects',
      title: p.name,
      subtitle: p.description || undefined,
      href: { path: '/workflow/project-detail', query: { id: p.id } }
    });
  }
  for (const d of data.docs || []) {
    out.push({
      id: `doc:${d.id}`,
      group: 'docs',
      title: d.title,
      subtitle: `${d.parentType}/${d.parentId}${d.snippet ? ` · ${d.snippet}` : ''}`,
      href: buildDocHref(d.parentType, d.parentId, d.id)
    });
  }
  for (const m of data.members || []) {
    const label = m.name || m.username || m.userId;
    out.push({
      id: `member:${m.userId}`,
      group: 'members',
      title: label,
      subtitle: m.role,
      href: { path: '/workspace/members' }
    });
  }
  return out;
}

export function moveActiveIndex(current: number, delta: number, length: number): number {
  if (length <= 0) return -1;
  if (current < 0) return delta > 0 ? 0 : length - 1;
  return (current + delta + length) % length;
}

export function buildSearchPagePath(q?: string): string | { path: string; query?: Record<string, string> } {
  const trimmed = (q || '').trim();
  if (!trimmed) return '/search';
  return { path: '/search', query: { q: trimmed } };
}
