<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue';
import { NButton, NDrawer, NSpin, NText, NUpload, NUploadDragger } from 'naive-ui';
import { documentApi } from '@/service/api/document';
import { useThemeStore } from '@/store/modules/theme';
import { compressImages } from '@/utils/imageCompress';
import SvgIcon from '@/components/custom/svg-icon.vue';
import type { Document } from '@/typings/api/document';
import { getDocumentDisplayType, getDocumentIcon } from '@/views/workflow/requirement-detail/utils/documentType';
import MarkdownRenderer from './MarkdownRenderer.vue';

interface Props {
  show: boolean;
  document: Document.Response | null;
  documents?: Document.Response[];
  requirementId: string;
  requirementCode?: string;
  loading?: boolean;
  getDownloadUrl: (doc: Document.Response) => string;
  width?: number | string;
  enableQuickUpload?: boolean; // 是否启用快速上传功能
  enableDelete?: boolean; // 是否启用删除功能
}

interface Emits {
  (e: 'update:show', value: boolean): void;
  (e: 'update:document', value: Document.Response | null): void;
  (e: 'documentUploaded'): void; // 文档上传后刷新列表
  (e: 'documentDeleted'): void; // 文档删除后刷新列表
}

const props = withDefaults(defineProps<Props>(), {
  documents: () => [],
  loading: false,
  width: 1100,
  enableQuickUpload: false,
  enableDelete: false
});

const emit = defineEmits<Emits>();
const themeStore = useThemeStore();

// 快速上传状态
const quickUploading = ref(false);
const quickUploadDragOver = ref(false);

// Markdown 文件内容
const markdownContent = ref<string>('');
const markdownLoading = ref(false);
const markdownError = ref<string>('');

// 图片 Blob URL（用于带认证的图片加载）
const imageUrl = ref<string>('');
const imageLoading = ref(false);

// 是否深色模式
const isDarkMode = computed(() => themeStore.darkMode);

// 使用 getDocumentDisplayType 工具函数判断文件类型
const displayType = computed(() => {
  if (!props.document) return 'other';
  return getDocumentDisplayType(props.document);
});

// 文件类型图标
const fileIcon = computed(() => getDocumentIcon(displayType.value));

// 下载 URL
const downloadUrl = computed(() => {
  if (!props.document) return '';
  return props.getDownloadUrl(props.document);
});

