import { describe, expect, it } from 'vitest';
import { buildIssueExportParams, formatIssueImportSummary } from './issue';

describe('issue csv helpers (E28)', () => {
  it('buildIssueExportParams drops empties', () => {
    expect(buildIssueExportParams({ status: 'open', search: '', foo: 1 })).toEqual({ status: 'open' });
    expect(buildIssueExportParams({ assignee_id: 'me', cycle_id: '__none__' })).toEqual({
      assignee_id: 'me',
      cycle_id: '__none__'
    });
  });

  it('formatIssueImportSummary', () => {
    expect(formatIssueImportSummary({ created: 1, updated: 2, errors: [] })).toBe('创建 1 · 更新 2');
    expect(
      formatIssueImportSummary({
        created: 0,
        updated: 0,
        errors: [{ row: 2, message: 'title 必填' }]
      })
    ).toContain('错误 1');
  });
  it('import summary surfaces cf errors (E34)', () => {
    expect(
      formatIssueImportSummary({
        created: 1,
        updated: 0,
        errors: [{ row: 2, message: 'cf.unknown: 未知自定义字段' }]
      })
    ).toContain('cf.unknown');
  });
});
