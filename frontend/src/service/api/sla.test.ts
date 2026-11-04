import { describe, expect, it } from 'vitest';
import { formatSlaRemaining, slaBadgeType } from './sla';
import { WEBHOOK_EVENTS, WEBHOOK_EVENT_LABELS } from './webhooks';
import { NOTIF_PREF_KEYS, NOTIF_PREF_LABELS, mergeNotifPrefs } from './notif-prefs';

describe('formatSlaRemaining', () => {
  const now = Date.parse('2026-11-05T00:00:00Z');

  it('shows remaining minutes under an hour', () => {
    expect(formatSlaRemaining('2026-11-05T00:25:00Z', now)).toBe('剩余 25 分钟');
  });

  it('shows remaining hours', () => {
    expect(formatSlaRemaining('2026-11-05T02:00:00Z', now)).toBe('剩余 2h');
  });

  it('shows overdue', () => {
    expect(formatSlaRemaining('2026-11-04T23:00:00Z', now)).toBe('逾期 1h');
  });

  it('handles missing', () => {
    expect(formatSlaRemaining(null)).toBe('—');
  });
});

describe('slaBadgeType', () => {
  it('maps statuses', () => {
    expect(slaBadgeType('breached')).toBe('error');
    expect(slaBadgeType('met')).toBe('success');
    expect(slaBadgeType('running')).toBe('warning');
  });
});

describe('E42 constants', () => {
  it('webhook includes issue.sla_breached', () => {
    expect(WEBHOOK_EVENTS).toContain('issue.sla_breached');
    expect(WEBHOOK_EVENT_LABELS['issue.sla_breached']).toBe('SLA 违约');
  });

  it('notif prefs include sla_breached', () => {
    expect(NOTIF_PREF_KEYS).toContain('sla_breached');
    expect(NOTIF_PREF_LABELS.sla_breached).toBe('SLA 违约');
    expect(mergeNotifPrefs().sla_breached).toBe(true);
  });
});
