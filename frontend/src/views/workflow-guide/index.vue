<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { NCard } from 'naive-ui';
import MarkdownIt from 'markdown-it';

// 从 public 文件夹加载 markdown 文档
const markdownContent = ref('');
const isLoading = ref(true);
const loadError = ref<string | null>(null);

// 初始化 markdown-it
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true
});

// 加载 markdown 文档
onMounted(async () => {
  try {
    const response = await fetch('/docs/OPENTASK_WORKFLOW_GUIDE.md');
    if (!response.ok) {
      throw new Error(`Failed to load workflow guide: ${response.statusText}`);
    }
    markdownContent.value = await response.text();
  } catch (error) {
    console.error('Error loading workflow guide:', error);
    loadError.value = error instanceof Error ? error.message : 'Unknown error';
  } finally {
    isLoading.value = false;
  }
});

const renderedHtml = computed(() => {
  return md.render(markdownContent.value);
});
</script>

<template>
  <div class="workflow-docs-container">
    <NCard title="OpenTask Workflow 使用指南" :bordered="false">
      <!-- 加载状态 -->
      <div v-if="isLoading" class="loading-state">
        <p>正在加载工作流指南...</p>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="loadError" class="error-state">
        <p>⚠️ 加载失败: {{ loadError }}</p>
        <p class="error-hint">
          请确保文档文件位于
          <code>/docs/OPENTASK_WORKFLOW_GUIDE.md</code>
        </p>
      </div>

      <!-- 正常渲染 -->
      <div v-else-if="renderedHtml" class="markdown-content" v-html="renderedHtml" />
    </NCard>
  </div>
</template>

<style scoped>
.workflow-docs-container {
  padding: 20px;
  width: 100%;
  max-width: 100%;
}

.loading-state,
.error-state {
  padding: 40px;
  text-align: center;
  color: #666;
}

.error-state {
  color: #d32f2f;
}

.error-hint {
  margin-top: 10px;
  font-size: 0.9em;
  color: #666;
}

.error-hint code {
  background-color: #f6f8fa;
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-family: 'Courier New', Courier, monospace;
}

.markdown-content {
  line-height: 1.6;
  color: #333;
}

.markdown-content :deep(h1) {
  font-size: 2em;
  font-weight: bold;
  margin-top: 1em;
  margin-bottom: 0.5em;
  border-bottom: 1px solid #eee;
  padding-bottom: 0.3em;
}

.markdown-content :deep(h2) {
  font-size: 1.5em;
  font-weight: bold;
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  border-bottom: 1px solid #eee;
  padding-bottom: 0.3em;
}

.markdown-content :deep(h3) {
  font-size: 1.25em;
  font-weight: bold;
  margin-top: 1em;
  margin-bottom: 0.5em;
}

.markdown-content :deep(p) {
  margin-bottom: 1em;
}

.markdown-content :deep(code) {
  background-color: #f6f8fa;
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.9em;
}

.markdown-content :deep(pre) {
  background-color: #f6f8fa;
  padding: 16px;
  border-radius: 6px;
  overflow-x: auto;
  margin-bottom: 1em;
}

.markdown-content :deep(pre code) {
  background-color: transparent;
  padding: 0;
  border-radius: 0;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin-bottom: 1em;
  padding-left: 2em;
}

.markdown-content :deep(li) {
  margin-bottom: 0.5em;
}

.markdown-content :deep(blockquote) {
  border-left: 4px solid #ddd;
  padding-left: 1em;
  margin: 1em 0;
  color: #666;
}

.markdown-content :deep(a) {
  color: #0969da;
  text-decoration: none;
}

.markdown-content :deep(a:hover) {
  text-decoration: underline;
}

.markdown-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 1em;
}

.markdown-content :deep(table th),
.markdown-content :deep(table td) {
  border: 1px solid #ddd;
  padding: 8px 12px;
  text-align: left;
}

.markdown-content :deep(table th) {
  background-color: #f6f8fa;
  font-weight: bold;
}
</style>
