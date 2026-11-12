import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';
import { describe, expect, it } from 'vitest';

describe('issue create surface', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/views/issue/create/index.vue'), 'utf8');

  it('imports the local surface sheet and drops the light-only hex colors', () => {
    expect(source).toContain("import '@/styles/issue-surface.css';");
    expect(source).not.toMatch(/#(?:fff|ffffff|f5f7fa|e8eaed|1a1a1a|aaa|f9fafb)\b/i);
    expect(source).not.toContain('outline: none');
    expect(source).toContain('background: var(--issue-surface)');
    expect(source).toContain('color: var(--issue-ink)');
    expect((source.match(/\$t\('page\.issueForm\.createTitle'\)/g) ?? []).length).toBe(2);
    expect(source).not.toContain('<NText strong style="font-size: 16px; margin-left: 12px">创建问题</NText>');
    expect(source).not.toMatch(/^\s+创建问题\s*$/m);
    expect(source).toContain('使用模板');
    expect(source).toContain('从模板创建问题');
    expect(source).toContain("$t('page.issueForm.advanced')");
    expect(source).toContain('const advancedExpanded = ref(false)');
    expect(source).toContain('请输入问题标题');
    expect(source).toContain('问题创建成功');
    expect(source).toContain('问题创建失败');
    expect(source).toContain("$t('page.issueForm.linkedTaskId')");
    expect(source).toContain("$t('page.issueForm.linkedRequirementId')");
    expect(source).toContain("$t('page.issueForm.assigneeId')");
    expect(source).not.toContain('>高级选项<');
  });
});