// 格式化文件大小
const formattedFileSize = computed(() => {
  if (!props.document) return '';
  const bytes = props.document.file_size;
  // 明确检查 null/undefined，允许 bytes 为 0
  if (bytes === null) return '-';
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${Math.round((bytes / k ** i) * 100) / 100} ${sizes[i]}`;
});

// 格式化更新时间
const formattedUpdateTime = computed(() => {
  if (!props.document || !props.document.updated_at) return '';
  const date = new Date(props.document.updated_at);
  if (Number.isNaN(date.getTime())) return '';
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return '刚刚更新';
  if (diffMins < 60) return `${diffMins} 分钟前更新`;
  if (diffHours < 24) return `${diffHours} 小时前更新`;
  if (diffDays < 7) return `${diffDays} 天前更新`;
  return date.toLocaleDateString('zh-CN');
});

// 内容统计（行数、字数）
const contentStats = computed(() => {
  if (displayType.value === 'markdown' && markdownContent.value) {
    const lines = markdownContent.value.split('\n').length;
    const chars = markdownContent.value.length;
    return { lines, chars };
  }
  return null;
});

// 侧边栏标题 - 显示需求编号或默认文本
const sidebarTitle = computed(() => {
  return props.requirementCode || '文档列表';
});

// 监听文档变化，加载 Markdown 或图片内容
watch(
  () => props.document,
  async newDoc => {
    // 清空之前的内容
    markdownContent.value = '';
    markdownError.value = '';

    // 释放旧的图片 Blob URL
    if (imageUrl.value) {
      URL.revokeObjectURL(imageUrl.value);
      imageUrl.value = '';
    }

    if (!newDoc) return;

    const docType = getDocumentDisplayType(newDoc);

    if (docType === 'markdown') {
      await loadMarkdownContent();
    } else if (docType === 'image') {
      await loadImageContent();
    }
  },
  { immediate: true }
);

// 加载图片内容（使用 API 层）
async function loadImageContent() {
  if (!props.document) return;

  imageLoading.value = true;

  try {
    // 使用 API 层下载图片 Blob
    const blob = await documentApi.downloadRequirementDocumentBlob(props.requirementId, props.document.id);
    imageUrl.value = URL.createObjectURL(blob);
  } catch (error) {
    console.error('加载图片失败:', error);
  } finally {
    imageLoading.value = false;
  }
}

// 组件卸载时释放 Blob URL
onUnmounted(() => {
  if (imageUrl.value) {
    URL.revokeObjectURL(imageUrl.value);
  }
});

// 加载 Markdown 文件内容
async function loadMarkdownContent() {
  if (!props.document) return;

  markdownLoading.value = true;
  markdownError.value = '';

  try {
    const content = await documentApi.downloadRequirementDocumentContent(props.requirementId, props.document.id);
    markdownContent.value = content;
  } catch (error) {
    console.error('加载 Markdown 文件失败:', error);
    markdownError.value = error instanceof Error ? error.message : '加载失败';
  } finally {
    markdownLoading.value = false;
  }
}

function handleDownload() {
  if (downloadUrl.value) {
    window.open(downloadUrl.value, '_blank');
  }
}

function handleDelete() {
  if (!props.document) return;

  window.$dialog?.warning({
    title: '确认删除',
    content: `确定要删除文档 "${props.document?.file_name || '未命名文档'}" 吗？此操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await documentApi.deleteRequirementDocument(props.requirementId, props.document.id);
        window.$message?.success('文档删除成功');
        // 触发删除事件，通知父组件刷新列表
        emit('documentDeleted');
        // 关闭抽屉
        handleClose();
      } catch {
        window.$message?.error('文档删除失败');
      }
    }
  });
}

function handleClose() {
  emit('update:show', false);
}

function handleSelectDocument(doc: Document.Response) {
  emit('update:document', doc);
}

function isDocumentActive(doc: Document.Response) {
  return props.document?.id === doc.id;
}

// 快速上传处理
async function handleQuickUpload(options: { fileList: Array<{ file: File }> }) {
  const files = options.fileList;
  if (files.length === 0) return;

  quickUploading.value = true;
  quickUploadDragOver.value = false;

  try {
    // 压缩图片并限制文件大小（1MB）
    const rawFiles = files.map(f => f.file);
    const compressedFiles = await compressImages(rawFiles, { maxSize: 1 * 1024 * 1024 });

    // 串行上传每个文件
    for (const file of compressedFiles) {
      // eslint-disable-next-line no-await-in-loop
      // 检查是否已存在同名文件
      const existingDoc = props.documents.find(doc => doc.file_name === file.name);

      if (existingDoc) {
        // 更新现有文档
        // eslint-disable-next-line no-await-in-loop
        await documentApi.updateRequirementDocument(props.requirementId, existingDoc.id, {
          file
        });
        window.$message?.success(`已更新文档：${file.name}`);
      } else {
        // 创建新文档
        // eslint-disable-next-line no-await-in-loop
        await documentApi.createForRequirement(props.requirementId, {
          file
        });
        window.$message?.success(`已上传文档：${file.name}`);
      }
    }

    // 触发刷新事件
    emit('documentUploaded');
  } catch (error) {
    console.error('快速上传失败:', error);
    window.$message?.error('上传失败，请重试');
  } finally {
    quickUploading.value = false;
  }
}

// 处理拖拽状态
function handleQuickUploadDragOver() {
  quickUploadDragOver.value = true;
}

function handleQuickUploadDragLeave() {
  quickUploadDragOver.value = false;
}

function handleQuickUploadDrop() {
  quickUploadDragOver.value = false;
}
</script>

