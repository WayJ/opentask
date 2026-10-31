<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { NButton, NForm, NFormItem, NModal, NSpace } from 'naive-ui';
import MarkdownEditor from '@/components/MarkdownEditor.vue';

interface Props {
  show: boolean;
  description: string;
  loading?: boolean;
}

interface Emits {
  (e: 'update:show', value: boolean): void;
  (e: 'save', description: string): void;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
});

const emit = defineEmits<Emits>();

// 表单数据
const formRef = ref();
const description = ref(props.description || '');
const descriptionError = ref('');

// 监听 props 变化，同步到表单
watch(
  () => props.description,
  newValue => {
    description.value = newValue || '';
  }
);

// 监听 show 变化，打开时重置表单
watch(
  () => props.show,
  newValue => {
    if (newValue) {
      description.value = props.description || '';
      descriptionError.value = '';
    }
  }
);

// 验证描述
function validateDescription(): boolean {
  if (!description.value.trim()) {
    descriptionError.value = '描述不能为空';
    return false;
  }
  descriptionError.value = '';
  return true;
}

// 处理保存
function handleSave() {
  if (!validateDescription()) {
    return;
  }
  emit('save', description.value.trim());
}

// 处理取消
function handleCancel() {
  emit('update:show', false);
}

// 模态框宽度 - 使用固定宽度以确保一致性
const modalWidth = computed(() => '900px');
const modalMaxWidth = computed(() => '95vw');
</script>

<template>
  <NModal
    :show="show"
    :mask-closable="!loading"
    :closable="!loading"
    :auto-focus="false"
    :style="{ width: modalWidth, maxWidth: modalMaxWidth }"
    preset="card"
    title="编辑需求描述"
    size="huge"
    @update:show="handleCancel"
  >
    <NForm ref="formRef" :model="{ description }" label-placement="top">
      <NFormItem
        label="描述内容"
        :validation-status="descriptionError ? 'error' : undefined"
        :feedback="descriptionError"
      >
        <MarkdownEditor
          v-model="description"
          placeholder="请输入需求描述，支持 Markdown 语法..."
          :rows="15"
          max-height="500px"
        />
      </NFormItem>
    </NForm>

    <template #footer>
      <NSpace justify="end">
        <NButton :disabled="loading" @click="handleCancel">取消</NButton>
        <NButton type="primary" :loading="loading" @click="handleSave">保存</NButton>
      </NSpace>
    </template>
  </NModal>
</template>

<style scoped>
:deep(.n-card__content) {
  padding: 20px;
}

/* 确保 MarkdownEditor 组件宽度正确 */
:deep(.markdown-editor) {
  width: 100%;
}

:deep(.markdown-textarea) {
  width: 100%;
  min-height: 300px;
}
</style>
