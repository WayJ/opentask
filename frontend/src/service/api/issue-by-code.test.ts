import { describe, expect, it } from 'vitest';
import { buildIssueDetailParams } from './issue';

describe('buildIssueDetailParams', () => {
  it('adds by_code when byCode true', () => {
    expect(buildIssueDetailParams({ byCode: true })).toEqual({ by_code: true });
  });
  it('returns undefined without byCode', () => {
    expect(buildIssueDetailParams()).toBeUndefined();
    expect(buildIssueDetailParams({})).toBeUndefined();
    expect(buildIssueDetailParams({ byCode: false })).toBeUndefined();
  });
});
