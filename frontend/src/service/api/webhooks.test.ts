import { describe, expect, it } from 'vitest';
import {
  applyIntegrationPreset,
  clearIntegrationPreset,
  DEFAULT_STAT_WINDOW,
  filterDeadLetterRows,
  filterDeliveriesByEvent,
  formatSuccessRate,
  INTEGRATION_PRESET_EVENTS,
  isDeliveryReplayable,
  normalizeStatsPayload,
  mergeAlertSettings,
  normalizeAlertSettings,
  isMutedUntil,
  isAlertPending,
  isAutoDisabledWebhook,
  DEFAULT_ALERT_SETTINGS,
  parseWebhookEvents,
  STAT_WINDOWS,
  WEBHOOK_EVENTS,
  WEBHOOK_EVENT_LABELS
} from './webhooks';

describe('webhooks helpers', () => {
  it('parseWebhookEvents splits and dedupes', () => {
    expect(parseWebhookEvents('issue.created, issue.updated issue.created')).toEqual([
      'issue.created',
      'issue.updated'
    ]);
  });

  it('parseWebhookEvents rejects unknown', () => {
    expect(() => parseWebhookEvents('issue.created,bogus')).toThrow(/未知事件/);
  });

  it('WEBHOOK_EVENTS covers required set including E44', () => {
    expect(WEBHOOK_EVENTS).toContain('issue.created');
    expect(WEBHOOK_EVENTS).toContain('comment.created');
    expect(WEBHOOK_EVENTS).toContain('issue.custom_field_changed');
    expect(WEBHOOK_EVENTS).toContain('issue.assignee_changed');
    expect(WEBHOOK_EVENTS).toContain('issue.label_added');
    expect(WEBHOOK_EVENTS).toContain('issue.label_removed');
    expect(WEBHOOK_EVENT_LABELS['issue.assignee_changed']).toBe('经办人变更');
    expect(WEBHOOK_EVENT_LABELS['issue.label_added']).toBe('添加标签');
    expect(WEBHOOK_EVENT_LABELS['issue.label_removed']).toBe('移除标签');
  });

  it('WEBHOOK_EVENTS covers E51 pack with labels', () => {
    expect(WEBHOOK_EVENTS).toContain('issue.cycle_changed');
    expect(WEBHOOK_EVENTS).toContain('issue.estimate_changed');
    expect(WEBHOOK_EVENTS).toContain('issue.project_changed');
    expect(WEBHOOK_EVENTS).toContain('issue.sla_paused');
    expect(WEBHOOK_EVENTS).toContain('issue.sla_resumed');
    expect(WEBHOOK_EVENT_LABELS['issue.cycle_changed']).toBe('冲刺变更');
    expect(WEBHOOK_EVENT_LABELS['issue.estimate_changed']).toBe('估点变更');
    expect(WEBHOOK_EVENT_LABELS['issue.project_changed']).toBe('项目变更');
    expect(WEBHOOK_EVENT_LABELS['issue.sla_paused']).toBe('SLA 暂停');
    expect(WEBHOOK_EVENT_LABELS['issue.sla_resumed']).toBe('SLA 恢复');
  });

  it('INTEGRATION_PRESET_EVENTS is cycle/estimate/project/sla_*', () => {
    expect(INTEGRATION_PRESET_EVENTS).toEqual([
      'issue.cycle_changed',
      'issue.estimate_changed',
      'issue.project_changed',
      'issue.sla_paused',
      'issue.sla_resumed'
    ]);
  });

  it('applyIntegrationPreset unions and dedupes', () => {
    expect(applyIntegrationPreset(['issue.created'])).toEqual([
      'issue.created',
      ...INTEGRATION_PRESET_EVENTS
    ]);
    expect(applyIntegrationPreset(['issue.cycle_changed', 'issue.updated'])).toEqual([
      'issue.cycle_changed',
      'issue.updated',
      'issue.estimate_changed',
      'issue.project_changed',
      'issue.sla_paused',
      'issue.sla_resumed'
    ]);
  });

  it('clearIntegrationPreset removes preset set', () => {
    expect(
      clearIntegrationPreset(['issue.created', 'issue.cycle_changed', 'issue.sla_paused'])
    ).toEqual(['issue.created']);
  });

  it('filterDeliveriesByEvent filters or passes all', () => {
    const list = [
      { id: '1', webhookId: 'w', eventType: 'issue.updated', success: true, attempt: 1 },
      { id: '2', webhookId: 'w', eventType: 'issue.cycle_changed', success: true, attempt: 1 },
      { id: '3', webhookId: 'w', eventType: 'issue.updated', success: false, attempt: 1 }
    ];
    expect(filterDeliveriesByEvent(list, 'all')).toHaveLength(3);
    expect(filterDeliveriesByEvent(list, 'issue.updated').map(d => d.id)).toEqual(['1', '3']);
    expect(filterDeliveriesByEvent(list, 'issue.cycle_changed').map(d => d.id)).toEqual(['2']);
  });

  it('isDeliveryReplayable respects flag and status', () => {
    expect(
      isDeliveryReplayable({
        id: '1',
        webhookId: 'w',
        eventType: 'x',
        success: false,
        attempt: 1,
        replayable: true
      })
    ).toBe(true);
    expect(
      isDeliveryReplayable({
        id: '1',
        webhookId: 'w',
        eventType: 'x',
        success: true,
        attempt: 1,
        status: 'success',
        replayable: false
      })
    ).toBe(false);
    expect(
      isDeliveryReplayable({
        id: '1',
        webhookId: 'w',
        eventType: 'x',
        success: false,
        attempt: 5,
        status: 'dead'
      })
    ).toBe(true);
  });
});

