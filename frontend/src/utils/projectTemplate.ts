/** E72: project template payload helpers (offset → date, validate). */

export const MAX_PROJECT_TEMPLATE_MILESTONES = 30;

export interface ProjectTemplateMilestoneDraft {
  name: string;
  description?: string | null;
  position?: number;
  targetOffsetDays?: number | null;
}

export function addDaysIso(
  baseIsoDate: string,
  offsetDays: number | null | undefined
): string | null {
  if (offsetDays === null || offsetDays === undefined) return null;
  const d = new Date(`${baseIsoDate.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return null;
  d.setUTCDate(d.getUTCDate() + Number(offsetDays));
  return d.toISOString().slice(0, 10);
}

export function validateMilestonePayload(
  milestones: Array<{ name?: string | null }>
): string | null {
  if (!Array.isArray(milestones)) return 'milestones must be a list';
  if (milestones.length > MAX_PROJECT_TEMPLATE_MILESTONES) {
    return `max ${MAX_PROJECT_TEMPLATE_MILESTONES} milestones`;
  }
  for (const m of milestones) {
    if (!String(m?.name || '').trim()) return 'milestone name required';
  }
  return null;
}

export function previewMilestones(
  milestones: ProjectTemplateMilestoneDraft[],
  baseIsoDate: string
): Array<{ name: string; targetDate: string | null }> {
  return (milestones || []).map(m => ({
    name: String(m.name || '').trim(),
    targetDate: addDaysIso(baseIsoDate, m.targetOffsetDays ?? null)
  }));
}
