import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';
import { describe, expect, it } from 'vitest';

function channel(hex: string, index: number) {
  const value = Number.parseInt(hex.slice(1 + index * 2, 3 + index * 2), 16) / 255;
  return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
}

function contrast(foreground: string, background: string) {
  const lum = (hex: string) => 0.2126 * channel(hex, 0) + 0.7152 * channel(hex, 1) + 0.0722 * channel(hex, 2);
  const lighter = Math.max(lum(foreground), lum(background));
  const darker = Math.min(lum(foreground), lum(background));
  return (lighter + 0.05) / (darker + 0.05);
}

function block(css: string, startPattern: RegExp) {
  const match = startPattern.exec(css);
  if (!match) throw new Error(`missing ${startPattern}`);
  const next = css.indexOf('\n}', match.index);
  return css.slice(match.index, next);
}

function token(section: string, name: string) {
  const match = section.match(new RegExp(`${name}:\\s*(#[0-9a-fA-F]{6})`));
  if (!match) throw new Error(`missing ${name}`);
  return match[1];
}

describe('issue surface tokens', () => {
  const css = readFileSync(resolve(process.cwd(), 'src/styles/issue-surface.css'), 'utf8');
  const light = block(css, /\.issue-list-container,\s*\.issue-create-page\s*\{/);
  const dark = block(css, /html\.dark \.issue-list-container,\s*html\.dark \.issue-create-page\s*\{/);

  it('keeps the current accent and pairs text against both surfaces', () => {
    expect(token(light, '--issue-accent')).toBe('#5e6ad2');
    expect(token(dark, '--issue-accent')).toBe('#5e6ad2');
    expect(token(light, '--issue-on-accent')).toBe('#ffffff');
    expect(token(dark, '--issue-on-accent')).toBe('#ffffff');
    expect(contrast('#ffffff', '#5e6ad2')).toBeGreaterThanOrEqual(4.5);
    expect(contrast(token(light, '--issue-ink-secondary'), '#ffffff')).toBeGreaterThanOrEqual(4.5);
    expect(contrast(token(dark, '--issue-ink-secondary'), '#0f1011')).toBeGreaterThanOrEqual(4.5);
    expect(contrast(token(light, '--issue-ink'), '#ffffff')).toBeGreaterThanOrEqual(4.5);
    expect(contrast(token(dark, '--issue-ink'), '#0f1011')).toBeGreaterThanOrEqual(4.5);
    expect(contrast('#ffffff', token(light, '--issue-danger'))).toBeGreaterThanOrEqual(4.5);
    expect(contrast('#ffffff', token(dark, '--issue-danger'))).toBeGreaterThanOrEqual(4.5);
    expect(contrast('#ffffff', '#a8071a')).toBeGreaterThanOrEqual(4.5);
    expect(contrast('#ffffff', '#820014')).toBeGreaterThanOrEqual(4.5);
    expect(contrast('#828fff', '#0f1011')).toBeGreaterThanOrEqual(3);
    expect(contrast('#5e6ad2', '#ffffff')).toBeGreaterThanOrEqual(3);
    expect(token(light, '--issue-danger')).toBe('#cf1322');
    expect(css).toContain('outline: var(--issue-focus)');
    expect(css).toContain(':not(.n-button--disabled)');
    expect(css).toContain(':not(.n-button--secondary)');
    expect(css).toContain('n-button--primary-type.n-button--secondary:not(.n-button--disabled)');
    expect(css).toContain('--n-text-color: #828fff !important');
    expect(css).toContain('preview-pane .markdown-body pre.hljs');
    expect(css).toContain('background-color: #ffffff');
    expect(css).toContain('.hljs-built_in');
    expect(css).toContain('color: #c35408');
    expect(css).toContain('preview-pane .markdown-body a');
    for (const ink of ['#24292e', '#d73a49', '#6a737d', '#22863a', '#c35408', '#6f42c1', '#005cc5', '#032f62']) {
      expect(contrast(ink, '#ffffff')).toBeGreaterThanOrEqual(4.5);
    }
    expect(contrast('#828fff', '#0f1011')).toBeGreaterThanOrEqual(4.5);
    const card = [24, 24, 28];
    const accent = [94, 106, 210];
    for (const alpha of [0.12, 0.16, 0.2]) {
      const wash = accent.map((part, index) => Math.round(part * alpha + card[index] * (1 - alpha)));
      const hex = `#${wash.map(part => part.toString(16).padStart(2, '0')).join('')}`;
      expect(contrast('#828fff', hex)).toBeGreaterThanOrEqual(4.5);
    }
    expect(css).toContain('--n-color-hover: #a8071a !important');
    expect(css).toContain('--n-color-pressed: #820014 !important');
    expect(css).toContain('.issue-create-page .markdown-textarea');
    expect(css).not.toContain('#646cff');
    expect(css).not.toContain('#f5222d');
    expect(css).not.toContain('--n-color-disabled');
    expect(css).not.toMatch(/background-color:\s*(var\(--issue-danger\)|#cf1322)/);
  });
});
