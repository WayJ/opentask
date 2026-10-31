<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import {
  NAlert,
  NButton,
  NButtonGroup,
  NDescriptions,
  NDescriptionsItem,
  NDrawer,
  NDrawerContent,
  NEmpty,
  NInput,
  NList,
  NListItem,
  NModal,
  NSpace,
  NSpin,
  NTag,
  NThing
} from 'naive-ui';
import MarkdownRenderer from './MarkdownRenderer.vue';

interface Props {
  modelValue: string;
  kbId: string;
  docId: string;
  placeholder?: string;
  readOnly?: boolean;
  height?: string;
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '请输入 Markdown 内容...',
  readOnly: false,
  height: '600px'
});

const emit = defineEmits<{
  'update:modelValue': [value: string];
  save: [content: string, message: string];
  'status-change': [status: string];
}>();

// Editor 相关
const editorContainer = ref<HTMLElement>();
let editorInstance: monaco.editor.IStandaloneCodeEditor | null = null;

// 状态管理
const loading = ref(false);
const error = ref('');
const showPreview = ref(false);
const isDirty = ref(false);

// Git 相关状态
const gitStatus = ref<Api.Knowledge.GitStatus | null>(null);
const commitMessage = ref('');
const submitting = ref(false);

// 历史记录相关
const showHistory = ref(false);
const historyList = ref<Api.Knowledge.DocumentHistory[]>([]);
const loadingHistory = ref(false);

// Diff 相关
const showDiff = ref(false);
const diffContent = ref<Api.Knowledge.DocumentDiff | null>(null);
const loadingDiff = ref(false);

// 初始化 Monaco Editor
function initEditor() {
  if (!editorContainer.value) return;

  // 注册 Markdown 语言
  monaco.languages.register({ id: 'markdown' });

  // 配置 Markdown 主题
  monaco.editor.defineTheme('markdown-theme', {
    base: 'vs',
    inherit: true,
    rules: [],
    colors: {
      'editor.background': '#ffffff',
      'editor.foreground': '#24292f'
    }
  });

  // 创建编辑器实例
  editorInstance = monaco.editor.create(editorContainer.value, {
    value: props.modelValue,
    language: 'markdown',
    theme: 'markdown-theme',
    readOnly: props.readOnly,
    automaticLayout: true,
    minimap: { enabled: true },
    fontSize: 14,
    lineHeight: 21,
    lineNumbers: 'on',
    scrollBeyondLastLine: false,
    wordWrap: 'on',
    formatOnPaste: true,
    formatOnType: true,
    tabSize: 2,
    renderWhitespace: 'selection',
    bracketPairColorization: { enabled: true },
    guides: {
      bracketPairs: true,
      indentation: true
    }
  });

  // 监听内容变化
  editorInstance.onDidChangeModelContent(() => {
    if (editorInstance) {
      const value = editorInstance.getValue();
      isDirty.value = value !== props.modelValue;
      emit('update:modelValue', value);
    }
  });

  // 添加快捷键
  // eslint-disable-next-line no-bitwise
  editorInstance.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
    handleSave();
  });

  emit('status-change', 'ready');
}

// 加载 Git 仓库原始内容
async function loadFromGit() {
  loading.value = true;
  error.value = '';

  try {
    const { fetchDocumentRawContent } = await import('@/service/api/knowledge');
    const { data, error: err } = await fetchDocumentRawContent(props.kbId, props.docId);

    if (err || !data) {
      throw new Error('加载文档失败');
    }

    // 更新编辑器内容
    if (editorInstance && data !== props.modelValue) {
      editorInstance.setValue(data);
      isDirty.value = false;
    }

    emit('status-change', 'loaded');
  } catch (e: any) {
    error.value = e.message || '加载失败';
    emit('status-change', 'error');
  } finally {
    loading.value = false;
  }
}

// 加载 Git 状态
async function loadGitStatus() {
  try {
    const { fetchKnowledgeBaseStatus } = await import('@/service/api/knowledge');
    const { data } = await fetchKnowledgeBaseStatus(props.kbId);

    if (data) {
      gitStatus.value = data;
    }
  } catch (e) {
    console.error('加载 Git 状态失败:', e);
  }
}

