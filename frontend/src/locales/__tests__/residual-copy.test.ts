import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { IssueTypeEnum } from '@/constants/issue';
import { SLA_METRICS } from '@/service/api/sla';
import { labelTable, labeledOptions, lookupLabel } from '../display-label';
import en from '../langs/en-us';
import zh from '../langs/zh-cn';

describe('residual copy catalog', () => {
  it('fixes the initiative verb and keeps the customer request verb', () => {
    expect(zh.page.shell.createInitiative).toBe('新建举措');
    expect(en.page.shell.createInitiative).toBe('New initiative');
    expect(zh.page.shell.createRequest).toBe('新建需求');
    const zhSource = readFileSync(resolve('src/locales/langs/zh-cn.ts'), 'utf8');
    expect(zhSource).not.toContain('新建议措');
  });

  it('translates labels without changing enum values', () => {
    expect(IssueTypeEnum.Bug).toBe('bug');
    expect(zh.page.issueType.bug).toBe('缺陷');
    expect(en.page.issueType.bug).toBe('Bug');
    expect(zh.page.issueType.feature).toBe('功能');
    expect(en.page.issueType.question).toBe('Question');
    expect(SLA_METRICS).toEqual(['time_in_status', 'first_response']);
    expect(zh.page.sla.metric.time_in_status).toBe('状态停留');
    expect(en.page.sla.metric.time_in_status).toBe('Time in status');
    expect(zh.page.issueStatus.in_progress).toBe('进行中');
    expect(en.page.issueStatus.in_progress).toBe('In progress');
    expect(zh.page.sla.exception.forced_open).toBe('强制营业');
    expect(zh.page.sla.defaultPolicyName).toBe('进行中停留');
    expect(en.page.sla.defaultPolicyName).toBe('Time in progress');
  });

  it('keeps protocol words and removes raw enums from the Chinese explanation', () => {
    expect(zh.page.sla.help).toContain('POST /api/sla/run-due');
    expect(zh.page.sla.help).toContain('cron');
    expect(zh.page.sla.help).not.toContain('time_in_status');
    expect(zh.page.sla.help).not.toContain('in_progress');
    expect(zh.page.sla.help).not.toContain('resolved/closed');
    expect(en.page.sla.help).toContain('POST /api/sla/run-due');
    expect(en.page.sla.help).not.toMatch(/状态停留/);
    expect(zh.page.insights.subtitle).not.toMatch(/\bOR\b/);
    expect(zh.page.insights.subtitle).not.toMatch(/digest/i);
    expect(zh.page.insights.exportCsv).toContain('CSV');
    expect(en.page.insights.exportCsv).toBe('Export CSV');
  });
});

describe('lookupLabel', () => {
  const table = labelTable({ bug: '缺陷', toString: '自有' });

  it('returns the own label and otherwise the original value', () => {
    expect(lookupLabel(table, 'bug')).toBe('缺陷');
    expect(lookupLabel(table, 'custom')).toBe('custom');
    expect(lookupLabel(table, null)).toBe('');
    expect(lookupLabel(undefined, 'bug')).toBe('bug');
    expect(labeledOptions(['bug', 'custom'] as const, table)).toEqual([
      { value: 'bug', label: '缺陷' },
      { value: 'custom', label: 'custom' }
    ]);
  });

  it('does not read inherited names unless they are own properties', () => {
    const inherited = Object.create({ toString: '继承', constructor: '继承' });
    expect(lookupLabel(inherited, 'toString')).toBe('toString');
    expect(lookupLabel(inherited, '__proto__')).toBe('__proto__');
    expect(lookupLabel(inherited, 'constructor')).toBe('constructor');
    expect(lookupLabel(table, 'toString')).toBe('自有');
    expect(lookupLabel(table, '__proto__')).toBe('__proto__');
  });
});
