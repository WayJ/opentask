import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';
import { compileStyle } from '@vue/compiler-sfc';
import { Window } from 'happy-dom';
import { describe, expect, it } from 'vitest';

const detail = readFileSync(resolve(process.cwd(), 'src/views/issue/detail/index.vue'), 'utf8');
const renderer = readFileSync(resolve(process.cwd(), 'src/components/MarkdownRenderer.vue'), 'utf8');

describe('detail description dark surface', () => {
  it('overrides prose only inside the detail description', () => {
    expect(detail).toContain('html.dark .issue-detail-container .description-content :deep(.markdown-body)');
    expect(detail).toContain('background-color: var(--color-bg-primary);');
    expect(detail).toContain('color: #828fff;');
    expect(detail).toContain('background-color: #23252a;');
  });

  it('does not restyle comments or the shared renderer', () => {
    expect(detail).not.toContain('html.dark .issue-detail-container .comment-text :deep(.markdown-body)');
    expect(renderer).not.toContain('.issue-detail-container');
  });

  it('keeps the dark chip on inline code and the light island on both fences', () => {
    const scoped = detail.match(/<style scoped>([\s\S]*?)<\/style>/);
    expect(scoped).not.toBeNull();
    const compiled = compileStyle({
      source: scoped?.[1] ?? '',
      filename: 'src/views/issue/detail/index.vue',
      id: 'surface',
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
      '<div class="issue-detail-container">',
      '<div class="description-content" data-v-surface>',
      '<div class="markdown-body">',
      '<p><code>code</code></p>',
      '<pre class="hljs"><code class="language-javascript">const value</code></pre>',
      '<pre class="hljs"><code>plain fence alpha</code></pre>',
      '</div></div></div>'
    ].join('');
    const pres = [...document.querySelectorAll('pre.hljs')];
    const background = (el: Element) => window.getComputedStyle(el).backgroundColor;
    expect(background(document.querySelector('p > code') as Element)).toBe('#23252a');
    expect(background(pres[0].querySelector('code') as Element)).not.toBe('#23252a');
    expect(background(pres[1].querySelector('code') as Element)).not.toBe('#23252a');
    expect(background(pres[0])).toBe('#ffffff');
    expect(background(pres[1])).toBe('#ffffff');
    window.close();
  });
});
