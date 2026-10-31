<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { NButton, NForm, NFormItem, NInput, NModal, NSelect, NSpace, useMessage } from 'naive-ui';
import type { FormInst, FormRules } from 'naive-ui';
import { createKnowledge, updateKnowledge } from '@/service/api/knowledge';
import type { Api } from '@/typings/api';

interface Props {
  visible: boolean;
  knowledge: Api.Knowledge.Knowledge | null;
  knowledgeBaseId: string;
}

interface Emits {
  (e: 'update:visible', value: boolean): void;
  (e: 'success'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const message = useMessage();
const formRef = ref<FormInst | null>(null);
const submitting = ref(false);

// 表单数据
const formData = ref<Api.Knowledge.CreateKnowledge & { status?: string; visibility?: string; tagIds?: string[] }>({
  title: '',
  summary: '',
  content: '',
  categoryId: '',
  tagIds: []
});

// 状态选项
const statusOptions = [
  { label: '草稿', value: 'draft' },
  { label: '已发布', value: 'published' },
  { label: '已归档', value: 'archived' }
];

// 可见性选项
const visibilityOptions = [
  { label: '公开', value: 'public' },
  { label: '私有', value: 'private' }
];

// 分类选项（示例）
const categoryOptions = ref<{ label: string; value: string }[]>([]);

// 标签选项（示例）
const tagOptions = ref<{ label: string; value: string }[]>([]);

// 表单验证规则
const formRules: FormRules = {
  title: [
    { required: true, message: '请输入知识标题', trigger: 'blur' },
    { min: 2, max: 200, message: '长度在 2 到 200 个字符', trigger: 'blur' }
  ],
  content: [
    { required: true, message: '请输入知识内容', trigger: 'blur' },
    { min: 10, message: '内容至少 10 个字符', trigger: 'blur' }
  ]
};

// 是否为编辑模式
const isEdit = computed(() => Boolean(props.knowledge));

// 监听知识变化，填充表单
watch(
  () => props.knowledge,
  knowledge => {
    if (knowledge) {
      formData.value = {
        title: knowledge.title,
        summary: knowledge.summary || '',
        content: knowledge.content,
        categoryId: knowledge.categoryId || '',
        tagIds: knowledge.tags?.map(t => t.id) || [],
        status: knowledge.status,
        visibility: knowledge.visibility
      };
    } else {
      formData.value = {
        title: '',
        summary: '',
        content: '',
        categoryId: '',
        tagIds: []
      };
    }
    formRef.value?.restoreValidation();
  }
);

// 关闭对话框
const handleClose = () => {
  emit('update:visible', false);
};

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return;

  try {
    await formRef.value.validate();
  } catch {
    return;
  }

  submitting.value = true;
  try {
    const data = {
      ...formData.value,
      knowledgeBaseId: props.knowledgeBaseId
    };

    if (isEdit.value && props.knowledge) {
      // 更新
      await updateKnowledge(props.knowledge.id, data);
      message.success('更新成功');
      emit('success');
      handleClose();
    } else {
      // 创建
      await createKnowledge(data);
      message.success('创建成功');
      emit('success');
      handleClose();
    }
  } catch (error) {
    message.error(isEdit.value ? '更新失败' : '创建失败');
    // eslint-disable-next-line no-console
    console.error(error);
  } finally {
    submitting.value = false;
  }
};
</script>

<template>
  <NModal
    :show="visible"
    :title="isEdit ? '编辑知识文档' : '创建知识文档'"
    :mask-closable="false"
    style="width: 800px"
    @update:show="handleClose"
  >
    <NForm
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-placement="left"
      label-width="100px"
      require-mark-placement="right-hanging"
    >
      <NFormItem label="标题" path="title">
        <NInput v-model:value="formData.title" placeholder="请输入知识标题" maxlength="200" show-count />
      </NFormItem>

      <NFormItem label="摘要" path="summary">
        <NInput
          v-model:value="formData.summary"
          type="textarea"
          :rows="2"
          placeholder="请输入知识摘要"
          maxlength="500"
          show-count
        />
      </NFormItem>

      <NFormItem label="内容" path="content">
        <NInput
          v-model:value="formData.content"
          type="textarea"
          :rows="10"
          placeholder="请输入知识内容（支持 Markdown）"
          maxlength="10000"
          show-count
        />
      </NFormItem>

      <NFormItem label="分类" path="categoryId">
        <NSelect v-model:value="formData.categoryId" placeholder="请选择分类" :options="categoryOptions" clearable />
      </NFormItem>

      <NFormItem label="标签" path="tags">
        <NSelect v-model:value="formData.tagIds" placeholder="请选择标签" :options="tagOptions" multiple clearable />
      </NFormItem>

      <NFormItem v-if="isEdit" label="状态" path="status">
        <NSelect v-model:value="formData.status" placeholder="请选择状态" :options="statusOptions" />
      </NFormItem>

      <NFormItem v-if="isEdit" label="可见性" path="visibility">
        <NSelect v-model:value="formData.visibility" placeholder="请选择可见性" :options="visibilityOptions" />
      </NFormItem>
    </NForm>

    <template #footer>
      <NSpace>
        <NButton @click="handleClose">取消</NButton>
        <NButton type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? '保存' : '创建' }}
        </NButton>
      </NSpace>
    </template>
  </NModal>
</template>

<style scoped></style>
