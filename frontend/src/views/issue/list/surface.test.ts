import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';
import { describe, expect, it } from 'vitest';

describe('issue list surface', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/views/issue/list/index.vue'), 'utf8');

  it('loads the local sheet without changing the list contract', () => {
    expect(source).toContain("import '@/styles/issue-surface.css';");
    expect(source).toContain("$t('page.issueList.actions.view')");
    expect(source).toContain("$t('common.delete')");
    expect(source).toContain("$t('page.issueList.messages.deleteTitle')");
    expect(source).toContain("$t('page.issueList.messages.deleteConfirmContent'");
    expect(source).toContain("$t('common.cancel')");
    expect(source).toContain("$t('page.issueList.messages.deleteSuccess')");
    expect(source).toContain('white-space: normal');
    expect(source).toContain('max-height: none');
    expect(source).toContain('scroll-x="1400"');
    expect(source).toContain('page.shell.noIssues');
    expect(source).toContain('page.shell.createIssue');
    expect(source).not.toContain('line-clamp');
    expect(source).not.toContain("default: () => '详情'");
    expect(source).not.toContain("default: () => '删除'");
    expect(source).not.toContain("title: '确认删除'");
  });
});
