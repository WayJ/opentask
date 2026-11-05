import { describe, expect, it } from 'vitest';
import { buildIssueDetailParams } from './issue';

describe('buildIssueDetailParams', () => {
  it('adds by_code when byCode true', () => {
    expect(buildIssueDetailParams({ byCode: true })).toEqual({ by_code: true });
  });
  it('adds include_deleted when includeDeleted true', () => {
    expect(buildIssueDetailParams({ includeDeleted: true })).toEqual({ include_deleted: true });
    expect(buildIssueDetailParams({ byCode: true, includeDeleted: true })).toEqual({
      by_code: true,
      include_deleted: true
    });
  });
  it('returns undefined without flags', () => {
    expect(buildIssueDetailParams()).toBeUndefined();
    expect(buildIssueDetailParams({})).toBeUndefined();
    expect(buildIssueDetailParams({ byCode: false })).toBeUndefined();
  });
});
