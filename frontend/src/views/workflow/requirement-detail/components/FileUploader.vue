<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { NButton, NText, NUpload, NUploadDragger } from 'naive-ui';
import { compressImages } from '@/utils/imageCompress';
import SvgIcon from '@/components/custom/svg-icon.vue';

interface FileItem {
  id: string;
  file: File;
}

interface Props {
  modelValue?: File | File[];
  maxSize?: number; // MB
  maxFiles?: number; // 最大文件数量
  accept?: string; // MIME type or file extension
  disabled?: boolean;
  multiple?: boolean; // 是否支持多文件上传
}

interface Emits {
  (e: 'update:modelValue', value: File | File[] | undefined): void;
  (e: 'change', value: File[]): void;
}

const props = withDefaults(defineProps<Props>(), {
  maxSize: 1, // 1MB
  maxFiles: 20, // 最多20个文件
  accept: '*',
  disabled: false,
  multiple: false
});

const emit = defineEmits<Emits>();

// 文件列表
const fileList = ref<FileItem[]>([]);

// 监听外部变化
watch(
  () => props.modelValue,
  newVal => {
    if (newVal) {
      if (Array.isArray(newVal)) {
        fileList.value = newVal.map((f, i) => ({
          id: `file-${i}-${Date.now()}`,
          file: f
        }));
      } else {
        fileList.value = [{ id: 'file-0', file: newVal }];
      }
    } else {
      fileList.value = [];
    }
  },
  { immediate: true }
);

// 计算属性
const canUpload = computed(() => {
  if (props.disabled) return false;
  if (props.multiple) {
    return fileList.value.length < props.maxFiles;
  }
  return fileList.value.length === 0;
});

