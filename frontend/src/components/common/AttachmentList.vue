<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import {
  NButton,
  NEmpty,
  NImage,
  NImageGroup,
  NPopconfirm,
  NSpin,
  NText,
  NUpload,
  NUploadDragger,
  useMessage
} from 'naive-ui';
import { Icon as Iconify } from '@iconify/vue';
import { issueApi } from '@/service/api/issue';
import type { Api } from '@/typings/api';
import {
  attachmentAccessDeniedMessage,
  toBrowserAttachmentUrl
} from '@/utils/attachmentUrls';
import ConversationViewer from './ConversationViewer.vue';

interface Props {
  issueId: string;
  /** E69: when set, upload/delete target comment attachments */
  commentId?: string;
  attachments?: Api.Document.Response[];
  readonly?: boolean;
}

interface Emits {
  (e: 'refresh'): void;
}

const props = withDefaults(defineProps<Props>(), {
  commentId: undefined,
  attachments: () => [],
  readonly: false
});

const emit = defineEmits<Emits>();
const message = useMessage();

const uploading = ref(false);
const uploadListRef = ref();

// 判断是否为图片类型
const isImage = (fileType: string, fileName: string) => {
  const imageTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp', 'image/svg+xml'];
  const imageExts = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp'];
  return imageTypes.includes(fileType) || imageExts.some(ext => fileName.toLowerCase().endsWith(ext));
};

const isJsonlFile = (fileName: string) => {
  return fileName.toLowerCase().endsWith('.jsonl');
};

