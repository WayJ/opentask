import { describe, expect, it } from 'vitest';
import {
  customFieldsToCfParams,
  isIssueCodeToken,
  parseSearchString,
  parsedQueryToFilters
} from './issueSearchParser';

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

describe('parseSearchString E32 custom fields', () => {
  it('parses field:key:value and cf:key:value', () => {
    const q = parseSearchString('field:severity:s1 is:open');
    expect(q.custom_fields).toEqual([{ key: 'severity', value: 's1' }]);
    expect(q.status).toBe('open');
    const q2 = parseSearchString('cf:stack:fe cf:shipped:true');
    expect(q2.custom_fields).toEqual([
      { key: 'stack', value: 'fe' },
      { key: 'shipped', value: 'true' }
    ]);
  });

  it('maps custom_fields via parsedQueryToFilters and cf params', () => {
    const f = parsedQueryToFilters(parseSearchString('field:severity:s1'));
    expect(f.custom_fields).toEqual([{ key: 'severity', value: 's1' }]);
    expect(customFieldsToCfParams(f.custom_fields)).toEqual({ 'cf.severity': 's1' });
  });
});


describe('E46 SmartSearch range ops', () => {
  it('parses cf:score>=8', () => {
    const q = parseSearchString('cf:score>=8');
    expect(q.custom_fields).toEqual([{ key: 'score', value: '8', op: 'gte' }]);
    expect(customFieldsToCfParams(q.custom_fields)).toEqual({ 'cf.score[gte]': '8' });
  });
});
