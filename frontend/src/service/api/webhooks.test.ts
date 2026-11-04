import { describe, expect, it } from 'vitest';
import { parseWebhookEvents, WEBHOOK_EVENTS } from './webhooks';

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

  it('WEBHOOK_EVENTS covers required set', () => {
    expect(WEBHOOK_EVENTS).toContain('issue.created');
    expect(WEBHOOK_EVENTS).toContain('comment.created');
  });
});