// 保存到 Git 仓库
async function handleSave() {
  if (!editorInstance || !commitMessage.value.trim()) {
    window.$message?.warning('请输入提交信息');
    return;
  }

  submitting.value = true;
  error.value = '';

  try {
    const content = editorInstance.getValue();
    const { commitDocument } = await import('@/service/api/knowledge');

    const { data, error: err } = await commitDocument(props.kbId, props.docId, {
      content,
      message: commitMessage.value,
      author: 'admin'
    });

    if (err || !data) {
      throw new Error('提交失败');
    }

    window.$message?.success('提交成功');
    isDirty.value = false;
    commitMessage.value = '';

    // 重新加载状态和历史
    await loadGitStatus();
    await loadHistory();

    emit('save', content, commitMessage.value);
    emit('status-change', 'committed');
  } catch (e: any) {
    error.value = e.message || '提交失败';
    window.$message?.error(error.value);
  } finally {
    submitting.value = false;
  }
}

// 加载历史记录
async function loadHistory() {
  loadingHistory.value = true;

  try {
    const { fetchDocumentHistory } = await import('@/service/api/knowledge');
    const { data } = await fetchDocumentHistory(props.kbId, props.docId, 20);

    if (data) {
      historyList.value = data;
    }
  } catch (e) {
    console.error('加载历史失败:', e);
  } finally {
    loadingHistory.value = false;
  }
}

// 显示/隐藏历史记录
function toggleHistory() {
  showHistory.value = !showHistory.value;
  if (showHistory.value && historyList.value.length === 0) {
    loadHistory();
  }
}

// 加载 Diff
async function loadDiff(commitA?: string, commitB?: string) {
  loadingDiff.value = true;

  try {
    const { fetchDocumentDiff } = await import('@/service/api/knowledge');
    const { data } = await fetchDocumentDiff(props.kbId, props.docId, {
      commit_a: commitA,
      commit_b: commitB
    });

    if (data) {
      diffContent.value = data;
      showDiff.value = true;
    }
  } catch (e) {
    console.error('加载 Diff 失败:', e);
  } finally {
    loadingDiff.value = false;
  }
}

// 切换预览模式
function togglePreview() {
  showPreview.value = !showPreview.value;
}

// 格式化文档
function formatDocument() {
  if (editorInstance) {
    editorInstance.getAction('editor.action.formatDocument')?.run();
  }
}

// 监听 modelValue 变化
watch(
  () => props.modelValue,
  newValue => {
    if (editorInstance && newValue !== editorInstance.getValue()) {
      editorInstance.setValue(newValue);
      isDirty.value = false;
    }
  }
);

// 组件挂载
onMounted(async () => {
  initEditor();
  await loadFromGit();
  await loadGitStatus();
});

// 组件卸载
onBeforeUnmount(() => {
  if (editorInstance) {
    editorInstance.dispose();
    editorInstance = null;
  }
});
</script>