<template>
  <NDrawer :show="show" :width="width" placement="right" @update:show="handleClose">
    <!-- 完全自定义布局，不使用 NDrawerContent 的插槽 -->
    <div class="doc-drawer-container" :class="{ 'dark-mode': isDarkMode }">
      <!-- 左侧边栏：文档列表 -->
      <div v-if="documents && documents.length > 0" class="doc-drawer-sidebar" :class="{ 'dark-mode': isDarkMode }">
        <div class="sidebar-header">
          <span class="sidebar-title">{{ sidebarTitle }}</span>
          <span class="sidebar-count">{{ documents.length }}</span>
        </div>
        <div class="sidebar-list">
          <div
            v-for="doc in documents"
            :key="doc.id"
            class="sidebar-item"
            :class="{ active: isDocumentActive(doc), 'dark-mode': isDarkMode }"
            @click="handleSelectDocument(doc)"
          >
            <SvgIcon :icon="getDocumentIcon(getDocumentDisplayType(doc))" class="sidebar-item-icon" />
            <span class="sidebar-item-name">{{ doc.file_name || '未命名文档' }}</span>
          </div>
        </div>

        <!-- 快速上传区域（仅需求详情页启用） -->
        <div v-if="enableQuickUpload" class="sidebar-upload">
          <NUpload
            :show-file-list="false"
            :multiple="true"
            :disabled="quickUploading"
            :custom-request="() => {}"
            @change="handleQuickUpload as any"
          >
            <NUploadDragger
              class="upload-dragger"
              :class="{ 'drag-over': quickUploadDragOver, 'dark-mode': isDarkMode }"
              @dragover.prevent="handleQuickUploadDragOver"
              @dragleave.prevent="handleQuickUploadDragLeave"
              @drop.prevent="handleQuickUploadDrop"
            >
              <NSpin :show="quickUploading" size="small">
                <SvgIcon icon="mdi:cloud-upload" class="upload-icon" />
                <div class="upload-text">拖拽文件上传</div>
              </NSpin>
            </NUploadDragger>
          </NUpload>
        </div>
      </div>

      <!-- 右侧主内容区 -->
      <div class="doc-drawer-main">
        <!-- Header: a.gui style -->
        <div class="doc-drawer-header">
          <!-- 左侧：文件信息 -->
          <div class="doc-header-left">
            <SvgIcon :icon="fileIcon" class="doc-icon" />
            <div class="doc-info">
              <h3 class="doc-title">{{ document?.file_name || '文档详情' }}</h3>
              <p class="doc-path">{{ formattedFileSize }}</p>
            </div>
          </div>

          <!-- 右侧：操作按钮 -->
          <div class="doc-header-right">
            <NButton v-if="enableDelete && document" size="medium" quaternary title="删除" @click="handleDelete">
              <template #icon>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                  <line x1="10" y1="11" x2="14" y2="11"></line>
                  <line x1="14" y1="15" x2="10" y2="15"></line>
                </svg>
              </template>
            </NButton>
            <NButton size="medium" quaternary title="下载" @click="handleDownload">
              <template #icon>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="7 10 12 15 17 10"></polyline>
                  <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
              </template>
            </NButton>
            <NButton size="medium" quaternary title="关闭" @click="handleClose">
              <template #icon>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </template>
            </NButton>
          </div>
        </div>

        <!-- Body: 内容预览区域 -->
        <div class="doc-drawer-body-middle">
          <div class="doc-drawer-body-scroll" :class="{ 'dark-mode': isDarkMode }">
            <NSpin :show="loading && !imageLoading">
              <div v-if="document" class="doc-content-wrapper" :class="{ 'dark-mode': isDarkMode }">
                <!-- 图片预览 -->
                <template v-if="displayType === 'image'">
                  <div class="preview-content">
                    <NSpin :show="imageLoading">
                      <img v-if="imageUrl" :src="imageUrl" :alt="document.file_name" class="preview-image" />
                      <div v-else class="preview-placeholder">
                        <SvgIcon icon="mdi:image" class="placeholder-icon" />
                        <p class="placeholder-text">加载图片中...</p>
                      </div>
                    </NSpin>
                  </div>
                </template>

                <!-- Markdown 预览 -->
                <template v-else-if="displayType === 'markdown'">
                  <NSpin :show="markdownLoading">
                    <div v-if="markdownError" class="preview-error">
                      <NText type="error">{{ markdownError }}</NText>
                    </div>
                    <MarkdownRenderer v-else-if="markdownContent" :content="markdownContent" />
                    <div v-else class="preview-empty">
                      <SvgIcon icon="mdi:language-markdown" class="empty-icon" />
                      <p>加载中...</p>
                    </div>
                  </NSpin>
                </template>

                <!-- PDF 预览 -->
                <template v-else-if="displayType === 'pdf'">
                  <div class="preview-content">
                    <iframe v-if="downloadUrl" :src="downloadUrl" class="preview-pdf" type="application/pdf" />
                    <div v-else class="preview-placeholder">
                      <SvgIcon icon="mdi:file-pdf-box" class="placeholder-icon" />
                      <p class="placeholder-text">无法预览 PDF，请下载后查看</p>
                    </div>
                  </div>
                </template>

                <!-- Word 预览 -->
                <template v-else-if="displayType === 'word'">
                  <div class="preview-placeholder">
                    <SvgIcon icon="mdi:file-word" class="placeholder-icon" />
                    <p class="placeholder-text">这是一个 Word 文档（.doc/.docx）</p>
                    <p class="placeholder-hint">请下载后使用 Microsoft Word 或兼容软件打开</p>
                    <NButton type="primary" secondary size="small" class="mt-3" @click="handleDownload">
                      下载文件
                    </NButton>
                  </div>
                </template>

                <!-- 其他类型 -->
                <template v-else>
                  <div class="preview-placeholder">
                    <SvgIcon icon="mdi:file-document" class="placeholder-icon" />
                    <p class="placeholder-text">不支持预览此文件类型</p>
                    <NButton type="primary" secondary size="small" class="mt-3" @click="handleDownload">
                      下载文件
                    </NButton>
                  </div>
                </template>
              </div>
            </NSpin>
          </div>
        </div>

        <!-- Footer: a.gui style -->
        <div class="doc-drawer-footer" :class="{ 'dark-mode': isDarkMode }">
          <div class="footer-left">
            <template v-if="contentStats">
              <span class="footer-text">{{ contentStats.lines }} 行</span>
              <span class="footer-text">{{ contentStats.chars }} 字符</span>
            </template>
          </div>
          <div class="footer-right">
            <span class="footer-text">{{ formattedUpdateTime }}</span>
          </div>
        </div>
      </div>
    </div>
  </NDrawer>
