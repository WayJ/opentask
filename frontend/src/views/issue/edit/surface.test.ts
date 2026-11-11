import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';
import { compileStyle } from '@vue/compiler-sfc';
import { Window } from 'happy-dom';
import { describe, expect, it } from 'vitest';

const edit = readFileSync(resolve(process.cwd(), 'src/views/issue/edit/index.vue'), 'utf8');
const surface = readFileSync(resolve(process.cwd(), 'src/styles/issue-surface.css'), 'utf8');
const renderer = readFileSync(resolve(process.cwd(), 'src/components/MarkdownRenderer.vue'), 'utf8');

describe('edit page local surface', () => {
  it('defines the issue tokens on the edit page itself', () => {
    expect(edit).toContain('.issue-edit-page {\n  --issue-canvas: #f5f6f6;');
    expect(edit).toContain('html.dark .issue-edit-page {\n  --issue-canvas: #010102;');
    expect(edit).toContain('--issue-accent: #5e6ad2;');
    expect(edit).toContain('--issue-focus: 2px solid #5e6ad2;');
    expect(edit).toContain('--issue-focus: 2px solid #828fff;');
    expect(edit).toContain('outline: var(--issue-focus);');
    expect(edit).toContain('outline-offset: 2px;');
  });

  it('draws a focus ring on sidebar selects only after measurement finds none', () => {
    expect(edit).toContain('.issue-edit-page .sidebar :deep(.n-base-selection:focus-within)');
    expect(edit).toContain('.issue-edit-page .sidebar :deep(.n-input:focus-within)');
  });

  it('keeps advanced options collapsed by default', () => {
    expect(edit).toContain('const advancedExpanded = ref(false);');
  });

  it('paints the preview shell from the local tokens and keeps 20px padding', () => {
    const scoped = edit.match(/<style scoped>([\s\S]*?)<\/style>/);
    expect(scoped).not.toBeNull();
    const compiled = compileStyle({
      source: scoped?.[1] ?? '',
      filename: 'src/views/issue/edit/index.vue',
      id: 'edit',
      scoped: true
    });
    expect(compiled.errors).toEqual([]);
    const window = new Window();
    const { document } = window;
    document.documentElement.className = 'dark';
    const style = document.createElement('style');
    style.textContent = compiled.code;
    document.head.appendChild(style);
    document.body.innerHTML = [
      '<div class="issue-edit-page" data-v-edit>',
      '<div class="preview-content" data-v-edit>',
      '<div class="markdown-body"><pre class="hljs"><code>plain</code></pre></div>',
      '</div></div>'
    ].join('');
    const page = document.querySelector('.issue-edit-page') as Element;
    const shell = document.querySelector('.preview-content') as Element;
    const pageStyle = window.getComputedStyle(page);
    const shellStyle = window.getComputedStyle(shell);
    expect(shellStyle.backgroundColor).toBe(pageStyle.getPropertyValue('--issue-surface').trim());
    expect(shellStyle.color).toBe(pageStyle.getPropertyValue('--issue-ink').trim());
    expect(shellStyle.padding).toBe('20px');
    expect(window.getComputedStyle(shell.querySelector('pre.hljs') as Element).backgroundColor).not.toBe('#ffffff');
    window.close();
  });

  it('does not add the edit page to the shared surface file or the renderer', () => {
    expect(surface).not.toContain('.issue-edit-page');
    expect(renderer).not.toContain('.issue-edit-page');
    expect(renderer).not.toContain('.issue-detail-container');
  });
});