describe('E54 webhook observability helpers', () => {
  it('STAT_WINDOWS default 7d', () => {
    expect(STAT_WINDOWS).toEqual(['24h', '7d', '30d']);
    expect(DEFAULT_STAT_WINDOW).toBe('7d');
  });

  it('normalizeStatsPayload fills totals and latency', () => {
    const n = normalizeStatsPayload({
      window: '24h',
      totals: {
        success: 8,
        pending_retry: 1,
        dead: 1,
        attempts: 10,
        successRate: 0.8,
        latencyMs: { p50: 100, p95: 400 }
      },
      byWebhook: [
        {
          webhookId: 'w1',
          name: 'A',
          totals: { success: 8, pending_retry: 1, dead: 1, attempts: 10, successRate: 0.8 }
        }
      ]
    });
    expect(n.window).toBe('24h');
    expect(n.totals.successRate).toBe(0.8);
    expect(n.totals.latencyMs?.p50).toBe(100);
    expect(n.byWebhook?.[0].webhookId).toBe('w1');
  });

  it('normalizeStatsPayload falls back window and null rate', () => {
    const n = normalizeStatsPayload({ window: '1h', totals: { successRate: null } });
    expect(n.window).toBe('7d');
    expect(n.totals.successRate).toBeNull();
    expect(n.totals.latencyMs).toBeUndefined();
  });

  it('filterDeadLetterRows by hook and event', () => {
    const rows = [
      { id: '1', webhookId: 'a', eventType: 'issue.created' },
      { id: '2', webhookId: 'b', eventType: 'issue.created' },
      { id: '3', webhookId: 'a', eventType: 'issue.updated' }
    ];
    expect(filterDeadLetterRows(rows, 'all', 'all')).toHaveLength(3);
    expect(filterDeadLetterRows(rows, 'a', 'all').map(r => r.id)).toEqual(['1', '3']);
    expect(filterDeadLetterRows(rows, 'a', 'issue.created').map(r => r.id)).toEqual(['1']);
  });

  it('formatSuccessRate', () => {
    expect(formatSuccessRate(0.8)).toBe('80.0%');
    expect(formatSuccessRate(null)).toBe('—');
  });
});



describe('E57 alert settings helpers', () => {
  it('normalize defaults opt-in off', () => {
    const n = normalizeAlertSettings(null);
    expect(n.enabled).toBe(false);
    expect(n.windowHours).toBe(24);
    expect(n).toMatchObject(DEFAULT_ALERT_SETTINGS);
  });

  it('merge inherits and overlays fields', () => {
    const ws = normalizeAlertSettings({ enabled: true, deadThreshold: 10 });
    const m = mergeAlertSettings(ws, { deadThreshold: 3 });
    expect(m.enabled).toBe(true);
    expect(m.deadThreshold).toBe(3);
    expect(m.windowHours).toBe(24);
    const inherit = mergeAlertSettings(ws, null);
    expect(inherit.deadThreshold).toBe(10);
    const empty = mergeAlertSettings(ws, {});
    expect(empty.deadThreshold).toBe(10);
  });

  it('mute suppresses pending alert state', () => {
    const now = new Date('2026-11-05T12:00:00Z');
    expect(isMutedUntil(new Date(now.getTime() + 3600_000).toISOString(), now)).toBe(true);
    expect(isMutedUntil(new Date(now.getTime() - 3600_000).toISOString(), now)).toBe(false);
    const muted = normalizeAlertSettings({
      enabled: true,
      muteUntil: new Date(now.getTime() + 3600_000).toISOString()
    });
    expect(isAlertPending(muted, now)).toBe(false);
    expect(isAlertPending(normalizeAlertSettings({ enabled: true, muteUntil: null }), now)).toBe(true);
    expect(isAlertPending(normalizeAlertSettings({ enabled: false }), now)).toBe(false);
  });

  it('auto-disabled badge helper', () => {
    expect(isAutoDisabledWebhook({ enabled: false, pausedReason: 'auto_dead_letter_alert' })).toBe(true);
    expect(isAutoDisabledWebhook({ enabled: true, pausedReason: 'auto_dead_letter_alert' })).toBe(false);
    expect(isAutoDisabledWebhook({ enabled: false, pausedReason: null })).toBe(false);
  });
});
