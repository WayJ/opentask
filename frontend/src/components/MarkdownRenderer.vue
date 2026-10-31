<script setup lang="ts">
import { computed } from 'vue';
import MarkdownIt from 'markdown-it';
import markdownItKatex from 'markdown-it-katex';
import hljs from 'highlight.js';
import 'katex/dist/katex.min.css';

interface Props {
  content: string;
}

const props = defineProps<Props>();

// 初始化 markdown-it
const md = new MarkdownIt({
  html: true, // 允许 HTML 标签
  linkify: true, // 自动转换 URL 为链接
  typographer: true, // 启用一些语言中立的替换和引号美化
  highlight: (str: string, lang: string) => {
    // 代码高亮支持
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre class="hljs"><code class="language-${lang}">${hljs.highlight(str, { language: lang }).value}</code></pre>`;
      } catch {
        // 忽略错误
      }
    }
    // 回退到默认处理
    return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`;
  }
});

// 集成 KaTeX 数学公式插件
md.use(markdownItKatex);

// 获取引用类型的链接和样式
function getReferenceInfo(refType: string, refId: string) {
  let href = '';
  let cssClass = '';

  switch (refType) {
    case 'ISSUE':
      href = `/issue/detail?id=${refId}`;
      cssClass = 'ref-mention ref-issue';
      break;
    case 'PROJECT':
      href = `/project/detail?id=${refId}`;
      cssClass = 'ref-mention ref-project';
      break;
    case 'REQUIREMENT':
      href = `/requirement/detail?id=${refId}`;
      cssClass = 'ref-mention ref-requirement';
      break;
    case 'DOC':
      href = `/doc/detail?id=${refId}`;
      cssClass = 'ref-mention ref-doc';
      break;
    default:
      href = `/#`;
      cssClass = 'ref-mention';
  }

  return { href, cssClass };
}

// 创建链接token
interface LinkTokenParams {
  refType: string;
  refId: string;
  refName: string;
  level: number;
}

function createLinkTokens({ refType, refId, refName, level }: LinkTokenParams) {
  const { href, cssClass } = getReferenceInfo(refType, refId);
  const linkLevel = level + 1;

  return [
    {
      type: 'link_open',
      tag: 'a',
      attrs: [
        ['href', href],
        ['class', cssClass]
      ],
      nesting: 1,
      level: linkLevel
    },
    {
      type: 'text',
      content: `+${refName}`,
      level: linkLevel
    },
    {
      type: 'link_close',
      tag: 'a',
      nesting: -1,
      level: linkLevel
    }
  ];
}

// 处理文本节点中的引用
function processTextContent(child: any) {
  const refRegex = /\+((?:ISSUE|PROJECT|REQUIREMENT|DOC|issue|project|requirement|doc))-([-\w]+)/g;
  const parts = child.content.split(refRegex);
  const newChildren = [];

  for (let k = 0; k < parts.length; k += 1) {
    const part = parts[k];
    if (k % 3 === 1 && part) {
      const refType = part.toUpperCase();
      const refId = parts[k + 1];
      const refName = `${refType}-${refId}`;
      const linkTokens = createLinkTokens({ refType, refId, refName, level: child.level });
      newChildren.push(...linkTokens);
      k += 1;
    } else if (part) {
      newChildren.push({
        type: 'text',
        content: part,
        level: child.level
      });
    }
  }

  return newChildren;
}

// 处理内联token的子节点
function processInlineChildren(children: any[]) {
  const newChildren = [];

  for (let j = 0; j < children.length; j += 1) {
    const child = children[j];
    if (child.type === 'text') {
      const processedTokens = processTextContent(child);
      newChildren.push(...processedTokens);
    } else {
      newChildren.push(child);
    }
  }

  return newChildren;
}

// 添加自定义插件：处理资源引用
md.use(markdownIt => {
  markdownIt.core.ruler.push('resource_references', state => {
    for (let i = 0; i < state.tokens.length; i += 1) {
      const token = state.tokens[i];
      if (token.type === 'inline') {
        token.children ||= [];
        token.children = processInlineChildren(token.children);
      }
    }
  });
});

// 渲染 markdown
const renderedHtml = computed(() => {
  if (!props.content) return '';
  return md.render(props.content);
});
</script>

<template>
  <div class="markdown-body" v-html="renderedHtml"></div>
