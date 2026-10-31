<script setup lang="ts">
import { computed } from 'vue';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js/lib/common';

interface EmbeddedTask {
  id: string;
  title: string;
  status: string;
  createdAt: string;
}

interface Props {
  content: string;
  embeddedTasks?: EmbeddedTask[];
}

const props = withDefaults(defineProps<Props>(), {
  embeddedTasks: () => []
});

// 初始化 markdown-it
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: true, // 单个换行符转换为 <br>
  highlight: (str: string, lang: string) => {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre class="hljs"><code class="language-${lang}">${hljs.highlight(str, { language: lang, ignoreIllegals: true }).value}</code></pre>`;
      } catch (err) {
        console.error('Highlight error:', err);
      }
    }
    return '';
  }
});

const renderedMarkdown = computed(() => {
  // 使用 markdown-it 渲染 markdown
  let html = md.render(props.content) as string;

  // 替换任务卡片标记
  props.embeddedTasks.forEach(task => {
    const marker = `[TASK:${task.id}]`;
    const taskCardHtml = `
      <div class="embedded-task-card" onclick="window.open('/mission-center/tasks/${task.id}', '_blank')">
        <div class="task-header">
          <span class="task-id">#${task.id.substring(0, 8)}</span>
          <span class="task-status">${task.status}</span>
        </div>
        <div class="task-title">${task.title}</div>
      </div>
    `;
    html = html.replace(marker, taskCardHtml);
  });

  return html;
});
</script>

<template>
  <div class="comment-display">
    <div class="markdown-body" v-html="renderedMarkdown"></div>
  </div>
</template>

<style scoped>
/* 使用全局 markdown-body 样式，只保留特殊的任务卡片样式 */

/* 嵌入任务卡片样式 */
.embedded-task-card {
  display: inline-flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 4px;
  cursor: pointer;
  color: white;
  margin: 6px 0;
  transition:
    transform 0.2s,
    box-shadow 0.2s;
  font-size: 12px;
}

.embedded-task-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.task-header {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
}

.task-title {
  font-size: 12px;
  font-weight: 500;
}
</style>
