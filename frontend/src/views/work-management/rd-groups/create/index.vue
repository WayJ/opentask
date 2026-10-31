<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { NButton, useMessage } from 'naive-ui';
import type { FormInst, FormRules } from 'naive-ui';
import { createRdGroup } from '@/service/api/work-management';

const router = useRouter();
const message = useMessage();

const formRef = ref<FormInst | null>(null);
const loading = ref(false);

const formValue = ref({
  name: '',
  director_id: '',
  leader_id: ''
});

const rules: FormRules = {
  name: {
    required: true,
    message: '请输入研发组名称',
    trigger: 'blur'
  },
  director_id: {
    required: true,
    type: 'string',
    message: '请选择产品总监',
    trigger: 'change'
  },
  leader_id: {
    required: true,
    type: 'string',
    message: '请选择组长',
    trigger: 'change'
  }
};

// 模拟用户选项（实际应从用户 API 获取）
const directorOptions = ref([
  { label: '产品总监 A', value: 'director-1' },
  { label: '产品总监 B', value: 'director-2' }
]);

const leaderOptions = ref([
  { label: '组长 A', value: 'leader-1' },
  { label: '组长 B', value: 'leader-2' }
]);

const handleBack = () => router.back();

const handleSubmit = async () => {
  if (!formRef.value) return;

  try {
    await formRef.value.validate();
    loading.value = true;

    await createRdGroup({
      name: formValue.value.name,
      director_id: formValue.value.director_id,
      leader_id: formValue.value.leader_id
    });

    message.success('创建成功');
    handleBack();
  } catch (error: any) {
    if (error?.errorFields) {
      message.error('请检查表单填写');
    } else {
      message.error('创建失败');
    }
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  // 待接入：加载用户列表
});
</script>

<template>
  <div class="rd-group-create">
    <NPageHeader title="创建研发组" @back="handleBack" />
    <NCard class="mt-4">
      <NForm
        ref="formRef"
        :model="formValue"
        :rules="rules"
        label-placement="left"
        label-width="120px"
        require-mark-placement="right-hanging"
      >
        <NFormItem label="研发组名称" path="name">
          <NInput v-model:value="formValue.name" placeholder="请输入研发组名称" />
        </NFormItem>

        <NFormItem label="产品总监" path="director_id">
          <NSelect
            v-model:value="formValue.director_id"
            placeholder="请选择产品总监"
            :options="directorOptions"
            label-field="label"
            value-field="value"
            filterable
          />
        </NFormItem>

        <NFormItem label="组长" path="leader_id">
          <NSelect
            v-model:value="formValue.leader_id"
            placeholder="请选择组长"
            :options="leaderOptions"
            label-field="label"
            value-field="value"
            filterable
          />
        </NFormItem>

        <NFormItem :show-label="false">
          <NButton type="primary" :loading="loading" @click="handleSubmit">创建</NButton>
          <NButton class="ml-2" @click="handleBack">取消</NButton>
        </NFormItem>
      </NForm>
    </NCard>
  </div>
</template>

<style scoped>
.rd-group-create {
  padding: 16px;
}

.mt-4 {
  margin-top: 16px;
}

.ml-2 {
  margin-left: 8px;
}
</style>
