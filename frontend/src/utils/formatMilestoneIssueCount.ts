/** E81: display issue_count for project milestones table. */
export function formatMilestoneIssueCount(n: number | null | undefined): string {
  const v = typeof n === 'number' && Number.isFinite(n) && n >= 0 ? Math.floor(n) : 0;
  return String(v);
}

/** E81: delete confirm copy; mention occupancy when count > 0. */
export function milestoneDeleteConfirmText(issueCount: number | null | undefined): string {
  const n = typeof issueCount === 'number' && issueCount > 0 ? Math.floor(issueCount) : 0;
  if (n > 0) {
    return `确定删除此里程碑吗？将清空 ${n} 个 Issue 的里程碑引用。`;
  }
  return '确定删除此里程碑吗?';
}
