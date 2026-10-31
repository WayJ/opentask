<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { NAlert, NButton, NDescriptions, NDescriptionsItem, NModal, NSpace, NSpin, NTag } from 'naive-ui';
import { documentApi } from '@/service/api/document';
import SvgIcon from '@/components/custom/svg-icon.vue';
import type { Document } from '@/typings/api/document';
import { getDocumentDisplayType } from '../utils/documentType';
import MarkdownPreview from './MarkdownPreview.vue';

interface Props {
  show: boolean;
  document: Document.Response | null;
  loading?: boolean;
  getDownloadUrl: (doc: Document.Response) => string;
}

interface Emits {
  (e: 'update:show', value: boolean): void;
  (e: 'edit', document: Document.Response): void;
}

const props = withDefaults(defineProps<Props>(), {
  show: false,
  document: null,
  loading: false
});

const emit = defineEmits<Emits>();

const localShow = computed({
  get: () => props.show,
  set: value => emit('update:show', value)
});

// Markdown 文件内容
const markdownContent = ref<string>('');
const markdownLoading = ref(false);
const markdownError = ref<string>('');

// 使用 getDocumentDisplayType 工具函数判断文件类型
const displayType = computed(() => {
  if (!props.document) return 'other';
  return getDocumentDisplayType(props.document);
});

// 判断文件类型（兼容旧代码）
const fileType = computed(() => {
  if (!props.document) return 'unknown';
  const mime_type = props.document.file_type.toLowerCase();

  if (mime_type.startsWith('image/')) return 'image';
  if (mime_type === 'application/pdf') return 'pdf';
  if (mime_type.includes('word') || mime_type.includes('document')) return 'word';
  if (mime_type.includes('excel') || mime_type.includes('spreadsheet')) return 'excel';
  if (mime_type.includes('powerpoint') || mime_type.includes('presentation')) return 'powerpoint';
  if (mime_type.includes('text')) return 'text';

  return 'unknown';
});

// 监听文档变化，加载 Markdown 内容
watch(
  () => props.document,
  async newDoc => {
    if (newDoc && displayType.value === 'markdown') {
      await loadMarkdownContent();
    } else {
      markdownContent.value = '';
      markdownError.value = '';
    }
  },
  { immediate: true }
);

// 加载 Markdown 文件内容
async function loadMarkdownContent() {
  if (!props.document) return;

  markdownLoading.value = true;
  markdownError.value = '';

  try {
    // 使用统一的 API 服务获取文档内容
    const content = await documentApi.downloadRequirementDocumentContent(
      props.document.entity_id || '',
      props.document.id
    );

    markdownContent.value = content;
  } catch (error) {
    console.error('加载 Markdown 文件失败:', error);
    markdownError.value = error instanceof Error ? error.message : '加载失败';
  } finally {
    markdownLoading.value = false;
  }
}

// 文件类型图标
const fileIcon = computed(() => {
  switch (fileType.value) {
    case 'image':
      return 'mdi:image';
    case 'pdf':
      return 'mdi:file-pdf-box';
    case 'word':
      return 'mdi:file-word';
    case 'excel':
      return 'mdi:file-excel';
    case 'powerpoint':
      return 'mdi:file-powerpoint';
    case 'text':
      return 'mdi:file-document';
    default:
      return 'mdi:file';
  }
});

// 文件类型颜色
const fileIconColor = computed(() => {
  switch (fileType.value) {
    case 'pdf':
      return 'text-red-500';
    case 'word':
      return 'text-blue-500';
    case 'excel':
      return 'text-green-500';
    case 'powerpoint':
      return 'text-orange-500';
    default:
      return 'text-gray-500';
  }
});

// 文件类型文本
const fileTypeText = computed(() => {
  switch (fileType.value) {
    case 'image':
      return '图片';
    case 'pdf':
      return 'PDF 文档';
    case 'word':
      return 'Word 文档';
    case 'excel':
      return 'Excel 表格';
    case 'powerpoint':
      return 'PowerPoint 演示';
    case 'text':
      return '文本文件';
    default:
      return '文件';
  }
});