</template>

<style>
/* Highlight.js 代码高亮样式 - GitHub 主题 */
@import 'highlight.js/styles/github.css';

/* KaTeX 数学公式字体 */
@font-face {
  font-family: 'KaTeX_Main';
  src: url('katex/fonts/KaTeX_Main-Regular.woff2') format('woff2');
}

/* 覆盖 highlight.js 代码块样式，与 markdown-body 兼容 */
.markdown-body pre code.hljs {
  padding: 12px;
  overflow: auto;
  font-size: 85%;
  line-height: 1.45;
  background-color: #f6f8fa;
  border-radius: 6px;
  margin: 0.75em 0;
}

.markdown-body .hljs {
  background-color: transparent;
}
/*
 * 紧凑版 GitHub Flavored Markdown 样式
 * 基于 GitHub 的实际样式，调整为更紧凑的布局
 */

.markdown-body {
  -ms-text-size-adjust: 100%;
  -webkit-text-size-adjust: 100%;
  margin: 0;
  color: #24292f;
  background-color: #ffffff;
  font-family:
    -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji';
  font-size: 14px;
  line-height: 1.5;
  word-wrap: break-word;
}

.markdown-body .octicon {
  display: inline-block;
  fill: currentColor;
  vertical-align: text-bottom;
}

.markdown-body details,
.markdown-body figcaption,
.markdown-body figure {
  display: block;
}

.markdown-body summary {
  display: list-item;
}

.markdown-body [hidden] {
  display: none !important;
}

.markdown-body a {
  background-color: transparent;
  color: #0969da;
  text-decoration: none;
}

.markdown-body a:active,
.markdown-body a:hover {
  outline-width: 0;
}

.markdown-body abbr[title] {
  border-bottom: none;
  text-decoration: underline dotted;
}

.markdown-body b,
.markdown-body strong {
  font-weight: 600;
}

.markdown-body dfn {
  font-style: italic;
}

/* 标题样式 - 紧凑版 */
.markdown-body h1 {
  margin: 0.5em 0 0.25em 0;
  padding-bottom: 0.2em;
  font-size: 1.4em;
  font-weight: 600;
  border-bottom: 1px solid #d0d7de;
}

.markdown-body h2 {
  margin: 0.5em 0 0.25em 0;
  padding-bottom: 0.2em;
  font-size: 1.25em;
  font-weight: 600;
  border-bottom: 1px solid #d0d7de;
}

.markdown-body h3 {
  margin: 0.5em 0 0.25em 0;
  font-size: 1.1em;
  font-weight: 600;
}

.markdown-body h4 {
  margin: 0.5em 0 0.25em 0;
  font-size: 1.05em;
  font-weight: 600;
}

.markdown-body h5 {
  margin: 0.5em 0 0.25em 0;
  font-size: 1em;
  font-weight: 600;
}

.markdown-body h6 {
  margin: 0.5em 0 0.25em 0;
  font-size: 0.95em;
  font-weight: 600;
  color: #57606a;
}

/* 段落样式 - 紧凑版 */
.markdown-body p {
  margin-top: 0;
  margin-bottom: 0.5em;
}

.markdown-body p:first-child {
  margin-top: 0;
}

.markdown-body p:last-child {
  margin-bottom: 0;
}

/* 引用块样式 - 紧凑版 */
.markdown-body blockquote {
  margin: 0.5em 0;
  padding: 0 0.75em;
  color: #57606a;
  border-left: 0.25em solid #d0d7de;
}

.markdown-body blockquote p {
  margin: 0;
}

/* 列表样式 - 紧凑版 */
.markdown-body ul,
.markdown-body ol {
  margin-top: 0;
  margin-bottom: 0.5em;
  padding-left: 1.5em;
}

.markdown-body ul ul,
.markdown-body ul ol,
.markdown-body ol ol,
.markdown-body ol ul {
  margin-top: 0;
  margin-bottom: 0;
}

.markdown-body li {
  margin-top: 0.15em;
  margin-bottom: 0.15em;
}

.markdown-body li > p {
  margin-top: 0.5em;
}

.markdown-body ul li {
  list-style-type: disc;
}

.markdown-body ul ul li {
  list-style-type: circle;
}

.markdown-body ul ul ul li {
  list-style-type: square;
}

