<script setup lang="ts">
import { ref, watch } from 'vue';
import type { FormInst, FormRules } from 'naive-ui';
import { useLoading } from '@sa/hooks';
import { fetchCreateRole } from '@/service/api';

/**
 * 新建角色抽屉
 *
 * 角色「编辑」在详情卡内联表单完成，本抽屉只负责创建
 * （code 创建后不可改，data_scope 默认 SELF 创建后可调）。
 */

defineOptions({ name: 'RoleEditDrawer' });

interface Emits {
  (e: 'update:visible', value: boolean): void;
  (e: 'submitted', newRoleId?: string): void;
}

const emit = defineEmits<Emits>();

const visible = defineModel<boolean>('visible', {
  default: false
});

const { loading: submitLoading, startLoading, endLoading } = useLoading();

const formRef = ref<FormInst | null>(null);

const model = ref({
  code: '',
  name: '',
  description: '',
  data_scope: 'SELF' as Api.SystemManage.DataScope
});

const DATA_SCOPES: { value: Api.SystemManage.DataScope; label: string }[] = [
  { value: 'ALL', label: '全部数据' },
  { value: 'DEPT_AND_CHILD', label: '本部门及子部门' },
  { value: 'DEPT', label: '仅本部门' },
  { value: 'CUSTOM', label: '自定义部门' },
  { value: 'SELF', label: '仅本人' }
];

// 角色编码约定：小写字母/数字/下划线/中划线（与后端 code 唯一约束配合）
const rules: FormRules = {
  code: [
    { required: true, message: '请输入角色编码', trigger: 'blur' },
    { pattern: /^[a-z][a-z0-9_-]{1,49}$/, message: '小写字母开头，仅含小写字母/数字/_/-，2-50 位', trigger: 'input' }
  ],
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }]
};

watch(visible, value => {
  if (value) {
    model.value = { code: '', name: '', description: '', data_scope: 'SELF' };
    formRef.value?.restoreValidation();
  }
});

function closeDrawer() {
  visible.value = false;
}

// 从 flat request 的 AxiosError 中取后端 detail（409 编码冲突等）
function getErrMsg(err: unknown, fallback: string) {
  const e = err as { response?: { data?: { detail?: string } }; message?: string } | null;
  return e?.response?.data?.detail || e?.message || fallback;
}

async function handleSubmit() {
  await formRef.value?.validate();
  startLoading();
  const { error, data } = await fetchCreateRole({
    code: model.value.code.trim(),
    name: model.value.name.trim(),
    description: model.value.description.trim() || undefined,
    data_scope: model.value.data_scope
  });
  endLoading();
  if (error) {
    window.$message?.error(getErrMsg(error, '创建角色失败'));
    return;
  }
  window.$message?.success('角色已创建');
  closeDrawer();
  emit('submitted', data?.id);
}
</script>

<template>
  <NDrawer v-model:show="visible" display-directive="show" :width="400">
    <NDrawerContent title="新建角色" closable>
      <NForm ref="formRef" :model="model" :rules="rules" label-placement="top">
        <NFormItem label="角色编码" path="code">
          <NInput
            v-model:value="model.code"
            placeholder="如 dev_lead（创建后不可修改）"
            @keydown.enter="handleSubmit"
          />
        </NFormItem>
        <NFormItem label="角色名称" path="name">
          <NInput v-model:value="model.name" placeholder="如 研发组长" />
        </NFormItem>
        <NFormItem label="角色描述" path="description">
          <NInput
            v-model:value="model.description"
            type="textarea"
            :rows="2"
            :maxlength="255"
            placeholder="角色用途说明（可选）"
          />
        </NFormItem>
        <NFormItem label="数据范围" path="data_scope">
          <NRadioGroup v-model:value="model.data_scope" name="create-data-scope">
            <NRadio v-for="scope in DATA_SCOPES" :key="scope.value" :value="scope.value">
              {{ scope.label }}
            </NRadio>
          </NRadioGroup>
          <template #feedback>
            <span class="scope-hint">创建后可在详情卡调整；自定义部门需创建后配置</span>
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
.scope-hint {
  font-size: var(--vk-font-caption);
  color: var(--vk-muted);
}
</style>
