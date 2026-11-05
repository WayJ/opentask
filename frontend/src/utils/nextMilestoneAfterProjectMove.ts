/** E80: local milestone after Issue project change (Q1a). */

export function nextMilestoneAfterProjectMove(
  oldProjectId: string | null | undefined,
  newProjectId: string | null | undefined,
  milestoneId: string | null | undefined
): string | null {
  const a = oldProjectId ?? null;
  const b = newProjectId ?? null;
  if (a === b) return milestoneId ?? null;
  return null;
}

export function projectMoveClearedMessage(
  oldProjectId: string | null | undefined,
  newProjectId: string | null | undefined,
  hadMilestone: boolean
): string | null {
  if (!hadMilestone) return null;
  if ((oldProjectId ?? null) === (newProjectId ?? null)) return null;
  return '已清除原项目里程碑';
}
