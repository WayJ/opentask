/** Project Timeline helpers (E8-S2) */

export type HealthStatus = 'on_track' | 'at_risk' | 'off_track';

export const HEALTH_LABELS: Record<HealthStatus, string> = {
  on_track: '进展顺利',
  at_risk: '存在风险',
  off_track: '偏离计划'
};

export const HEALTH_TAG_TYPE: Record<HealthStatus, 'success' | 'warning' | 'error'> = {
  on_track: 'success',
  at_risk: 'warning',
  off_track: 'error'
};

export type TimelineZoom = 'week' | 'month';

export interface TimelineProjectLike {
  starts_at?: string | null;
  target_date?: string | null;
}

export interface TimelineMilestoneLike {
  id: string;
  target_date?: string | null;
}

export interface TimelineIssueLike {
  id: string;
  due_date?: string | null;
}

/** Empty when no project dates and no milestones (and no due issues). */
export function isTimelineEmpty(
  project: TimelineProjectLike | null | undefined,
  milestones: TimelineMilestoneLike[] = [],
  issues: TimelineIssueLike[] = []
): boolean {
  const hasProjectDates = Boolean(project?.starts_at || project?.target_date);
  const hasMilestones = milestones.length > 0;
  const hasDueIssues = issues.some(i => Boolean(i.due_date));
  return !hasProjectDates && !hasMilestones && !hasDueIssues;
}

/** Day width in px for zoom level (MVP fixed). */
export function timelineDayWidth(zoom: TimelineZoom): number {
  return zoom === 'week' ? 28 : 10;
}

export function parseDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** Inclusive day span for timeline range, with padding. */
export function computeTimelineRange(
  project: TimelineProjectLike | null | undefined,
  items: { milestones?: TimelineMilestoneLike[]; issues?: TimelineIssueLike[]; padDays?: number } = {}
): { start: Date; end: Date } | null {
  const milestones = items.milestones || [];
  const issues = items.issues || [];
  const padDays = items.padDays ?? 3;
  const dates: Date[] = [];
  const a = parseDate(project?.starts_at);
  const b = parseDate(project?.target_date);
  if (a) dates.push(a);
  if (b) dates.push(b);
  for (const m of milestones) {
    const d = parseDate(m.target_date);
    if (d) dates.push(d);
  }
  for (const i of issues) {
    const d = parseDate(i.due_date);
    if (d) dates.push(d);
  }
  if (dates.length === 0) return null;
  const min = new Date(Math.min(...dates.map(d => d.getTime())));
  const max = new Date(Math.max(...dates.map(d => d.getTime())));
  min.setDate(min.getDate() - padDays);
  max.setDate(max.getDate() + padDays);
  return { start: min, end: max };
}

export function offsetDays(from: Date, to: Date): number {
  const ms = to.getTime() - from.getTime();
  return Math.round(ms / (24 * 60 * 60 * 1000));
}
