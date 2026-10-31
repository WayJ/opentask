<script setup lang="ts">
/* eslint-disable vue/no-mutating-props */
import { computed, ref, watch } from 'vue';
import { NAlert, NButton, NModal, NSpace, NSpin } from 'naive-ui';
import FileUploader from './FileUploader.vue';

interface DocumentForm {
  id: string;
}

interface Props {
  show: boolean;
  form: DocumentForm;
  multiple?: boolean; // 是否支持多文件上传
}

interface Emits {
  (e: 'update:show', value: boolean): void;
  (e: 'confirm', file?: File): void;
  (e: 'batchConfirm', files?: File[]): void;
}

const props = withDefaults(defineProps<Props>(), {
  show: false,
  multiple: false
});

const emit = defineEmits<Emits>();

const localShow = computed({
  get: () => props.show,
  set: value => emit('update:show', value)
});

const modalTitle = computed(() => {
  if (props.form.id) {
    return '编辑文档';
  }
  return props.multiple ? '批量上传文档' : '新建文档';
});

const attachmentFile = ref<File | undefined>(undefined);
const attachmentFiles = ref<File[]>([]);
const isUploading = ref(false);

// 监听 modal 打开，重置文件
watch(
  () => props.show,
  newVal => {
    if (newVal) {
      attachmentFile.value = undefined;
      attachmentFiles.value = [];
      isUploading.value = false;
    }
  }
);

// 处理文件变化（单文件）
function handleFileChange(files: File[]) {
  attachmentFile.value = files[0];
}

// 处理文件变化（多文件）
function handleFilesChange(files: File[]) {
  attachmentFiles.value = files;
}

// 处理保存
function handleConfirm() {
  if (isUploading.value) return; // 防止重复点击

  if (props.multiple) {
    // 多文件上传
    if (attachmentFiles.value.length === 0) {
      window.$message?.error('请选择文件');
      return;
    }
    isUploading.value = true;
    emit('batchConfirm', attachmentFiles.value);
  } else {
    // 单文件上传
    isUploading.value = true;
    emit('confirm', attachmentFile.value);
  }
}

// 获取文件上传组件的接受类型
const acceptTypes = '.png,.jpg,.jpeg,.gif,.webp,.svg,.bmp,.ico,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.md';

// 计算保存按钮是否禁用
const saveDisabled = computed(() => {
  if (props.form.id) {
    // 编辑模式，不需要文件
    return false;
  }
  // 新建模式，需要文件
  if (props.multiple) {
    return attachmentFiles.value.length === 0;
  }
  return !attachmentFile.value;
});

// 重置上传状态（供父组件调用）
function resetUploadingState() {
  isUploading.value = false;
}

// 暴露方法给父组件
defineExpose({
  resetUploadingState
});
</script>

<template>
  <NModal v-model:show="localShow" preset="card" :title="modalTitle" style="width: 700px">
    <NSpin :show="isUploading">
      <NAlert type="info" style="margin-bottom: 16px">
        <template #header>文档说明</template>
        <template v-if="multiple">
          批量上传模式：支持一次上传多个文档，最多20个，每个不超过1MB（图片自动压缩至1080p）。支持图片、PDF、Office文档、文本文件等。
        </template>
        <template v-else>
          文档就是附件，文档名直接使用上传的文件名。支持的文件类型：PNG、JPG、GIF、WebP、SVG、PDF、Word、Excel、PowerPoint、Markdown、文本文件等。图片自动压缩至1080p，大小控制在1MB以下。
        </template>
      </NAlert>

      <!-- 单文件上传 -->
      <FileUploader
        v-if="!multiple"
        v-model="attachmentFile"
        :max-size="1"
        :accept="acceptTypes"
        @change="handleFileChange"
      />

      <!-- 多文件上传 -->
      <FileUploader
        v-else
        :multiple="true"
        :max-size="1"
        :max-files="20"
        :accept="acceptTypes"
        @change="handleFilesChange"
      />
    </NSpin>

    <template #footer>
      <NSpace justify="end">
        <NButton :disabled="isUploading" @click="localShow = false">取消</NButton>
        <NButton type="primary" :disabled="saveDisabled || isUploading" @click="handleConfirm">
          <template v-if="isUploading">上传中...</template>
          <template v-else>保存</template>
        </NButton>
      </NSpace>
    </template>
  </NModal>
</template>