.markdown-body ol li {
  list-style-type: decimal;
}

/* 行内代码样式 */
.markdown-body code:not([lang]):not([class]) {
  padding: 0.15em 0.3em;
  margin: 0;
  font-size: 85%;
  background-color: rgba(175, 184, 193, 0.2);
  border-radius: 4px;
}

.markdown-body code {
  font-family:
    ui-monospace,
    SFMono-Regular,
    SF Mono,
    Menlo,
    Consolas,
    Liberation Mono,
    monospace;
  font-size: 85%;
}

/* 代码块样式 - 紧凑版，与 highlight.js 兼容 */
.markdown-body pre {
  padding: 12px;
  overflow: auto;
  font-size: 85%;
  line-height: 1.45;
  background-color: #f6f8fa;
  border-radius: 6px;
  margin: 0.75em 0;
}

.markdown-body pre code {
  padding: 0;
  background-color: transparent;
  border-radius: 0;
  display: block;
}

/* Highlight.js 代码高亮样式覆盖 */
.markdown-body pre code.hljs {
  background-color: transparent;
}

/* 表格样式 - 紧凑版 */
.markdown-body table {
  border-spacing: 0;
  border-collapse: collapse;
  display: block;
  width: 100%;
  max-width: 100%;
  margin-top: 0;
  margin-bottom: 0.75em;
  overflow: auto;
}

.markdown-body table th {
  font-weight: 600;
  background-color: #f6f8fa;
}

.markdown-body table th,
.markdown-body table td {
  padding: 4px 10px;
  border: 1px solid #d0d7de;
}

.markdown-body table tr {
  background-color: #ffffff;
  border-top: 1px solid #d0d7de;
}

.markdown-body table tr:nth-child(2n) {
  background-color: #f6f8fa;
}

.markdown-body table tr:hover {
  background-color: #f1f3f5;
}

/* 图片样式 */
.markdown-body img {
  max-width: 100%;
  box-sizing: content-box;
  background-color: #ffffff;
  max-height: 400px;
}

.markdown-body img[align='right'] {
  padding-left: 20px;
}

.markdown-body img[align='left'] {
  padding-right: 20px;
}

.markdown-body .emoji {
  font-family: 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol';
  font-size: 1em;
  font-style: normal;
  font-weight: 400;
  line-height: 1;
}

.markdown-body frame {
  border: 0;
}

.markdown-body hr {
  height: 0.25em;
  padding: 0;
  margin: 1.5em 0;
  background-color: #d0d7de;
  border: 0;
}

.markdown-body input[type='checkbox'] {
  margin: 0.2em 0.5em 0.25em -1.6em;
  vertical-align: middle;
}

.markdown-body .task-list-item {
  list-style-type: none;
}

.markdown-body .task-list-item label {
  display: flex;
  align-items: center;
}

.markdown-body .task-list-item .task-list-item-checkbox {
  margin: 0 0.5em 0.25em -1.6em;
}

.markdown-body::before {
  display: table;
  content: '';
}

.markdown-body::after {
  display: table;
  clear: both;
  content: '';
}

.markdown-body > *:first-child {
  margin-top: 0 !important;
}

.markdown-body > *:last-child {
  margin-bottom: 0 !important;
}

/* 引用链接样式 */
.markdown-body a.ref-mention {
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
  white-space: nowrap;
  transition: all 0.2s;
  text-decoration: none !important;
}

.markdown-body a.ref-issue {
  background-color: rgba(24, 160, 88, 0.1);
  color: #18a058;
}

.markdown-body a.ref-issue:hover {
  background-color: rgba(24, 160, 88, 0.2);
}

.markdown-body a.ref-project {
  background-color: rgba(24, 144, 255, 0.1);
  color: #1890ff;
}

.markdown-body a.ref-project:hover {
  background-color: rgba(24, 144, 255, 0.2);
}

.markdown-body a.ref-requirement {
  background-color: rgba(230, 126, 34, 0.1);
  color: #e67e22;
}

.markdown-body a.ref-requirement:hover {
  background-color: rgba(230, 126, 34, 0.2);
}

.markdown-body a.ref-doc {
  background-color: rgba(155, 89, 182, 0.1);
  color: #9b59b6;
}

.markdown-body a.ref-doc:hover {
  background-color: rgba(155, 89, 182, 0.2);
}
</style>