</template>

<style scoped>
/* ========== a.gui style exact copy with dark mode ========== */

/* 主容器 - 横向布局：左侧边栏 + 右侧主内容 */
.doc-drawer-container {
  display: flex;
  flex-direction: row;
  width: 100%;
  height: 100%;
  background: #ffffff;
}

.doc-drawer-container.dark-mode {
  background: var(--color-bg-dark);
}

/* ========== 左侧边栏：文档列表 ========== */
.doc-drawer-sidebar {
  width: 220px;
  flex-shrink: 0;
  border-right: 1px solid var(--color-border-subtle);
  background: #f9fafb;
  display: flex;
  flex-direction: column;
}

.doc-drawer-sidebar.dark-mode {
  border-right: 1px solid #374151;
  background: #1f2937;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border-subtle);
  height: 52px;
  background: #f3f4f6;
}

.doc-drawer-sidebar.dark-mode .sidebar-header {
  border-bottom: 1px solid #374151;
  background: var(--color-bg-dark);
}

.sidebar-title {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.doc-drawer-sidebar.dark-mode .sidebar-title {
  color: var(--color-border-default);
}

.sidebar-count {
  font-size: 12px;
  color: var(--color-text-secondary);
  background: var(--color-border-subtle);
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.doc-drawer-sidebar.dark-mode .sidebar-count {
  color: var(--color-text-tertiary);
  background: #374151;
}

.sidebar-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.sidebar-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1);
  margin-bottom: 4px;
}

