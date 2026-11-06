<script setup lang="ts">
import { computed, ref } from 'vue';
import { NButton, NButtonGroup, NSpace, NText } from 'naive-ui';
import MarkdownRenderer from './MarkdownRenderer.vue';

interface Props {
  modelValue: string;
  placeholder?: string;
  rows?: number;
  maxHeight?: string;
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '支持 Markdown 语法...',
  rows: 8,
  maxHeight: '500px'
});

const emit = defineEmits<{
  'update:modelValue': [value: string];
}>();

const content = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value)
});

const showPreview = ref(false);

// 工具栏操作
function insertText(before: string, after: string = '', placeholder: string = '') {
  const textarea = document.querySelector('.markdown-textarea') as HTMLTextAreaElement;
  if (!textarea) return;

  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const selectedText = content.value.substring(start, end) || placeholder;

  const newText = content.value.substring(0, start) + before + selectedText + after + content.value.substring(end);
  content.value = newText;

  // 恢复焦点和光标位置
  textarea.focus();
  const newCursorPos = start + before.length + selectedText.length;
  textarea.setSelectionRange(newCursorPos, newCursorPos);
}

function insertBold() {
  insertText('**', '**', '粗体文本');
}

function insertItalic() {
  insertText('*', '*', '斜体文本');
}

function insertCode() {
  insertText('`', '`', '代码');
}

function insertCodeBlock() {
  insertText('\n```\n', '\n```\n', '代码块');
}

function insertLink() {
  insertText('[', '](url)', '链接文本');
}

function insertList() {
  insertText('\n- ', '', '列表项');
}

function insertQuote() {
  insertText('\n> ', '', '引用文本');
}

function insertHeader() {
  insertText('\n## ', '', '标题');
}

function insertTask() {
  insertText('\n- [ ] ', '', '待办事项');
}
</script>

<template>
  <div class="markdown-editor">
    <!-- 工具栏 -->
    <div class="toolbar">
      <NSpace :size="4">
        <NButtonGroup size="small">
          <NButton title="粗体 (Ctrl+B)" @click="insertBold">
            <icon-mdi-format-bold />
          </NButton>
          <NButton title="斜体 (Ctrl+I)" @click="insertItalic">
            <icon-mdi-format-italic />
          </NButton>
          <NButton title="行内代码 (Ctrl+`)" @click="insertCode">
            <icon-mdi-code-tags />
          </NButton>
          <NButton title="代码块" @click="insertCodeBlock">
            <icon-mdi-file-code-outline />
          </NButton>
        </NButtonGroup>

        <NButtonGroup size="small">
          <NButton title="链接" @click="insertLink">
            <icon-mdi-link-variant />
          </NButton>
          <NButton title="无序列表" @click="insertList">
            <icon-mdi-format-list-bulleted />
          </NButton>
          <NButton title="引用" @click="insertQuote">
            <icon-mdi-format-quote-close />
          </NButton>
          <NButton title="标题" @click="insertHeader">
            <icon-mdi-format-header-1 />
          </NButton>
          <NButton title="任务列表" @click="insertTask">
            <icon-mdi-checkbox-marked-outline />
          </NButton>
        </NButtonGroup>

        <NButtonGroup size="small">
          <NButton :type="showPreview ? 'default' : 'primary'" @click="showPreview = !showPreview">
            <icon-mdi-eye-outline v-if="!showPreview" />
            <icon-mdi-pencil-outline v-else />
            {{ showPreview ? '编辑' : '预览' }}
          </NButton>
        </NButtonGroup>
      </NSpace>

      <!-- Markdown 语法提示 -->
      <NPopover trigger="hover" width="300" placement="bottom-end" style="float: right">
        <template #trigger>
          <NButton text size="small">
            <icon-mdi-help-circle-outline />
            语法帮助
          </NButton>
        </template>
        <div class="syntax-help">
          <h4>Markdown 语法</h4>
          <ul>
            <li>
              <code>**粗体**</code>
              -
              <strong>粗体</strong>
            </li>
            <li>
              <code>*斜体*</code>
              -
              <em>斜体</em>
            </li>
            <li>
              <code>`代码`</code>
              -
              <code>行内代码</code>
            </li>
            <li>
              <code>```代码块```</code>
              - 代码块
            </li>
            <li>
              <code>[文本](url)</code>
              - 链接
            </li>
            <li>
              <code>- 列表项</code>
              - 无序列表
            </li>
            <li>
              <code># 标题</code>
              - 标题
            </li>
            <li>
              <code>> 引用</code>
              - 引用块
            </li>
            <li>
              <code>- [ ] 任务</code>
              - 任务列表
            </li>
            <li>
              <code>@username</code>
              - 提及用户
            </li>
            <li>
              <code>#OT-1</code>
              - 引用 Issue
            </li>
          </ul>
        </div>
      </NPopover>
    </div>

    <!-- 编辑/预览区域 -->
    <div class="editor-container" :style="{ maxHeight: props.maxHeight }">
      <!-- 编辑模式 -->
      <div v-show="!showPreview" class="editor-pane">
        <textarea v-model="content" class="markdown-textarea" :placeholder="props.placeholder" :rows="props.rows" />
      </div>

      <!-- 预览模式 -->
      <div v-show="showPreview" class="preview-pane">
        <MarkdownRenderer :content="content" />
        <NEmpty v-if="!content" description="输入内容后预览" size="small" />
      </div>
    </div>

    <!-- 提示文本 -->
    <div class="editor-footer">
      <NSpace justify="space-between">
        <NText depth="3" style="font-size: 12px">{{ content.length }} 字符</NText>
        <NText depth="3" style="font-size: 12px">支持 Markdown 语法 • Ctrl+Enter 快速提交</NText>
      </NSpace>
    </div>
  </div>
</template>

<style scoped>
.markdown-editor {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
}

.toolbar {
  padding: 8px 12px;
  background: #f9f9f9;
  border-bottom: 1px solid #e0e0e0;
}

.editor-container {
  overflow-y: auto;
  overflow-x: hidden;
}

.editor-pane,
.preview-pane {
  padding: 12px;
  min-height: 200px;
}

.markdown-textarea {
  width: 100%;
  min-height: 150px;
  padding: 8px;
  border: none;
  outline: none;
  resize: vertical;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.6;
  color: #24292f;
}

.markdown-textarea::placeholder {
  color: #999;
}

.preview-pane {
  background: #fff;
}

.editor-footer {
  padding: 8px 12px;
  background: #f9f9f9;
  border-top: 1px solid #e0e0e0;
}

/* Markdown 渲染器增强 */
.preview-pane :deep(.markdown-body) {
  color: #24292f;
  font-size: 14px;
  line-height: 1.6;
}

.syntax-help {
  font-size: 13px;
}

.syntax-help h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 600;
}

.syntax-help ul {
  margin: 0;
  padding-left: 20px;
}

.syntax-help li {
  margin: 4px 0;
  font-size: 12px;
}

.syntax-help code {
  background: #f5f5f5;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 11px;
}
</style>
