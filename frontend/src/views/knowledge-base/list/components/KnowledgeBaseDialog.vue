<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { NButton, NForm, NFormItem, NInput, NModal, NSelect, NSpace, useMessage } from 'naive-ui';
import type { FormInst, FormRules } from 'naive-ui';
import { createKnowledgeBase, updateKnowledgeBase } from '@/service/api/knowledge-base';
import type { Api } from '@/typings/api';

interface Props {
  visible: boolean;
  knowledgeBase: Api.KnowledgeBase.KnowledgeBase | null;
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
const formData = ref<Api.KnowledgeBase.CreateKnowledgeBase & { status?: string }>({
  name: '',
  description: '',
  icon: '',
  repositoryUrl: ''
});

// 状态选项
const statusOptions = [
  { label: '活跃', value: 'active' },
  { label: '已归档', value: 'archived' }
];

// 表单验证规则
const formRules: FormRules = {
  name: [
    { required: true, message: '请输入知识库名称', trigger: 'blur' },
    { min: 2, max: 100, message: '长度在 2 到 100 个字符', trigger: 'blur' }
  ]
};

// 是否为编辑模式
const isEdit = computed(() => Boolean(props.knowledgeBase));

// 监听知识库变化，填充表单
watch(
  () => props.knowledgeBase,
  kb => {
    if (kb) {
      formData.value = {
        name: kb.name,
        description: kb.description || '',
        icon: kb.icon || '',
        repositoryUrl: kb.repositoryUrl || '',
        status: kb.status
      };
    } else {
      formData.value = {
        name: '',
        description: '',
        icon: '',
        repositoryUrl: ''
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
    if (isEdit.value && props.knowledgeBase) {
      // 更新
      await updateKnowledgeBase(props.knowledgeBase.id, formData.value);
      message.success('更新成功');
      emit('success');
      handleClose();
    } else {
      // 创建
      await createKnowledgeBase(formData.value);
      message.success('创建成功');
      emit('success');
      handleClose();
    }
  } catch (error) {
    message.error(isEdit.value ? '更新失败' : '创建失败');
    console.error(error);
  } finally {
    submitting.value = false;
  }
};
</script>

<template>
  <NModal
    :show="visible"
    :title="isEdit ? '编辑知识库' : '创建知识库'"
    :mask-closable="false"
    preset="card"
    class="kb-dialog"
    :style="{ width: '480px' }"
    @update:show="handleClose"
  >
    <NForm
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-placement="top"
      require-mark-placement="right-hanging"
      class="kb-form"
    >
      <NFormItem label="知识库名称" path="name">
        <NInput v-model:value="formData.name" placeholder="输入知识库名称" maxlength="100" show-count />
      </NFormItem>

      <NFormItem label="知识库描述" path="description">
        <NInput
          v-model:value="formData.description"
          type="textarea"
          :rows="3"
          placeholder="简要描述知识库的用途和内容"
          maxlength="500"
          show-count
        />
      </NFormItem>

      <NFormItem label="图标地址" path="icon">
        <NInput v-model:value="formData.icon" placeholder="https://example.com/icon.png（可选）">
          <template #prefix>
            <span class="i-carbon-image text-icon" />
          </template>
        </NInput>
      </NFormItem>

      <NFormItem label="Git 仓库地址" path="repositoryUrl">
        <NInput v-model:value="formData.repositoryUrl" placeholder="https://github.com/user/repo.git（可选）">
          <template #prefix>
            <span class="i-carbon-git-repo text-icon" />
          </template>
        </NInput>
      </NFormItem>

      <NFormItem v-if="isEdit" label="状态" path="status">
        <NSelect v-model:value="formData.status" placeholder="选择状态" :options="statusOptions" />
      </NFormItem>
    </NForm>

    <template #footer>
      <NSpace justify="end" :size="8">
        <NButton @click="handleClose">取消</NButton>
        <NButton type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? '保存' : '创建' }}
        </NButton>
      </NSpace>
    </template>
  </NModal>
</template>

<style scoped lang="scss">
.kb-dialog {
  width: 480px;

  :deep(.n-card__content) {
    padding: 20px 24px;
  }

  .kb-form {
    :deep(.n-form-item) {
      margin-bottom: 18px;

      &:last-child {
        margin-bottom: 0;
      }

      .n-form-item-label {
        font-weight: 500;
        font-size: 13px;
        color: #666;
        margin-bottom: 6px;
        padding: 0;
      }

      .n-form-item-blank {
        min-height: 34px;
      }
    }

    :deep(.n-input) {
      &:hover .n-input__border {
        border-color: #c0c4cc;
      }

      &:focus-within .n-input__border {
        border-color: #18a058;
      }
    }

    :deep(.n-input__textarea-el) {
      resize: vertical;
      min-height: 72px;
      padding: 8px 12px;
    }
  }
}

.text-icon {
  font-size: 16px;
  color: #999;
}
</style>
