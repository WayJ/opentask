/**
 * 将 .vue 文件中与 design token 值完全相同的硬编码 hex 颜色替换为 var() 引用。
 *
 * 仅替换 CSS 上下文：
 *   1. <style> 块内部
 *   2. 模板中 style="..." 内联属性
 * 跳过 JS 代码（ECharts 配置等）与 SVG/组件属性（fill=/stroke=/color=），
 * 这些位置 var() 不生效。
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { execSync } from 'node:child_process';

const TOKEN_MAP = {
  '3b82f6': '--color-primary',
  '2563eb': '--color-primary-hover',
  '1d4ed8': '--color-primary-active',
  '22c55e': '--color-success',
  f59e0b: '--color-warning',
  ef4444: '--color-danger',
  '8b5cf6': '--color-info',
  f7f8fa: '--color-bg-secondary',
  f0f2f5: '--color-bg-tertiary',
  111827: '--color-text-primary',
  '6b7280': '--color-text-secondary',
  '9ca3af': '--color-text-tertiary',
  e5e7eb: '--color-border-subtle',
  d1d5db: '--color-border-default'
};

const HEX_RE = new RegExp(`#(${Object.keys(TOKEN_MAP).join('|')})\\b`, 'gi');

function replaceHex(css) {
  let count = 0;
  const out = css.replace(HEX_RE, (_m, hex) => {
    count += 1;
    return `var(${TOKEN_MAP[hex.toLowerCase()]})`;
  });
  return { out, count };
}

const files = execSync('git ls-files "src/**/*.vue"', { encoding: 'utf8' }).trim().split('\n').filter(Boolean);

const styleBlockRe = /(<style[^>]*>)([\s\S]*?)(<\/style>)/gi;
const styleAttrRe = /(style=")([^"]*)(")/g;

let total = 0;
const perFile = [];

for (const file of files) {
  let content = readFileSync(file, 'utf8');
  let fileCount = 0;

  // 1. <style> 块
  content = content.replace(styleBlockRe, (...groups) => {
    const [, open, body, close] = groups;
    const { out, count } = replaceHex(body);
    fileCount += count;
    return open + out + close;
  });

  // 2. style="..." 内联属性（仅静态属性）
  content = content.replace(styleAttrRe, (...groups) => {
    const [, open, body, close] = groups;
    const { out, count } = replaceHex(body);
    fileCount += count;
    return open + out + close;
  });

  if (fileCount > 0) {
    writeFileSync(file, content);
    perFile.push(`${file}: ${fileCount}`);
    total += fileCount;
  }
}

console.log(`Replaced ${total} hex occurrences in ${perFile.length} files:`);
perFile.forEach(l => console.log(`  ${l}`));