// 格式化文件大小
const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / k ** i).toFixed(1)} ${sizes[i]}`;
};

// 上传前验证
const beforeUpload = (data: { file: { file?: File; name?: string; size?: number } }) => {
  const file = data.file.file || data.file;
  if (!file) return false;

  // 限制文件大小为 10MB
  const maxSize = 10 * 1024 * 1024;
  if (file.size > maxSize) {
    message.error('文件大小不能超过 10MB');
    return false;
  }

  return true;
};

// 处理文件上传
const handleUpload = async ({ file }: { file: { file?: File } }) => {
  const uploadFile = file.file;
  if (!uploadFile) return;

  uploading.value = true;
  try {
    if (props.commentId) {
      await issueApi.uploadCommentAttachment(props.issueId, props.commentId, { file: uploadFile });
    } else {
      await issueApi.uploadAttachment(props.issueId, { file: uploadFile });
    }
    message.success('附件上传成功');
    emit('refresh');
    // 清空上传列表
    if (uploadListRef.value) {
      uploadListRef.value.clear();
    }
  } catch (error) {
    console.error('上传附件失败:', error);
    message.error('附件上传失败');
  } finally {
    uploading.value = false;
  }
};

// 处理删除附件
const handleDelete = async (attachmentId: string) => {
  try {
    if (props.commentId) {
      await issueApi.deleteCommentAttachment(props.issueId, props.commentId, attachmentId);
    } else {
      await issueApi.deleteAttachment(props.issueId, attachmentId);
    }
    message.success('附件删除成功');
    emit('refresh');
  } catch (error) {
    console.error('删除附件失败:', error);
    message.error('附件删除失败');
  }
};

// E66: signed preview URLs for <img> / ConversationViewer (no naked public URLs)
const previewUrlMap = ref<Record<string, string>>({});
const previewError = ref<string | null>(null);

async function refreshSignedPreviewUrls() {
  previewError.value = null;
  const next: Record<string, string> = {};
  const list = props.attachments || [];
  for (const att of list) {
    if (!isImage(att.file_type, att.file_name) && !isJsonlFile(att.file_name)) {
      continue;
    }
    try {
      const purpose = isImage(att.file_type, att.file_name) ? 'preview' : 'download';
      const { data, error } = await issueApi.createAttachmentSignedUrl(att.id, purpose);
      if (error) {
        const status = (error as any)?.response?.status ?? (error as any)?.status ?? 0;
        previewError.value = attachmentAccessDeniedMessage(status || 404);
        console.error('签发附件签名 URL 失败:', error);
        continue;
      }
      if (data?.url) {
        next[att.id] = toBrowserAttachmentUrl(data.url);
      }
    } catch (error: any) {
      const status = error?.response?.status ?? error?.status ?? 0;
      previewError.value = attachmentAccessDeniedMessage(status || 404);
      console.error('签发附件签名 URL 失败:', error);
    }
  }
  previewUrlMap.value = next;
}

watch(
  () => props.attachments,
  () => {
    void refreshSignedPreviewUrls();
  },
  { deep: true }
);

onMounted(() => {
  void refreshSignedPreviewUrls();
});

const getAttachmentPreviewUrl = (attachmentId: string) => {
  return previewUrlMap.value[attachmentId] || '';
};

// E66: explicit download via authenticated blob fetch
const handleDownload = async (attachment: Api.Document.Response) => {
  try {
    const blob = await issueApi.downloadAttachmentBlob(attachment.id);
    // downloadRequest (createRequest) returns Blob directly on success
    const objectUrl = URL.createObjectURL(blob as Blob);
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = attachment.file_name;
    link.click();
    URL.revokeObjectURL(objectUrl);
  } catch (error: any) {
    const status = error?.response?.status ?? error?.status ?? 0;
    message.error(attachmentAccessDeniedMessage(status || 404));
    console.error('下载附件失败:', error);
  }
};

// 分离图片和文件附件
const imageAttachments = computed(() => {
  const list = props.attachments || [];
  return Array.isArray(list) ? list.filter(att => isImage(att.file_type, att.file_name)) : [];
});

const fileAttachments = computed(() => {
  const list = props.attachments || [];
  return Array.isArray(list) ? list.filter(att => !isImage(att.file_type, att.file_name)) : [];
});

// 对话查看器状态
const conversationViewer = ref({
  show: false,
  fileUrl: '',
  fileName: ''
});

// 查看对话
const handleViewConversation = async (attachment: Api.Document.Response) => {
  let fileUrl = previewUrlMap.value[attachment.id];
  if (!fileUrl) {
    try {
      const { data, error } = await issueApi.createAttachmentSignedUrl(attachment.id, 'download');
      if (error || !data?.url) {
        const status = (error as any)?.response?.status ?? (error as any)?.status ?? 0;
        message.error(attachmentAccessDeniedMessage(status || 404));
        return;
      }
      fileUrl = toBrowserAttachmentUrl(data.url);
    } catch (error: any) {
      const status = error?.response?.status ?? error?.status ?? 0;
      message.error(attachmentAccessDeniedMessage(status || 404));
      return;
    }
  }
  conversationViewer.value = {
    show: true,
    fileUrl,
    fileName: attachment.file_name
  };
};
</script>

<template>
  <div class="attachment-list">
    <!-- 上传区域 -->
    <div v-if="!readonly" class="mb-4">
      <NUpload
        ref="uploadListRef"
        :custom-request="handleUpload"
        :before-upload="beforeUpload"
        :show-file-list="false"
        :disabled="uploading"
        accept="*/*"
      >
        <NUploadDragger>
          <div class="upload-dragger-content">
            <NSpin :show="uploading">
              <div class="upload-icon">
                <div class="i-material-symbols-cloud-upload-outline text-48px" />
              </div>
              <NText class="upload-text">点击或拖拽文件到此区域上传</NText>
              <NText depth="3" style="font-size: 12px">支持图片、PDF、文档等文件，最大 10MB</NText>
            </NSpin>
          </div>
        </NUploadDragger>
      </NUpload>
    </div>

    <!-- 空状态 -->
    <NEmpty v-if="attachments.length === 0" description="暂无附件" class="py-8" />

    <NText v-if="previewError" type="error" class="mb-2" style="display: block; font-size: 12px">
      {{ previewError }}
    </NText>

    <!-- 图片附件 -->
    <div v-if="imageAttachments.length > 0" class="mb-4">
      <NText class="section-title">图片</NText>
      <NImageGroup>
        <div class="image-grid">
          <div v-for="att in imageAttachments" :key="att.id" class="image-item">
            <NImage :src="getAttachmentPreviewUrl(att.id)" :alt="att.file_name" class="attachment-image" />
            <div class="image-actions">
              <div class="action-icon" @click.stop="handleDownload(att)">
                <Iconify icon="lucide:download" :width="20" :height="20" />
              </div>

              <NPopconfirm @positive-click="handleDelete(att.id)">
                <template #trigger>
                  <div class="action-icon action-icon--delete">
                    <Iconify icon="lucide:trash-2" :width="20" :height="20" />
                  </div>
                </template>
                确定删除此附件吗？
              </NPopconfirm>
            </div>
            <NText class="image-name" :title="att.file_name">{{ att.file_name }}</NText>
          </div>
        </div>
      </NImageGroup>
    </div>

    <!-- 文件附件 -->
    <div v-if="fileAttachments.length > 0">
      <NText class="section-title">文件</NText>
      <div class="file-list">
        <div v-for="att in fileAttachments" :key="att.id" class="file-item">
          <div class="file-icon">
            <div
              class="text-24px"
              :class="
                isImage(att.file_type, att.file_name)
                  ? 'i-material-symbols-image-outline'
                  : 'i-material-symbols-description-outline'
              "
            />
          </div>
          <div class="file-info">
            <NText class="file-name" :title="att.file_name">{{ att.file_name }}</NText>
            <NText depth="3" style="font-size: 12px">
              {{ formatFileSize(att.file_size) }}
            </NText>
          </div>
          <div class="file-actions">
            <!-- 查看对话按钮 (JSONL 文件) -->
            <NButton v-if="isJsonlFile(att.file_name)" size="small" type="info" @click="handleViewConversation(att)">
              <Iconify icon="lucide:message-square" :width="16" :height="16" />
              查看对话
            </NButton>

            <NButton size="small" @click="handleDownload(att)">
              <div class="i-material-symbols-download-outline" />
              下载
            </NButton>

            <NPopconfirm v-if="!readonly" @positive-click="handleDelete(att.id)">
              <template #trigger>
                <NButton size="small" type="error">
                  <div class="i-material-symbols-delete-outline" />
                  删除
                </NButton>
              </template>
              确定删除此附件吗？
            </NPopconfirm>
          </div>
        </div>
      </div>
    </div>

    <!-- 对话查看器弹窗 -->
    <ConversationViewer
      :show="conversationViewer.show"
      :file-url="conversationViewer.fileUrl"
      :file-name="conversationViewer.fileName"
      @update:show="conversationViewer.show = $event"
    />
  </div>
</template>

<style scoped>
.attachment-list {
  width: 100%;
}

.upload-dragger-content {
  padding: 24px;
  text-align: center;
}

.upload-icon {
  margin-bottom: 12px;
  color: #18a058;
}

.upload-text {
  display: block;
  margin-bottom: 4px;
  font-size: 14px;
}

.section-title {
  display: block;
  margin-bottom: 12px;
  font-weight: 500;
  font-size: 14px;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}

.image-item {
  position: relative;
  height: 150px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--n-border-color);
  cursor: pointer;
  background: var(--n-color-modal);
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.attachment-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.image-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  gap: 8px;
  z-index: 100;
}

.action-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  backdrop-filter: blur(8px);
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  cursor: pointer;
  transition: all 0.2s ease;
  color: #333;
}

.action-icon:hover {
  background: rgba(255, 255, 255, 1);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.image-name {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 6px 10px;
  font-size: 12px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.7));
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  pointer-events: none;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--n-border-color);
  transition: background-color 0.2s;
}

.file-item:hover {
  background-color: var(--n-hover-color);
}

.file-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background-color: var(--n-color-modal);
  color: var(--n-text-color);
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-actions {
  display: flex;
  gap: 8px;
}

.file-actions :deep(.n-button) {
  display: flex;
  align-items: center;
  gap: 4px;
}

.file-actions :deep(.n-button:hover) {
  opacity: 0.8;
}
</style>