// 文件大小格式化
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${Math.round((bytes / k ** i) * 100) / 100} ${sizes[i]}`;
}

// 文件类型图标
function getFileIcon(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  const iconMap: Record<string, string> = {
    pdf: 'mdi:file-pdf-box',
    doc: 'mdi:file-word',
    docx: 'mdi:file-word',
    xls: 'mdi:file-excel',
    xlsx: 'mdi:file-excel',
    ppt: 'mdi:file-powerpoint',
    pptx: 'mdi:file-powerpoint',
    png: 'mdi:image',
    jpg: 'mdi:image',
    jpeg: 'mdi:image',
    gif: 'mdi:image',
    zip: 'mdi:zip-box',
    rar: 'mdi:zip-box'
  };
  return iconMap[ext] || 'mdi:file-document';
}

// 验证文件类型（不检查大小，因为压缩后已经控制）
function validateFileType(fileToValidate: File): boolean {
  // 检查文件类型
  if (props.accept !== '*') {
    const acceptedTypes = props.accept.split(',').map(t => t.trim());
    const fileExt = `.${fileToValidate.name.split('.').pop()?.toLowerCase()}`;
    const fileType = fileToValidate.type;

    const isAccepted = acceptedTypes.some(accept => {
      if (accept.startsWith('.')) {
        return fileExt === accept.toLowerCase();
      }
      return fileType.includes(accept);
    });

    if (!isAccepted) {
      window.$message?.error(`不支持的文件类型: "${fileToValidate.name}"`);
      return false;
    }
  }

  return true;
}

// 处理文件选择
async function handleFileSelect(options: { fileList: Array<{ file: File }> }) {
  const incomingFiles = options.fileList;
  if (incomingFiles.length === 0) return;

  // 压缩图片（会自动调整大小和质量）
  const rawFiles = incomingFiles.map(f => f.file);
  const maxSizeBytes = props.maxSize * 1024 * 1024;
  const compressedFiles = await compressImages(rawFiles, { maxSize: maxSizeBytes });

  if (props.multiple) {
    // 多文件模式
    const remainingSlots = props.maxFiles - fileList.value.length;
    if (remainingSlots <= 0) {
      window.$message?.error(`最多只能上传 ${props.maxFiles} 个文件`);
      return;
    }

    const filesToAdd = compressedFiles.slice(0, remainingSlots);
    const validFiles: FileItem[] = [];

    for (const file of filesToAdd) {
      // 验证文件（压缩后的文件应该已经满足大小要求）
      if (validateFileType(file)) {
        // 检查文件是否已存在（通过文件名判断）
        const isDuplicate = fileList.value.some(f => f.file.name === file.name);
        if (!isDuplicate) {
          validFiles.push({
            id: `file-${Date.now()}-${Math.random()}`,
            file
          });
        }
      }
    }

    if (validFiles.length > 0) {
      fileList.value = [...fileList.value, ...validFiles];
      const files = fileList.value.map(f => f.file);
      emit('update:modelValue', files);
      emit('change', files);
    }
  } else {
    // 单文件模式
    const selectedFile = compressedFiles[0];
    if (validateFileType(selectedFile)) {
      fileList.value = [{ id: 'file-0', file: selectedFile }];
      emit('update:modelValue', selectedFile);
      emit('change', [selectedFile]);
    }
  }
}

// 删除文件
function removeFile(fileId: string) {
  fileList.value = fileList.value.filter(f => f.id !== fileId);
  const files = fileList.value.map(f => f.file);
  if (props.multiple) {
    emit('update:modelValue', files);
    emit('change', files);
  } else {
    emit('update:modelValue', undefined);
    emit('change', []);
  }
}

// 暴露方法
defineExpose({
  clearFiles: () => {
    fileList.value = [];
    emit('update:modelValue', props.multiple ? [] : undefined);
    emit('change', []);
  },
  getFiles: () => fileList.value.map(f => f.file),
  getFileCount: () => fileList.value.length
});
</script>

<template>
  <div class="file-uploader">
    <!-- 拖拽上传区域 -->
    <NUpload
      v-if="canUpload"
      :show-file-list="false"
      :accept="accept"
      :disabled="disabled"
      :multiple="multiple"
      custom-request
      @change="handleFileSelect"
    >
      <NUploadDragger>
        <div style="margin-bottom: 12px">
          <SvgIcon icon="mdi:cloud-upload" style="font-size: 48px; opacity: 0.6" />
        </div>
        <NText style="font-size: 16px">点击或拖拽文件到此区域上传</NText>
        <NText depth="3" style="display: block; margin-top: 8px">
          <template v-if="multiple">
            支持多文件上传，最多 {{ maxFiles }} 个，每个最大 {{ maxSize }}MB（图片自动压缩）
          </template>
          <template v-else>支持单个文件最大 {{ maxSize }}MB（图片自动压缩至1080p）</template>
        </NText>
      </NUploadDragger>
    </NUpload>

    <!-- 文件列表显示 -->
    <div v-if="fileList.length > 0" class="file-list">
      <div v-for="fileItem in fileList" :key="fileItem.id" class="file-item">
        <div class="file-item-left">
          <SvgIcon :icon="getFileIcon(fileItem.file.name)" class="file-icon" />
          <div class="file-info">
            <div class="file-name">{{ fileItem.file.name }}</div>
            <NText depth="3" style="font-size: 12px">
              {{ formatFileSize(fileItem.file.size) }}
            </NText>
          </div>
        </div>
        <NButton quaternary circle size="small" :disabled="disabled" @click="removeFile(fileItem.id)">
          <template #icon>
            <SvgIcon icon="mdi:close-circle" />
          </template>
        </NButton>
      </div>
    </div>
  </div>
</template>

<style scoped>
.file-uploader {
  width: 100%;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background-color: var(--n-color);
  border: 1px solid var(--n-border-color);
  border-radius: 8px;
  transition: all 0.3s;
}

.file-item:hover {
  background-color: var(--n-color-modal);
  border-color: var(--n-color-target);
}

.file-item-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.file-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.file-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
