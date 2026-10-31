<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { NButton, NSelect, NSpace, NTooltip } from 'naive-ui';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import markdownItToc from 'markdown-it-toc-done-right';
import markdownItAnchor from 'markdown-it-anchor';
import SvgIcon from '@/components/custom/svg-icon.vue';

interface Props {
  content: string;
  fileName?: string;
}

const props = withDefaults(defineProps<Props>(), {
  fileName: ''
});

// 代码高亮主题
type ThemeType = 'github' | 'github-dark' | 'atom-one-dark' | 'atom-one-light' | 'vs' | 'vs2015' | 'xcode';

interface ThemeOption {
  label: string;
  value: ThemeType;
}

const themeOptions: ThemeOption[] = [
  { label: 'GitHub Light', value: 'github' },
  { label: 'GitHub Dark', value: 'github-dark' },
  { label: 'Atom One Dark', value: 'atom-one-dark' },
  { label: 'Atom One Light', value: 'atom-one-light' },
  { label: 'VS', value: 'vs' },
  { label: 'VS 2015', value: 'vs2015' },
  { label: 'XCode', value: 'xcode' }
];

const selectedTheme = ref<ThemeType>('github');
const isFullscreen = ref(false);
const tocSidebarRef = ref<HTMLElement | null>(null);

// 配置 markdown-it
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  highlight(str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(str, { language: lang, ignoreIllegals: true }).value;
      } catch {
        // 忽略高亮错误，使用默认渲染
      }
    }
    return md.utils.escapeHtml(str);
  }
});

// 使用 anchor 插件为标题生成 id
md.use(markdownItAnchor, {
  permalink: markdownItAnchor.permalink.linkInsideHeader({
    symbol: '',
    placement: 'before'
  })
});

// 使用目录插件
md.use(markdownItToc, { listType: 'ul' });

// 提取目录内容
const tocHtml = computed(() => {
  if (!props.content) return '';

  // 如果内容中没有 [toc]，自动在开头添加
  let content = props.content;
  if (!content.includes('[toc]')) {
    content = `[toc]\n\n${content}`;
  }

  const rendered = md.render(content);
  // 匹配多种可能的目录容器格式
  const tocMatch =
    rendered.match(/<div class="table-of-contents">[\s\S]*?<\/div>/) ||
    rendered.match(/<nav[^>]*>[\s\S]*?<\/nav>/) ||
    rendered.match(/<ul class="toc-list">[\s\S]*?<\/ul>/);

  if (tocMatch) {
    return tocMatch[0];
  }

  // 如果没有找到目录，返回空字符串
  return '';
});

// 提取主要内容（移除目录后的内容）
const contentHtml = computed(() => {
  if (!props.content) return '';

  // 如果内容中没有 [toc]，自动在开头添加
  let content = props.content;
  if (!content.includes('[toc]')) {
    content = `[toc]\n\n${content}`;
  }

  const rendered = md.render(content);
  // 移除目录部分
  return rendered
    .replace(/<div class="table-of-contents">[\s\S]*?<\/div>/, '')
    .replace(/<nav[^>]*>[\s\S]*?<\/nav>/, '')
    .replace(/<ul class="toc-list">[\s\S]*?<\/ul>/, '');
});

// 切换主题
function handleThemeChange(value: ThemeType) {
  selectedTheme.value = value;
}

