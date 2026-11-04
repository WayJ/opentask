import { describe, expect, it } from 'vitest';
import {
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
