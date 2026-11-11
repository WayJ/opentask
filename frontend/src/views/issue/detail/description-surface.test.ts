import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const detail = readFileSync(resolve(process.cwd(), 'src/views/issue/detail/index.vue'), 'utf8');
const renderer = readFileSync(resolve(process.cwd(), 'src/components/MarkdownRenderer.vue'), 'utf8');

describe('detail description dark surface', () => {
  it('overrides prose only inside the detail description', () => {
    expect(detail).toContain(
      'html.dark .issue-detail-container .description-content :deep(.markdown-body)'
    );
    expect(detail).toContain('background-color: var(--color-bg-primary);');
    expect(detail).toContain('color: #828fff;');
    expect(detail).toContain('background-color: #23252a;');
  });

  it('does not restyle comments or the shared renderer', () => {
    expect(detail).not.toContain('html.dark .issue-detail-container .comment-text :deep(.markdown-body)');
    expect(renderer).not.toContain('.issue-detail-container');
  });
});
