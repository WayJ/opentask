import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';
import { compileStyle } from '@vue/compiler-sfc';
import { describe, expect, it } from 'vitest';

const detail = readFileSync(resolve(process.cwd(), 'src/views/issue/detail/index.vue'), 'utf8');

function editButtonBlock(source: string): string {
  const start = source.indexOf('<div v-if="!issue.is_deleted" class="issue-actions">');
  const end = source.indexOf('复制问题', start);
  if (start < 0 || end < 0) return '';
  return source.slice(start, end);
}

describe('detail edit button focus ring', () => {
  it('keeps the edit label, visibility, and route', () => {
    const block = editButtonBlock(detail);
    expect(block).toContain('v-if="!issue.is_deleted"');
    expect(block).toContain('编辑');
    expect(block).toContain(`@click="router.push({ path: '/issue/edit', query: { id: issue.id } })"`);
  });

  it('keeps the existing generic focus rule', () => {
    expect(detail).toContain(`*:focus-visible {
  outline: 2px solid var(--color-accent-primary);
  outline-offset: 2px;
}`);
  });

  it('adds one class and the two edit-page focus tiers', () => {
    const block = editButtonBlock(detail);
    expect(block).toContain('class="issue-action-edit"');
    expect(detail.match(/class="issue-action-edit"/g)).toHaveLength(1);
    expect(detail).toContain(`.issue-detail-container {
  --issue-focus: 2px solid #5e6ad2;
}`);
    expect(detail).toContain(`html.dark .issue-detail-container {
  --issue-focus: 2px solid #828fff;
}`);
    expect(detail).toContain(`.issue-detail-container .issue-actions .n-button.issue-action-edit:focus-visible {
  outline: var(--issue-focus);
  outline-offset: 2px;
}`);
    expect(detail).not.toContain('.issue-action-edit:focus {');
    const scoped = detail.match(/<style scoped>([\s\S]*?)<\/style>/);
    expect(scoped).not.toBeNull();
    const compiled = compileStyle({
      source: scoped?.[1] ?? '',
      filename: 'src/views/issue/detail/index.vue',
      id: 'focus',
      scoped: true
    });
    expect(compiled.errors).toEqual([]);
    expect(compiled.code).toContain(
      '.issue-detail-container .issue-actions .n-button.issue-action-edit[data-v-focus]:focus-visible'
    );
    expect(compiled.code).toContain('outline: var(--issue-focus);');
    expect(compiled.code).toContain('outline: 2px solid var(--color-accent-primary);');
  });
});
