import { describe, expect, it } from 'vitest';
import { isIssueCodeToken, parseSearchString, parsedQueryToFilters } from './issueSearchParser';

describe('parseSearchString E21', () => {
  it('parses assignee:@me and assignee:me as me', () => {
    expect(parseSearchString('assignee:@me').assignee_id).toBe('me');
    expect(parseSearchString('assignee:me').assignee_id).toBe('me');
  });

  it('parses is:open / priority / type / cycle / project', () => {
    const q = parseSearchString('is:open priority:high type:bug cycle:abc project:p1');
    expect(q.status).toBe('open');
    expect(q.priority).toBe('high');
    expect(q.type).toBe('bug');
    expect(q.cycle_id).toBe('abc');
    expect(q.project_id).toBe('p1');
  });

  it('accumulates labels', () => {
    const q = parseSearchString('label:bug label:frontend');
    expect(q.labels).toEqual(['bug', 'frontend']);
  });

  it('keeps KEY-N in search', () => {
    const q = parseSearchString('SMK-12 login bug');
    expect(q.search).toContain('SMK-12');
    expect(q.search).toContain('login');
    expect(isIssueCodeToken('SMK-12')).toBe(true);
    expect(isIssueCodeToken('not-a-key')).toBe(false);
  });

  it('parsedQueryToFilters maps fields', () => {
    const f = parsedQueryToFilters(parseSearchString('assignee:@me is:open label:bug'));
    expect(f.assignee_id).toBe('me');
    expect(f.status).toBe('open');
    expect(f.labels).toEqual(['bug']);
  });
});
