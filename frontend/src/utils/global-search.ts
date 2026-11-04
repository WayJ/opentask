/** Pure helpers for Linear-style global Search page (E17/E60). */

export type SearchGroupId = 'issues' | 'projects' | 'docs' | 'members';

export interface SearchFlatItem {
  id: string;
  group: SearchGroupId;
  title: string;
  subtitle?: string;
  href: string | { path: string; query?: Record<string, string> };
  rank?: number;
}

export interface SearchGroupsInput {
  issues: Array<{
    id: string;
    issueCode: string;
    title: string;
    status?: string;
    rank?: number;
    snippet?: string;
  }>;
  projects: Array<{
    id: string;
    name: string;
    description?: string;
    rank?: number;
    snippet?: string;
  }>;
  docs: Array<{
    id: string;
    title: string;
    parentType: string;
    parentId: string;
    snippet?: string;
    rank?: number;
  }>;
  members: Array<{ userId: string; name?: string | null; username?: string | null; role: string }>;
}

const SNIPPET_MAX = 120;

function clipSnippet(s?: string): string | undefined {
  if (!s) return undefined;
  const clipped = s.trim().replace(/\n/g, ' ').slice(0, SNIPPET_MAX);
  return clipped || undefined;
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

/**
 * Flatten API groups. Missing rank is fine (E17 clients).
 * Within each group, prefer API order (already rank DESC); do not require rank.
 */
export function flattenSearchResults(data: SearchGroupsInput): SearchFlatItem[] {
  const out: SearchFlatItem[] = [];
  for (const i of data.issues || []) {
    const snip = clipSnippet(i.snippet);
    out.push({
      id: `issue:${i.id}`,
      group: 'issues',
      title: i.title,
      subtitle: [i.issueCode, i.status, snip].filter(Boolean).join(' · '),
      href: { path: '/issue/detail', query: { id: i.id } },
      rank: i.rank
    });
  }
  for (const p of data.projects || []) {
    const snip = clipSnippet(p.snippet) || p.description || undefined;
    out.push({
      id: `project:${p.id}`,
      group: 'projects',
      title: p.name,
      subtitle: snip,
      href: { path: '/workflow/project-detail', query: { id: p.id } },
      rank: p.rank
    });
  }
  for (const d of data.docs || []) {
    const snip = clipSnippet(d.snippet);
    out.push({
      id: `doc:${d.id}`,
      group: 'docs',
      title: d.title,
      subtitle: `${d.parentType}/${d.parentId}${snip ? ` · ${snip}` : ''}`,
      href: buildDocHref(d.parentType, d.parentId, d.id),
      rank: d.rank
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
