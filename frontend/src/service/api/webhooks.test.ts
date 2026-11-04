import { describe, expect, it } from 'vitest';
import {
  applyIntegrationPreset,
  clearIntegrationPreset,
  filterDeliveriesByEvent,
  INTEGRATION_PRESET_EVENTS,
  isDeliveryReplayable,
  parseWebhookEvents,
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
    expect(WEBHOOK_EVENT_LABELS['issue.cycle_changed']).toBe('Cycle 变更');
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
