import { describe, expect, it } from 'vitest';
import { buildIssueDetailLocation } from './issue-board-nav';

describe('buildIssueDetailLocation', () => {
  it('builds query-id location (not path segment)', () => {
    expect(buildIssueDetailLocation('abc-123')).toEqual({
      path: '/issue/detail',
      query: { id: 'abc-123' }
    });
  });
});