// 下载文档
function handleDownload() {
  if (!props.content) return;

  const blob = new Blob([props.content], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = props.fileName || 'document.md';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// 全屏切换
function handleFullscreen() {
  const container = document.querySelector('.markdown-preview-container') as HTMLElement;
  if (!container) return;

  if (!isFullscreen.value) {
    if (container.requestFullscreen) {
      container.requestFullscreen();
    }
  } else if (document.exitFullscreen) {
    document.exitFullscreen();
  }
}

// 监听全屏变化事件
if (typeof document !== 'undefined') {
  document.addEventListener('fullscreenchange', () => {
    isFullscreen.value = Boolean(document.fullscreenElement);
  });
}

// 绑定目录点击事件
function bindTocClickEvents() {
  nextTick(() => {
    const sidebar = tocSidebarRef.value;
    if (!sidebar) return;

    const links = sidebar.querySelectorAll('a');
    links.forEach(link => {
      link.addEventListener('click', e => {
        e.preventDefault();
        const href = (e.currentTarget as HTMLAnchorElement).getAttribute('href');
        if (href) {
          // 移除 # 号，获取 id
          const id = href.substring(1);
          // 使用 getElementById，它会自动处理 URL 编码
          const targetElement = document.getElementById(id) as HTMLElement;
          if (targetElement) {
            targetElement.scrollIntoView({
              behavior: 'smooth',
              block: 'start'
            });
          }
        }
      });
    });
  });
}

// 监听目录内容和全屏状态变化，重新绑定事件
watch([tocHtml, isFullscreen], () => {
  bindTocClickEvents();
});

// 组件挂载后绑定事件
onMounted(() => {
  bindTocClickEvents();
});
</script>

<template>
  <div class="markdown-preview-container" :class="{ 'is-fullscreen': isFullscreen }">
    <!-- 右上角工具栏 -->
    <div class="markdown-toolbar-floating">
      <NSpace align="center" :size="8">
        <NSelect
          v-model:value="selectedTheme"
          :options="themeOptions"
          size="small"
          style="width: 130px"
          @update:value="handleThemeChange"
        />
        <NTooltip trigger="hover">
          <template #trigger>
            <NButton size="small" secondary :disabled="!content" @click="handleDownload">
              <template #icon>
                <SvgIcon icon="mdi:download" />
              </template>
            </NButton>
          </template>
          下载 Markdown 文档
        </NTooltip>
        <NTooltip trigger="hover">
          <template #trigger>
            <NButton size="small" secondary @click="handleFullscreen">
              <template #icon>
                <SvgIcon :icon="isFullscreen ? 'mdi:fullscreen-exit' : 'mdi:fullscreen'" />
              </template>
            </NButton>
          </template>
          {{ isFullscreen ? '退出全屏' : '全屏预览' }}
        </NTooltip>
      </NSpace>
    </div>

    <!-- Markdown 内容区域 -->
    <div class="markdown-content-wrapper">
      <!-- 左侧目录 - 仅在全屏时显示 -->
      <div v-if="isFullscreen && tocHtml" ref="tocSidebarRef" class="markdown-toc-sidebar" v-html="tocHtml"></div>

      <!-- 主内容区 -->
      <div class="markdown-preview" :class="`theme-${selectedTheme}`" v-html="contentHtml"></div>
    </div>
  </div>
</template>

<style scoped>
.markdown-preview-container {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.markdown-content-wrapper {
  position: relative;
  display: flex;
  gap: 16px;
  height: 100%;
}

.markdown-preview-container.is-fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999;
  background-color: #ffffff;
}

.markdown-toolbar-floating {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 10;
  padding: 8px 12px;
  background-color: rgba(255, 255, 255, 0.95);
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(4px);
}

.markdown-preview {
  flex: 1;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  font-size: 15px;
  line-height: 1.7;
  color: #24292f;
  word-wrap: break-word;
  padding: 16px;
  padding-top: 56px;
  background-color: #ffffff;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  overflow-y: auto;
  min-width: 0;
  scroll-behavior: smooth;
}

/* 目录侧边栏 - 仅在全屏时显示 */
.markdown-toc-sidebar {
  display: none;
  width: 280px;
  flex-shrink: 0;
  padding: 20px;
  padding-top: 80px;
  background-color: #fafbfc;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  overflow-y: auto;
  font-size: 13px;
}

/* 全屏时显示目录 */
.markdown-preview-container.is-fullscreen .markdown-toc-sidebar {
  display: block;
  background-color: #ffffff;
}

/* 目录标题 */
.markdown-toc-sidebar :deep(.table-of-contents) {
  margin: 0;
}

.markdown-toc-sidebar :deep(.table-of-contents)::before {
  content: '目录';
  display: block;
  font-size: 16px;
  font-weight: 600;
  color: #24292f;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid #e0e0e0;
}

/* 目录列表 */
.markdown-toc-sidebar :deep(ul) {
  list-style: none;
  padding-left: 0;
  margin: 0;
}

.markdown-toc-sidebar :deep(ul ul) {
  padding-left: 20px;
  margin-top: 4px;
}

.markdown-toc-sidebar :deep(li) {
  margin: 6px 0;
}

/* 目录链接 */
.markdown-toc-sidebar :deep(a) {
  color: #586069;
  text-decoration: none;
  display: block;
  padding: 6px 12px;
  border-radius: 6px;
  transition: all 0.2s ease;
  line-height: 1.5;
  cursor: pointer;
}

.markdown-toc-sidebar :deep(a:hover) {
  background-color: #f1f8ff;
  color: #0366d6;
  text-decoration: none;
  transform: translateX(2px);
}

.markdown-toc-sidebar :deep(a:active) {
  transform: translateX(1px);
}

/* 第一级标题样式 */
.markdown-toc-sidebar :deep(ul > li > a) {
  font-weight: 600;
  font-size: 14px;
  color: #24292f;
}

/* 第二级及以下的字体大小 */
.markdown-toc-sidebar :deep(ul ul a) {
  font-size: 13px;
}

.markdown-toc-sidebar :deep(ul ul ul a) {
  font-size: 12px;
  opacity: 0.95;
}

.markdown-toc-sidebar :deep(ul ul ul ul a) {
  font-size: 12px;
  opacity: 0.9;
}

.markdown-toc-sidebar :deep(ul ul ul ul ul a) {
  font-size: 11px;
  opacity: 0.85;
}

.markdown-toc-sidebar :deep(ul ul ul ul ul ul a) {
  font-size: 11px;
  opacity: 0.8;
}

.markdown-toc-sidebar :deep(ul ul ul ul ul ul ul a) {
  font-size: 11px;
  opacity: 0.75;
}

/* 标题样式 */
.markdown-preview :deep(h1),
.markdown-preview :deep(h2),
.markdown-preview :deep(h3),
.markdown-preview :deep(h4),
.markdown-preview :deep(h5),
.markdown-preview :deep(h6) {
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
}

.markdown-preview :deep(h1) {
  font-size: 2em;
  border-bottom: 1px solid #d0d7de;
  padding-bottom: 0.3em;
}

.markdown-preview :deep(h2) {
  font-size: 1.5em;
  border-bottom: 1px solid #d0d7de;
  padding-bottom: 0.3em;
}

.markdown-preview :deep(h3) {
  font-size: 1.25em;
}

.markdown-preview :deep(h4) {
  font-size: 1em;
}

.markdown-preview :deep(h5) {
  font-size: 0.875em;
}

.markdown-preview :deep(h6) {
  font-size: 0.85em;
  color: #57606a;
}

/* 段落样式 */
.markdown-preview :deep(p) {
  margin-top: 0;
  margin-bottom: 16px;
}

/* 列表样式 */
.markdown-preview :deep(ul),
.markdown-preview :deep(ol) {
  margin-top: 0;
  margin-bottom: 16px;
  padding-left: 2em;
}

.markdown-preview :deep(li) {
  margin-top: 0.25em;
}

.markdown-preview :deep(li > p) {
  margin-top: 16px;
}

.markdown-preview :deep(ul ul),
.markdown-preview :deep(ul ol),
.markdown-preview :deep(ol ol),
.markdown-preview :deep(ol ul) {
  margin-top: 0;
  margin-bottom: 0;
}

/* 代码样式 */
.markdown-preview :deep(code) {
  padding: 0.2em 0.4em;
  margin: 0;
  font-size: 85%;
  font-family:
    ui-monospace,
    SFMono-Regular,
    SF Mono,
    Menlo,
    Consolas,
    Liberation Mono,
    monospace;
  background-color: rgba(175, 184, 193, 0.2);
  border-radius: 6px;
}

.markdown-preview :deep(pre) {
  padding: 16px;
  overflow: auto;
  font-size: 85%;
  line-height: 1.45;
  background-color: #f6f8fa;
  border-radius: 6px;
  margin-bottom: 16px;
}

.markdown-preview :deep(pre code) {
  padding: 0;
  background-color: transparent;
  border: 0;
}

/* 代码高亮样式 - 默认 GitHub Light */
.markdown-preview :deep(.hljs) {
  background-color: #f6f8fa;
  padding: 16px;
  border-radius: 6px;
  margin-bottom: 0;
}

/* GitHub Dark 主题 */
.markdown-preview.theme-github-dark {
  background-color: #0d1117;
  color: #c9d1d9;
}

.markdown-preview.theme-github-dark :deep(.hljs) {
  background-color: #161b22;
}

.markdown-preview.theme-github-dark :deep(pre) {
  background-color: #161b22;
}

.markdown-preview.theme-github-dark :deep(code) {
  background-color: rgba(110, 118, 129, 0.4);
}

.markdown-preview.theme-github-dark :deep(table tr) {
  background-color: #0d1117;
}

.markdown-preview.theme-github-dark :deep(table tr:nth-child(2n)) {
  background-color: #161b22;
}

.markdown-preview.theme-github-dark :deep(table th) {
  background-color: #161b22;
}

.markdown-preview.theme-github-dark :deep(a) {
  color: #58a6ff;
}

/* Atom One Dark 主题 */
.markdown-preview.theme-atom-one-dark {
  background-color: #282c34;
  color: #abb2bf;
}

.markdown-preview.theme-atom-one-dark :deep(.hljs) {
  background-color: #282c34;
}

.markdown-preview.theme-atom-one-dark :deep(pre) {
  background-color: #282c34;
}

.markdown-preview.theme-atom-one-dark :deep(code) {
  background-color: rgba(110, 118, 129, 0.4);
}

.markdown-preview.theme-atom-one-dark :deep(table tr) {
  background-color: #282c34;
}

.markdown-preview.theme-atom-one-dark :deep(table tr:nth-child(2n)) {
  background-color: #21252b;
}

.markdown-preview.theme-atom-one-dark :deep(table th) {
  background-color: #21252b;
}

.markdown-preview.theme-atom-one-dark :deep(a) {
  color: #61afef;
}

/* Atom One Light 主题 */
.markdown-preview.theme-atom-one-light {
  background-color: #fafafa;
  color: #383a42;
}

.markdown-preview.theme-atom-one-light :deep(.hljs) {
  background-color: #fafafa;
}

.markdown-preview.theme-atom-one-light :deep(pre) {
  background-color: #fafafa;
}

.markdown-preview.theme-atom-one-light :deep(code) {
  background-color: rgba(110, 118, 129, 0.4);
}

.markdown-preview.theme-atom-one-light :deep(table tr) {
  background-color: #fafafa;
}

.markdown-preview.theme-atom-one-light :deep(table tr:nth-child(2n)) {
  background-color: #f0f0f0;
}

.markdown-preview.theme-atom-one-light :deep(table th) {
  background-color: #f0f0f0;
}

.markdown-preview.theme-atom-one-light :deep(a) {
  color: #4078c0;
}

/* VS 主题 */
.markdown-preview.theme-vs {
  background-color: #ffffff;
  color: #000000;
}

.markdown-preview.theme-vs :deep(.hljs) {
  background-color: #f5f5f5;
}

.markdown-preview.theme-vs :deep(pre) {
  background-color: #f5f5f5;
}

.markdown-preview.theme-vs :deep(code) {
  background-color: rgba(0, 0, 0, 0.05);
}

.markdown-preview.theme-vs :deep(table tr:nth-child(2n)) {
  background-color: #f0f0f0;
}

.markdown-preview.theme-vs :deep(table th) {
  background-color: #f0f0f0;
}

/* VS 2015主题 */
.markdown-preview.theme-vs2015 {
  background-color: #1e1e1e;
  color: #d4d4d4;
}

.markdown-preview.theme-vs2015 :deep(.hljs) {
  background-color: #1e1e1e;
}

.markdown-preview.theme-vs2015 :deep(pre) {
  background-color: #1e1e1e;
}

.markdown-preview.theme-vs2015 :deep(code) {
  background-color: rgba(110, 118, 129, 0.4);
}

.markdown-preview.theme-vs2015 :deep(table tr) {
  background-color: #1e1e1e;
}

.markdown-preview.theme-vs2015 :deep(table tr:nth-child(2n)) {
  background-color: #252526;
}

.markdown-preview.theme-vs2015 :deep(table th) {
  background-color: #252526;
}

.markdown-preview.theme-vs2015 :deep(a) {
  color: #4fc1ff;
}

/* XCode 主题 */
.markdown-preview.theme-xcode {
  background-color: #ffffff;
  color: #000000;
}

.markdown-preview.theme-xcode :deep(.hljs) {
  background-color: #f5f5f5;
}

.markdown-preview.theme-xcode :deep(pre) {
  background-color: #f5f5f5;
}

.markdown-preview.theme-xcode :deep(code) {
  background-color: rgba(0, 0, 0, 0.05);
}

.markdown-preview.theme-xcode :deep(table tr:nth-child(2n)) {
  background-color: #f0f0f0;
}

.markdown-preview.theme-xcode :deep(table th) {
  background-color: #f0f0f0;
}

/* 复制按钮样式 */
.markdown-preview :deep(blockquote) {
  margin: 0 0 16px;
  padding: 0 1em;
  color: #57606a;
  border-left: 0.25em solid #d0d7de;
}

.markdown-preview :deep(blockquote > :first-child) {
  margin-top: 0;
}

.markdown-preview :deep(blockquote > :last-child) {
  margin-bottom: 0;
}

/* 表格样式 */
.markdown-preview :deep(table) {
  display: block;
  width: max-content;
  max-width: 100%;
  overflow: auto;
  border-spacing: 0;
  border-collapse: collapse;
  margin-bottom: 16px;
}

.markdown-preview :deep(table th) {
  font-weight: 600;
  background-color: #f6f8fa;
  padding: 6px 13px;
  border: 1px solid #d0d7de;
}

.markdown-preview :deep(table td) {
  padding: 6px 13px;
  border: 1px solid #d0d7de;
}

.markdown-preview :deep(table tr) {
  background-color: #ffffff;
  border-top: 1px solid #d0d7de;
}

.markdown-preview :deep(table tr:nth-child(2n)) {
  background-color: #f6f8fa;
}

/* 链接样式 */
.markdown-preview :deep(a) {
  color: #0969da;
  text-decoration: none;
}

.markdown-preview :deep(a:hover) {
  text-decoration: underline;
}

/* 图片样式 */
.markdown-preview :deep(img) {
  max-width: 100%;
  box-sizing: content-box;
  background-color: #ffffff;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* 水平线样式 */
.markdown-preview :deep(hr) {
  height: 0.25em;
  padding: 0;
  margin: 24px 0;
  background-color: #d0d7de;
  border: 0;
}

/* 任务列表样式 */
.markdown-preview :deep(input[type='checkbox']) {
  margin-right: 0.5em;
}

/* 删除线样式 */
.markdown-preview :deep(del) {
  color: #57606a;
}

/* 强调样式 */
.markdown-preview :deep(strong) {
  font-weight: 600;
}

.markdown-preview :deep(em) {
  font-style: italic;
}

/* 全屏模式样式 */
.markdown-preview-container.is-fullscreen .markdown-content-wrapper {
  height: 100vh;
}

.markdown-preview-container.is-fullscreen .markdown-preview {
  border-radius: 0;
  border: none;
  padding: 80px 32px 32px 32px;
}

/* 全屏且有目录时，调整内容区域 */
.markdown-preview-container.is-fullscreen:has(.markdown-toc-sidebar) .markdown-preview {
  padding-left: 32px;
}

.markdown-preview-container.is-fullscreen .markdown-toc-sidebar {
  display: block;
  border-radius: 0;
  border: none;
  border-right: 1px solid #e0e0e0;
  background-color: #ffffff;
  padding-top: 80px;
}

.markdown-preview-container.is-fullscreen .markdown-toolbar-floating {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 20;
  background-color: rgba(255, 255, 255, 0.98);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}
</style>