<template>
  <div class="monaco-markdown-editor">
    <!-- 错误提示 -->
    <NAlert v-if="error" type="error" :title="error" closable class="mb-4" @close="error = ''" />

    <!-- 工具栏 -->
    <div class="toolbar">
      <NSpace :size="8" justify="space-between">
        <!-- 左侧按钮组 -->
        <NSpace :size="4">
          <!-- Git 操作 -->
          <NButtonGroup size="small">
            <NButton
              :type="isDirty ? 'primary' : 'default'"
              :loading="submitting"
              :disabled="!isDirty || !commitMessage.trim()"
              @click="handleSave"
            >
              <template #icon>
                <icon-mdi:content-save />
              </template>
              提交 (Ctrl+S)
            </NButton>
            <NButton @click="toggleHistory">
              <template #icon>
                <icon-mdi:history />
              </template>
              历史
            </NButton>
            <NButton @click="formatDocument">
              <template #icon>
                <icon-mdi:format-align-left />
              </template>
              格式化
            </NButton>
          </NButtonGroup>

          <!-- 视图切换 -->
          <NButtonGroup size="small">
            <NButton :type="showPreview ? 'primary' : 'default'" @click="togglePreview">
              <template #icon>
                <icon-mdi:eye-outline v-if="!showPreview" />
                <icon-mdi:pencil-outline v-else />
              </template>
              {{ showPreview ? '编辑' : '预览' }}
            </NButton>
          </NButtonGroup>
        </NSpace>

        <!-- 右侧状态信息 -->
        <NSpace v-if="gitStatus" :size="8">
          <NTag size="small" type="info">
            <template #icon>
              <icon-mdi:source-branch />
            </template>
            {{ gitStatus.branch }}
          </NTag>
          <NTag size="small" :type="gitStatus.is_dirty ? 'warning' : 'success'">
            <template #icon>
              <icon-mdi:check-circle v-if="!gitStatus.is_dirty" />
              <icon-mdi:alert-circle v-else />
            </template>
            {{ gitStatus.is_dirty ? '未提交' : '已提交' }}
          </NTag>
        </NSpace>
      </NSpace>
    </div>

    <!-- 提交信息输入 -->
    <div v-if="isDirty" class="commit-message-bar">
      <NSpace vertical :size="0">
        <NInput
          v-model:value="commitMessage"
          placeholder="输入提交信息（例如：修复文档错误、更新内容等）"
          @keyup.enter.ctrl="handleSave"
        />
        <NText depth="3" style="font-size: 12px">按 Ctrl+Enter 快速提交</NText>
      </NSpace>
    </div>

    <!-- 主编辑区域 -->
    <div class="editor-wrapper" :style="{ height: props.height }">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-overlay">
        <NSpin size="large" description="加载中..." />
      </div>

      <!-- 编辑器 -->
      <div v-show="!showPreview" ref="editorContainer" class="monaco-editor-container" />

      <!-- 预览 -->
      <div v-show="showPreview" class="preview-container">
        <MarkdownRenderer :content="props.modelValue" />
        <NEmpty v-if="!props.modelValue" description="暂无内容" />
      </div>
    </div>

    <!-- 历史记录侧边栏 -->
    <NDrawer v-model:show="showHistory" :width="400" placement="right">
      <NDrawerContent title="文档历史" closable>
        <NSpin :show="loadingHistory">
          <NList v-if="historyList.length > 0" hoverable clickable>
            <NListItem v-for="item in historyList" :key="item.sha">
              <template #prefix>
                <icon-mdi:source-commit class="text-icon" />
              </template>
              <NThing :title="item.message" :description="`${item.author} • ${item.timestamp}`" />
              <template #suffix>
                <NButton size="small" @click="loadDiff(item.sha)">查看变更</NButton>
              </template>
            </NListItem>
          </NList>
          <NEmpty v-else description="暂无历史记录" />
        </NSpin>
      </NDrawerContent>
    </NDrawer>

    <!-- Diff 查看器 -->
    <NModal v-model:show="showDiff" preset="card" title="文档变更" style="width: 80vw; max-width: 1200px">
      <NSpin :show="loadingDiff">
        <div v-if="diffContent" class="diff-viewer">
          <NDescriptions :column="2" bordered>
            <NDescriptionsItem label="文件路径">
              {{ diffContent.file_path }}
            </NDescriptionsItem>
            <NDescriptionsItem label="提交">
              {{ diffContent.commit_a || '工作区' }} → {{ diffContent.commit_b || '最新' }}
            </NDescriptionsItem>
          </NDescriptions>
          <div class="diff-content mt-4">
            <pre class="diff-text">{{ diffContent.diff }}</pre>
          </div>
        </div>
      </NSpin>
    </NModal>
  </div>
</template>

<style scoped>
.monaco-markdown-editor {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
  background: #fff;
}

.toolbar {
  padding: 8px 12px;
  background: #f9f9f9;
  border-bottom: 1px solid #e0e0e0;
}

.commit-message-bar {
  padding: 8px 12px;
  background: #fffbeb;
  border-bottom: 1px solid #fcd34d;
}

.editor-wrapper {
  position: relative;
  overflow: hidden;
}

.monaco-editor-container {
  width: 100%;
  height: 100%;
}

.preview-container {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  padding: 20px;
  background: #fff;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}

.diff-viewer {
  max-height: 70vh;
  overflow-y: auto;
}

.diff-content {
  padding: 12px;
  background: #f5f5f5;
  border-radius: 4px;
}

.diff-text {
  margin: 0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
