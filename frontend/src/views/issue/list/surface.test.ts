import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';
import { describe, expect, it } from 'vitest';

describe('issue list surface', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/views/issue/list/index.vue'), 'utf8');

  it('loads the local sheet without changing the list contract', () => {
    expect(source).toContain("import '@/styles/issue-surface.css';");
    expect(source).toContain("default: () => '详情'");
    expect(source).toContain("default: () => '删除'");
    expect(source).toContain("title: '确认删除'");
    expect(source).toContain("positiveText: '删除'");
    expect(source).toContain("negativeText: '取消'");
    expect(source).toContain("window.$message?.success('问题删除成功')");
    expect(source).toContain('white-space: normal');
    expect(source).toContain('max-height: none');
    expect(source).toContain('scroll-x="1400"');
    expect(source).toContain('page.shell.noIssues');
    expect(source).toContain('page.shell.createIssue');
    expect(source).not.toContain('line-clamp');
  });
});