.sidebar-item:hover {
  background: var(--color-border-subtle);
}

.doc-drawer-sidebar.dark-mode .sidebar-item:hover {
  background: #374151;
}

.sidebar-item.active {
  background: #dbeafe;
  color: var(--color-primary-active);
}

.doc-drawer-sidebar.dark-mode .sidebar-item.active {
  background: #1e40af;
  color: #93c5fd;
}

.sidebar-item-icon {
  font-size: 14px;
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.doc-drawer-sidebar.dark-mode .sidebar-item-icon {
  color: var(--color-text-tertiary);
}

.sidebar-item.active .sidebar-item-icon {
  color: var(--color-primary-active);
}

.doc-drawer-sidebar.dark-mode .sidebar-item.active .sidebar-item-icon {
  color: #93c5fd;
}

.sidebar-item-name {
  font-size: 13px;
  color: #374151;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.doc-drawer-sidebar.dark-mode .sidebar-item-name {
  color: var(--color-border-default);
}

.sidebar-item.active .sidebar-item-name {
  color: var(--color-primary-active);
  font-weight: 500;
}

.doc-drawer-sidebar.dark-mode .sidebar-item.active .sidebar-item-name {
  color: #93c5fd;
}

/* ========== 快速上传区域 ========== */
.sidebar-upload {
  padding: 12px;
  border-top: 1px solid var(--color-border-subtle);
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
}

.doc-drawer-sidebar.dark-mode .sidebar-upload {
  border-top: 1px solid #374151;
  background: linear-gradient(135deg, #0c4a6e 0%, #075985 100%);
}

.upload-dragger {
  padding: 16px 12px;
  border: 2px dashed #0ea5e9;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.8);
  transition: all 200ms ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 70px;
  box-shadow: 0 1px 3px rgba(14, 165, 233, 0.1);
}

.upload-dragger.dark-mode {
  background: rgba(30, 41, 59, 0.8);
  border-color: #38bdf8;
  box-shadow: 0 1px 3px rgba(56, 189, 248, 0.2);
}

.upload-dragger.drag-over {
  border-color: var(--color-primary);
  border-width: 3px;
  background: rgba(59, 130, 246, 0.1);
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.upload-dragger.drag-over.dark-mode {
  border-color: #60a5fa;
  background: rgba(59, 130, 246, 0.2);
  box-shadow: 0 4px 12px rgba(96, 165, 250, 0.4);
}

.upload-icon {
  font-size: 24px;
  color: #0ea5e9;
  margin-bottom: 6px;
}

.upload-dragger.dark-mode .upload-icon {
  color: #38bdf8;
}

.upload-dragger.drag-over .upload-icon {
  color: var(--color-primary);
  transform: scale(1.1);
}

.upload-text {
  font-size: 12px;
  font-weight: 500;
  color: #0369a1;
  text-align: center;
}

.upload-dragger.dark-mode .upload-text {
  color: #7dd3fc;
}

/* ========== 右侧主内容区 ========== */
.doc-drawer-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* ========== Header - a.gui CodeEditorHeader ========== */
.doc-drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
  flex-shrink: 0;
  padding: 6px 12px;
  border-bottom: 1px solid var(--color-border-subtle);
  height: 52px;
}

.doc-drawer-header.dark-mode {
  border-bottom: 1px solid #374151;
}

.doc-header-left {
  display: flex;
  min-width: 0;
  flex: 1 1 0%;
  align-items: center;
  gap: 8px;
}

.doc-icon {
  font-size: 12px;
  flex-shrink: 0;
  color: var(--color-text-secondary);
}

.doc-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.doc-title {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.doc-path {
  margin: 0;
  font-size: 11px;
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.doc-header-right {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 2px;
}

.doc-header-right button {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px;
  border-radius: 6px;
  color: #4b5563;
  transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

.doc-header-right button:hover {
  background-color: #f3f4f6;
  color: var(--color-text-primary);
}

/* ========== Body - a.gui CodeEditorSurface ========== */
/* 中间层 - 限制高度，overflow-hidden */
.doc-drawer-body-middle {
  flex: 1 1 0%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* 滚动层 - 可滚动的内容区域 */
.doc-drawer-body-scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.doc-drawer-body-scroll.dark-mode {
  background: var(--color-bg-dark);
}

/* 内容包装器 */
.doc-content-wrapper {
  flex: 1;
  min-height: 100%;
  background: #ffffff;
}

.doc-content-wrapper.dark-mode {
  background: var(--color-bg-dark);
}

.doc-content-wrapper.dark-mode {
  background: var(--color-bg-dark);
}

.preview-content {
  display: flex;
  justify-content: center;
  padding: 32px;
  background: #ffffff;
}

.doc-content-wrapper.dark-mode .preview-content {
  background: var(--color-bg-dark);
}

.preview-image {
  max-width: 100%;
  border-radius: 8px;
  box-shadow:
    0 1px 3px 0 rgba(0, 0, 0, 0.1),
    0 1px 2px 0 rgba(0, 0, 0, 0.06);
}

.preview-pdf {
  width: 100%;
  min-height: 500px;
  border: none;
}

.preview-error,
.preview-empty,
.preview-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  padding: 40px;
  text-align: center;
}

.empty-icon,
.placeholder-icon {
  font-size: 48px;
  color: var(--color-text-tertiary);
  margin-bottom: 16px;
}

.placeholder-text {
  margin: 0 0 4px 0;
  font-size: 14px;
  color: #374151;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.dark-mode .placeholder-text {
  color: var(--color-border-default);
}

.placeholder-hint {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-secondary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.dark-mode .placeholder-hint {
  color: var(--color-text-tertiary);
}

.mt-3 {
  margin-top: 12px;
}

/* ========== Footer - a.gui CodeEditorFooter ========== */
.doc-drawer-footer {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 6px 12px;
  border-top: 1px solid var(--color-border-subtle);
  background: #f3f4f6;
  line-height: 1;
}

.doc-drawer-footer.dark-mode {
  border-top: 1px solid #374151;
  background: #1f2937;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.footer-right {
  display: flex;
  align-items: center;
}

.footer-text {
  font-size: 12px;
  line-height: 16px;
  color: #4b5563;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.dark-mode .footer-text {
  color: var(--color-text-tertiary);
}

/* ========== Markdown Renderer - a.gui compatible ========== */
.doc-content-wrapper :deep(.markdown-body) {
  padding: 32px;
  background: #ffffff;
  color: var(--color-text-primary);
  font-size: 14px;
  line-height: 1.6;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  max-width: 896px; /* max-w-4xl = 56rem = 896px */
  margin: 0 auto;
}

.doc-content-wrapper.dark-mode :deep(.markdown-body) {
  background: var(--color-bg-dark);
  color: var(--color-border-subtle);
}

/* 标题 */
.doc-content-wrapper :deep(.markdown-body) h1,
.doc-content-wrapper :deep(.markdown-body) h2,
.doc-content-wrapper :deep(.markdown-body) h3,
.doc-content-wrapper :deep(.markdown-body) h4,
.doc-content-wrapper :deep(.markdown-body) h5,
.doc-content-wrapper :deep(.markdown-body) h6 {
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
  color: var(--color-text-primary);
}

.doc-content-wrapper :deep(.markdown-body) h1,
.doc-content-wrapper :deep(.markdown-body) h2 {
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border-subtle);
}

.doc-content-wrapper.dark-mode :deep(.markdown-body) h1,
.doc-content-wrapper.dark-mode :deep(.markdown-body) h2,
.doc-content-wrapper.dark-mode :deep(.markdown-body) h3,
.doc-content-wrapper.dark-mode :deep(.markdown-body) h4,
.doc-content-wrapper.dark-mode :deep(.markdown-body) h5,
.doc-content-wrapper.dark-mode :deep(.markdown-body) h6 {
  color: var(--color-border-subtle);
  border-bottom: 1px solid #374151;
}

/* 段落 */
.doc-content-wrapper :deep(.markdown-body) p {
  margin-top: 0;
  margin-bottom: 16px;
}

/* 行内代码 */
.doc-content-wrapper :deep(.markdown-body) code {
  padding: 2px 4px;
  background-color: #f3f4f6;
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace;
  font-size: 13px;
  color: var(--color-text-primary);
}

.doc-content-wrapper.dark-mode :deep(.markdown-body) code {
  background-color: #374151;
  color: var(--color-border-subtle);
}

/* 代码块 */
.doc-content-wrapper :deep(.markdown-body) pre {
  padding: 16px;
  overflow: auto;
  font-size: 13px;
  line-height: 1.45;
  background-color: #f6f8fa;
  border-radius: 6px;
  margin-bottom: 16px;
}

.doc-content-wrapper.dark-mode :deep(.markdown-body) pre {
  background-color: #1f2937;
}

.doc-content-wrapper :deep(.markdown-body) pre code {
  padding: 0;
  background-color: transparent;
}

/* 列表 */
.doc-content-wrapper :deep(.markdown-body) ul,
.doc-content-wrapper :deep(.markdown-body) ol {
  padding-left: 2em;
  margin-bottom: 16px;
}

/* 引用 */
.doc-content-wrapper :deep(.markdown-body) blockquote {
  padding: 0 1em;
  margin-left: 0;
  margin-bottom: 16px;
  color: var(--color-text-secondary);
  border-left: 4px solid var(--color-border-default);
}

.doc-content-wrapper.dark-mode :deep(.markdown-body) blockquote {
  color: var(--color-text-tertiary);
  border-left: 4px solid #4b5563;
}

/* 链接 */
.doc-content-wrapper :deep(.markdown-body) a {
  color: var(--color-primary-hover);
  text-decoration: none;
}

.doc-content-wrapper.dark-mode :deep(.markdown-body) a {
  color: #60a5fa;
}

.doc-content-wrapper :deep(.markdown-body) a:hover {
  text-decoration: underline;
}

/* 图片 */
.doc-content-wrapper :deep(.markdown-body) img {
  max-width: 100%;
  height: auto;
  border-radius: 6px;
}

/* 表格 */
.doc-content-wrapper :deep(.markdown-body) table {
  border-spacing: 0;
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 16px;
}

.doc-content-wrapper :deep(.markdown-body) table th,
.doc-content-wrapper :deep(.markdown-body) table td {
  padding: 6px 13px;
  border: 1px solid var(--color-border-default);
}

.doc-content-wrapper.dark-mode :deep(.markdown-body) table th,
.doc-content-wrapper.dark-mode :deep(.markdown-body) table td {
  border: 1px solid #4b5563;
}

.doc-content-wrapper :deep(.markdown-body) table th {
  font-weight: 600;
  background-color: #f3f4f6;
}

.doc-content-wrapper.dark-mode :deep(.markdown-body) table th {
  background-color: #1f2937;
}

/* KaTeX 深色模式 */
.dark-mode :deep(.katex) {
  color: var(--color-border-subtle);
}

/* 滚动条 */
.doc-content-wrapper::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.doc-content-wrapper::-webkit-scrollbar-track {
  background: transparent;
}

.doc-content-wrapper.dark-mode::-webkit-scrollbar-track {
  background: rgba(31, 41, 55, 0.5);
}

.doc-content-wrapper::-webkit-scrollbar-thumb {
  background-color: var(--color-border-default);
  border-radius: 4px;
}

.doc-content-wrapper.dark-mode::-webkit-scrollbar-thumb {
  background-color: rgba(107, 114, 128, 0.5);
}

.doc-content-wrapper::-webkit-scrollbar-thumb:hover {
  background-color: var(--color-text-tertiary);
}

.doc-content-wrapper.dark-mode::-webkit-scrollbar-thumb:hover {
  background-color: rgba(107, 114, 128, 0.7);
}
</style>
