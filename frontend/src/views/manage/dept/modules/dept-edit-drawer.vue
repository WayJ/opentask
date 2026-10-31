<script setup lang="ts">
import { ref, watch } from 'vue';
import type { FormInst, FormRules } from 'naive-ui';
import { useLoading } from '@sa/hooks';
import { fetchCreateDept } from '@/service/api';

/**
 * 新建部门抽屉（根部门 / 子部门）
 *
 * 部门「编辑」在详情卡内联表单完成，本抽屉只负责创建。
 */

interface Props {
  /** 父部门 id；null = 根部门 */
  parentId?: string | null;
  /** 父部门名称（仅展示） */
  parentName?: string;
}

const props = withDefaults(defineProps<Props>(), {
  parentId: null,
  parentName: ''
});

interface Emits {
  (e: 'update:visible', value: boolean): void;
  (e: 'submitted', newDeptId?: string): void;
}

const emit = defineEmits<Emits>();

const visible = defineModel<boolean>('visible', {
  default: false
});

const { loading: submitLoading, startLoading, endLoading } = useLoading();

const formRef = ref<FormInst | null>(null);

const model = ref({
  name: '',
  sort: 0
});

const rules: FormRules = {
  name: [{ required: true, message: '请输入部门名称', trigger: 'blur' }]
};

watch(visible, value => {
  if (value) {
    model.value = { name: '', sort: 0 };
    formRef.value?.restoreValidation();
  }
});

function closeDrawer() {
  visible.value = false;
}

async function handleSubmit() {
  await formRef.value?.validate();
  startLoading();
  const { error, data } = await fetchCreateDept({
    name: model.value.name.trim(),
    parent_id: props.parentId || null,
    sort: model.value.sort
  });
  endLoading();
  if (error) return;
  window.$message?.success('部门已创建');
  closeDrawer();
  emit('submitted', data?.id);
}
</script>

<template>
  <NDrawer v-model:show="visible" display-directive="show" :width="380">
    <NDrawerContent :title="parentId ? `新建子部门${parentName ? `（${parentName}）` : ''}` : '新建根部门'" closable>
      <NForm ref="formRef" :model="model" :rules="rules" label-placement="top">
        <NFormItem label="部门名称" path="name">
          <NInput v-model:value="model.name" placeholder="请输入部门名称" @keydown.enter="handleSubmit" />
        </NFormItem>
        <NFormItem label="排序" path="sort">
          <NInputNumber v-model:value="model.sort" :min="0" class="w-full" />
          <template #feedback>
            <span class="sort-hint">数值越小越靠前</span>
          </template>
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace :size="12" justify="end">
          <NButton size="small" @click="closeDrawer">取消</NButton>
          <NButton type="primary" size="small" :loading="submitLoading" @click="handleSubmit">创建</NButton>
        </NSpace>
      </template>
    </NDrawerContent>
  </NDrawer>
</template>

<style scoped>
.sort-hint {
  font-size: var(--vk-font-caption);
  color: var(--vk-muted);
}
</style>
