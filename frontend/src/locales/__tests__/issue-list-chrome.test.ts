import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';
import { describe, expect, it } from 'vitest';
import en from '../langs/en-us';
import zh from '../langs/zh-cn';

function keysOf(value: unknown, prefix = ''): string[] {
  if (!value || typeof value !== 'object') return [prefix];
  return Object.entries(value as Record<string, unknown>).flatMap(([key, child]) =>
    keysOf(child, prefix ? `${prefix}.${key}` : key)
  );
}

function schemaKeysOfIssueList(source: string): string[] {
  const match = /(?:^|[\n\r;{])\s*issueList\s*:/.exec(source);
  if (!match) return [];
  const start = source.indexOf('{', match.index + match[0].length);
  if (start < 0) return [];

  // The walker is the approved plan's schema reader. Keep its control flow.
  /* eslint-disable complexity, no-continue */
  function parseObject(from: number, prefix: string): { keys: string[]; end: number } {
    const keys: string[] = [];
    let i = from + 1;
    while (i < source.length) {
      while (i < source.length && /[\s,;]/.test(source[i])) i += 1;
      if (source[i] === '}') return { keys, end: i + 1 };
      if (source.startsWith('//', i)) {
        const nl = source.indexOf('\n', i);
        i = nl < 0 ? source.length : nl + 1;
        continue;
      }
      if (source.startsWith('/*', i)) {
        const endC = source.indexOf('*/', i + 2);
        i = endC < 0 ? source.length : endC + 2;
        continue;
      }
      const keyMatch = /^[A-Za-z_][A-Za-z0-9_]*/.exec(source.slice(i));
      if (!keyMatch) {
        i += 1;
        continue;
      }
      const key = keyMatch[0];
      i += key.length;
      while (i < source.length && /\s/.test(source[i])) i += 1;
      if (source[i] !== ':') continue;
      i += 1;
      while (i < source.length && /\s/.test(source[i])) i += 1;
      const path = prefix ? `${prefix}.${key}` : key;
      if (source[i] === '{') {
        const nested = parseObject(i, path);
        keys.push(...nested.keys);
        i = nested.end;
      } else {
        keys.push(path);
        while (i < source.length && source[i] !== ';' && source[i] !== ',' && source[i] !== '}') i += 1;
        if (source[i] === ';' || source[i] === ',') i += 1;
      }
    }
    return { keys, end: i };
  }
  /* eslint-enable complexity, no-continue */

  return parseObject(start, '').keys;
}

describe('issue list chrome copy', () => {
  it('keeps locked Chinese and English list chrome', () => {
    expect(zh.page.issueList.tabs.myTodos).toBe('我的待办');
    expect(en.page.issueList.tabs.myTodos).toBe('My to-dos');
    expect(zh.page.issueList.tabs.open).toBe('开放中');
    expect(en.page.issueList.tabs.open).toBe('Active');
    expect(en.page.issueList.tabs.open).not.toBe('Open');
    expect(zh.page.issueList.actions.view).toBe('详情');
    expect(en.page.issueList.actions.view).toBe('View');
    expect(zh.page.issueList.columns.key).toBe('编号');
    expect(en.page.issueList.columns.key).toBe('Key');
    expect(zh.page.issueList.groupBy.none).toBe('不分组');
    expect(en.page.issueList.groupBy.none).toBe('No grouping');
    expect(zh.page.issueList.messages.deleteConfirmContent).toBe('确定要删除问题 "{title}" 吗？');
    expect(en.page.issueList.messages.deleteConfirmContent).toBe('Delete issue “{title}”?');
    expect(keysOf(zh.page.issueList).sort()).toEqual(keysOf(en.page.issueList).sort());
    const typings = readFileSync(resolve(process.cwd(), 'src/typings/app.d.ts'), 'utf8');
    expect(schemaKeysOfIssueList(typings).sort()).toEqual(keysOf(zh.page.issueList).sort());
    expect(en.page.issueList.tabs.myTodos).not.toBe(zh.page.issueList.tabs.myTodos);
    expect(en.page.issueList.actions.view).not.toBe(zh.page.issueList.actions.view);
  });

  it('wires the list page to the new keys and leaves groupIssuesBy alone', () => {
    const list = readFileSync(resolve(process.cwd(), 'src/views/issue/list/index.vue'), 'utf8');
    const groupBy = readFileSync(resolve(process.cwd(), 'src/utils/groupIssuesBy.ts'), 'utf8');
    expect(list).toContain("$t('page.issueList.tabs.myTodos')");
    expect(list).toContain("$t('page.issueList.toolbar.saveView')");
    expect(list).toContain("$t('page.issueList.columns.title')");
    expect(list).toContain("$t('page.issueList.filters.reset')");
    expect(list).toContain('page.issueList.groupBy.');
    expect(list).not.toContain('<span class="tab-label">我的待办</span>');
    expect(list).not.toContain("title: '编号'");
    expect(list).toContain("$t('page.issueList.columns.key')");
    expect(list).not.toContain("label: '创建时间'");
    expect(groupBy).toContain("label: '不分组'");
    expect(groupBy).toContain("label: '状态'");
  });
});
