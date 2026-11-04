/** Canonical Issue detail location used by list/board/palette (query id, not path segment). */
export function buildIssueDetailLocation(id: string): { path: string; query: { id: string } } {
  return { path: '/issue/detail', query: { id } };
}
