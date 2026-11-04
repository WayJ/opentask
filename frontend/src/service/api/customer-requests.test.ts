import { describe, expect, it } from 'vitest';
import {
  buildPublicStatusPath,
  isPublicStatusCardRedacted
} from './customer-requests';

describe('customer-requests public status helpers (E63)', () => {
  it('buildPublicStatusPath normalizes token and path', () => {
    expect(buildPublicStatusPath('abc')).toBe('/r/abc');
    expect(buildPublicStatusPath('/r/abc')).toBe('/r/abc');
  });

  it('isPublicStatusCardRedacted rejects internal fields', () => {
    expect(
      isPublicStatusCardRedacted({
        title: 't',
        status: 'open',
        linkedIssueCount: 0,
        linkedIssueCodes: [],
        publicRepliesEnabled: false
      })
    ).toBe(true);
    expect(isPublicStatusCardRedacted({ title: 't', workspaceId: 'w' })).toBe(false);
    expect(isPublicStatusCardRedacted({ title: 't', body: 'secret' })).toBe(false);
  });
});
