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

function block(css: string, selector: string) {
  const start = css.indexOf(selector);
  const next = css.indexOf('\n}', start);
  return css.slice(start, next);
}

function token(section: string, name: string) {
  const match = section.match(new RegExp(`${name}:\\s*(#[0-9a-fA-F]{6})`));
  if (!match) throw new Error(`missing ${name}`);
  return match[1];
}

describe('theme contrast', () => {
  const css = readFileSync(resolve(process.cwd(), 'src/styles/design-tokens.css'), 'utf8');
  const light = block(css, ':root {');
  const dark = block(css, 'html.dark {');

  it('keeps body text and the accent above the UI threshold', () => {
    expect(contrast(token(light, '--vk-muted'), token(light, '--vk-bg'))).toBeGreaterThanOrEqual(4.5);
    expect(contrast(token(light, '--vk-accent'), '#ffffff')).toBeGreaterThanOrEqual(3);
    expect(contrast(token(dark, '--vk-muted'), token(dark, '--vk-bg'))).toBeGreaterThanOrEqual(4.5);
    expect(contrast(token(dark, '--vk-accent'), token(dark, '--vk-bg'))).toBeGreaterThanOrEqual(3);
  });
});
