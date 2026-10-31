<script setup lang="ts">
/* eslint-disable vue/no-mutating-props */
import { computed } from 'vue';
import { NAlert, NButton, NForm, NFormItem, NInput, NModal, NSelect, NSpace, type SelectOption } from 'naive-ui';
import type { Task } from '@/service/api/requirement';

interface Props {
  show: boolean;
  mode: 'create' | 'createSub' | 'edit';
  parentTask?: Task | null;
  formData: {
    title: string;
    description: string;
    task_type?: 'IMPLEMENT' | 'DESIGN' | 'TEST' | 'REVIEW' | 'DEPLOY';
    status?: Task['status'];
  };
  taskTypeOptions: SelectOption[];
  taskStatusOptions?: SelectOption[];
}

interface Emits {
  (e: 'update:show', value: boolean): void;
  (e: 'confirm'): void;
}

const props = withDefaults(defineProps<Props>(), {
  show: false,
  mode: 'create',
  parentTask: null
});

const emit = defineEmits<Emits>();

const localShow = computed({
  get: () => props.show,
  set: value => emit('update:show', value)
});

const title = computed(() => {
  switch (props.mode) {
    case 'createSub':
      return '创建子任务';
    case 'edit':
      return '编辑任务';
    default:
      return '创建任务';
  }
});

const showTaskType = computed(() => props.mode !== 'edit');
const showStatus = computed(() => props.mode === 'edit');
const buttonText = computed(() => (props.mode === 'edit' ? '更新' : '创建'));
</script>

<template>
  <NModal v-model:show="localShow" preset="card" :title="title" style="width: 600px">
    <NAlert v-if="mode === 'createSub' && parentTask" type="info" class="mb-4">父任务: {{ parentTask.title }}</NAlert>
    <NForm :model="formData" label-placement="left" label-width="80px">
      <NFormItem label="标题" required>
        <NInput v-model:value="formData.title" :placeholder="mode === 'createSub' ? '子任务标题' : '任务标题'" />
      </NFormItem>
      <NFormItem label="描述">
        <NInput
          v-model:value="formData.description"
          type="textarea"
          :placeholder="mode === 'createSub' ? '子任务描述' : '任务描述'"
        />
      </NFormItem>
      <NFormItem v-if="showTaskType" label="类型">
        <NSelect v-model:value="formData.task_type" :options="taskTypeOptions" />
      </NFormItem>
      <NFormItem v-if="showStatus" label="状态">
        <NSelect v-model:value="formData.status" :options="taskStatusOptions" />
      </NFormItem>
    </NForm>
    <template #footer>
      <NSpace justify="end">
        <NButton @click="localShow = false">取消</NButton>
        <NButton type="primary" @click="emit('confirm')">{{ buttonText }}</NButton>
      </NSpace>
    </template>
  </NModal>
</template>