// 文件大小格式化
const formattedFileSize = computed(() => {
  if (!props.document) return '';
  const bytes = props.document.file_size;
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${Math.round((bytes / k ** i) * 100) / 100} ${sizes[i]}`;
});

// 下载 URL
const downloadUrl = computed(() => {
  if (!props.document) return '';
  return props.getDownloadUrl(props.document);
});

const statusText = computed(() => {
  if (!props.document) return '';
  switch (props.document.status) {
    case 'DRAFT':
      return '草稿';
    case 'PUBLISHED':
      return '已发布';
    case 'ARCHIVED':
      return '已归档';
    default:
      return props.document.status;
  }
});

const statusType = computed(() => (props.document?.status === 'PUBLISHED' ? 'success' : 'default'));

function handleEdit() {
  if (props.document) {
    emit('edit', props.document);
  }
}

function handleDownload() {
  if (downloadUrl.value) {
    window.open(downloadUrl.value, '_blank');
  }
}
</script>

<template>
  <NModal v-model:show="localShow" preset="card" title="文档详情" style="width: 700px">
    <NSpin :show="loading">
      <div v-if="document">
        <NDescriptions>
          <NDescriptionsItem label="文件名">
            <div class="flex items-center gap-2">
              <SvgIcon :icon="fileIcon" class="text-lg" :class="[fileIconColor]" />
              {{ document.file_name }}
            </div>
          </NDescriptionsItem>
          <NDescriptionsItem label="文件类型">{{ fileTypeText }}</NDescriptionsItem>
          <NDescriptionsItem label="文件大小">{{ formattedFileSize }}</NDescriptionsItem>
          <NDescriptionsItem label="状态">
            <NTag :type="statusType">{{ statusText }}</NTag>
          </NDescriptionsItem>
          <NDescriptionsItem label="更新时间">
            {{ new Date(document.updated_at).toLocaleString() }}
          </NDescriptionsItem>
        </NDescriptions>

        <div class="mt-4">
          <h4>文件预览</h4>
          <div class="document-preview-wrapper">
            <!-- 图片预览 -->
            <template v-if="displayType === 'image'">
              <img :src="downloadUrl" :alt="document.file_name" class="document-image" />
            </template>

            <!-- Markdown 预览 -->
            <template v-else-if="displayType === 'markdown'">
              <NSpin :show="markdownLoading">
                <NAlert v-if="markdownError" type="error" :title="markdownError" class="mb-3" />
                <MarkdownPreview
                  v-else-if="markdownContent"
                  :content="markdownContent"
                  :file-name="document.file_name"
                  :download-url="downloadUrl"
                />
                <div v-else class="document-file-preview">
                  <SvgIcon icon="mdi:language-markdown" class="file-icon-large text-gray-500" />
                  <p class="mt-3">加载中...</p>
                </div>
              </NSpin>
            </template>

            <!-- PDF 预览 -->
            <template v-else-if="displayType === 'pdf'">
              <iframe v-if="downloadUrl" :src="downloadUrl" class="pdf-preview" type="application/pdf">
                <div class="document-file-preview">
                  <SvgIcon icon="mdi:file-pdf-box" class="file-icon-large text-red-500" />
                  <p class="mt-3">无法预览 PDF，请下载后查看</p>
                  <NButton type="primary" secondary @click="handleDownload">下载文件</NButton>
                </div>
              </iframe>
            </template>

            <!-- Word 预览 -->
            <template v-else-if="displayType === 'word'">
              <div class="document-file-preview">
                <SvgIcon icon="mdi:file-word" class="file-icon-large text-blue-500" />
                <p class="mt-3">这是一个 Word 文档（.doc/.docx）</p>
                <p class="mt-2 text-sm text-gray-500">请下载后使用 Microsoft Word 或兼容软件打开</p>
                <NButton type="primary" secondary class="mt-3" @click="handleDownload">下载文件</NButton>
              </div>
            </template>

            <!-- Excel 预览 -->
            <template v-else-if="fileType === 'excel'">
              <div class="document-file-preview">
                <SvgIcon icon="mdi:file-excel" class="file-icon-large text-green-500" />
                <p class="mt-3">这是一个 Excel 表格</p>
                <NButton type="primary" secondary @click="handleDownload">下载文件</NButton>
              </div>
            </template>

            <!-- PowerPoint 预览 -->
            <template v-else-if="fileType === 'powerpoint'">
              <div class="document-file-preview">
                <SvgIcon icon="mdi:file-powerpoint" class="file-icon-large text-orange-500" />
                <p class="mt-3">这是一个 PowerPoint 演示</p>
                <NButton type="primary" secondary @click="handleDownload">下载文件</NButton>
              </div>
            </template>

            <!-- 其他类型 -->
            <template v-else>
              <div class="document-file-preview">
                <SvgIcon icon="mdi:file" class="file-icon-large text-gray-500" />
                <p class="mt-3">不支持预览此文件类型</p>
                <NButton type="primary" secondary @click="handleDownload">下载文件</NButton>
              </div>
            </template>
          </div>
        </div>
      </div>
    </NSpin>
    <template #footer>
      <NSpace justify="end">
        <NButton @click="localShow = false">关闭</NButton>
        <NButton type="primary" @click="handleEdit">编辑</NButton>
      </NSpace>
    </template>
  </NModal>
</template>

<style scoped>
.mt-4 {
  margin-top: 16px;
}

.mb-3 {
  margin-bottom: 12px;
}

.mt-3 {
  margin-top: 12px;
}

.mt-2 {
  margin-top: 8px;
}

.document-preview-wrapper {
  min-height: 200px;
  max-height: 500px;
  overflow-y: auto;
  padding: 16px;
  background-color: #fafafa;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
}

.document-preview-wrapper h4 {
  margin-bottom: 12px;
  color: #333;
}

.document-image {
  max-width: 100%;
  max-height: 500px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.pdf-preview {
  width: 100%;
  min-height: 500px;
  max-height: 500px;
  border: none;
  border-radius: 8px;
}

.document-file-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  padding: 32px;
}

.file-icon-large {
  font-size: 64px;
}

.flex {
  display: flex;
}

.items-center {
  align-items: center;
}

.gap-2 {
  gap: 8px;
}

.text-lg {
  font-size: 18px;
}

.text-sm {
  font-size: 14px;
}

.text-blue-500 {
  color: var(--color-primary);
}

.text-red-500 {
  color: var(--color-danger);
}

.text-green-500 {
  color: var(--color-success);
}

.text-orange-500 {
  color: #f97316;
}

.text-gray-500 {
  color: var(--color-text-secondary);
}
</style>
