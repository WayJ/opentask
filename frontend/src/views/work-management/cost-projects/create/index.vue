<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import {
  type FormInst,
  type FormRules,
  NButton,
  NInput,
  NSelect,
  NSpace,
  type SelectOption,
  useMessage
} from 'naive-ui';
import { createCostProject } from '@/service/api/work-management';

const router = useRouter();
const message = useMessage();

const formRef = ref<FormInst | null>(null);
const submitting = ref(false);
const loadingManagers = ref(false);

const managerOptions = ref<SelectOption[]>([]);

const formValue = ref({
  name: '',
  code: '',
  manager_id: '',
  status: 'active',
  description: ''
});

const rules: FormRules = {
  name: {
    required: true,
    message: '请输入项目名称',
    trigger: 'blur'
  },
  code: {
    required: true,
    message: '请输入项目编号',
    trigger: 'blur'
  },
  manager_id: {
    required: true,
    type: 'string',
    message: '请选择项目经理',
    trigger: 'change'
  },
  status: {
    required: true,
    type: 'string',
    message: '请选择状态',
    trigger: 'change'
  }
};

const statusOptions = [
  { label: '活跃', value: 'active' },
  { label: '已完成', value: 'completed' },
  { label: '已归档', value: 'archived' }
];

const fetchManagers = async () => {
  loadingManagers.value = true;
  try {
    // 待接入：从用户服务获取用户列表，过滤项目经理角色
    managerOptions.value = [
      { label: '张三', value: '1' },
      { label: '李四', value: '2' },
      { label: '王五', value: '3' }
    ];
  } catch {
    message.error('加载用户列表失败');
  } finally {
    loadingManagers.value = false;
  }
};

const handleSubmit = async () => {
  if (!formRef.value) return;

  try {
    await formRef.value.validate();
    submitting.value = true;

    await createCostProject({
      name: formValue.value.name,
      code: formValue.value.code,
      manager_id: formValue.value.manager_id,
      status: formValue.value.status as any,
      description: formValue.value.description
    });

    message.success('创建成功');
    router.push('/work-management/cost-projects');
  } catch (error: any) {
    if (error?.errorFields) {
      message.error('请检查表单填写');
    } else {
      message.error('创建失败');
    }
  } finally {
    submitting.value = false;
  }
};

const handleBack = () => router.back();

onMounted(() => {
  fetchManagers();
});
</script>

<template>
  <div class="cost-project-create">
    <NPageHeader title="创建成本项目" @back="handleBack" />
    <NCard class="mt-4">
      <NForm
        ref="formRef"
        :model="formValue"
        :rules="rules"
        label-placement="left"
        label-width="120px"
        require-mark-placement="right-hanging"
      >
        <NFormItem label="项目名称" path="name">
          <NInput v-model:value="formValue.name" placeholder="请输入项目名称" maxlength="100" show-count />
        </NFormItem>

        <NFormItem label="项目编号" path="code">
          <NInput v-model:value="formValue.code" placeholder="请输入项目编号" maxlength="50" />
        </NFormItem>

        <NFormItem label="项目经理" path="manager_id">
          <NSelect
            v-model:value="formValue.manager_id"
            :options="managerOptions"
            :loading="loadingManagers"
            placeholder="请选择项目经理"
            filterable
            label-field="label"
            value-field="value"
          />
        </NFormItem>

        <NFormItem label="状态" path="status">
          <NSelect v-model:value="formValue.status" :options="statusOptions" placeholder="请选择状态" />
        </NFormItem>

        <NFormItem label="项目描述" path="description">
          <NInput
            v-model:value="formValue.description"
            type="textarea"
            placeholder="请输入项目描述（可选）"
            :autosize="{ minRows: 3, maxRows: 6 }"
          />
        </NFormItem>

        <NFormItem :show-label="false">
          <NSpace>
            <NButton type="primary" :loading="submitting" @click="handleSubmit">创建</NButton>
            <NButton @click="handleBack">取消</NButton>
          </NSpace>
        </NFormItem>
      </NForm>
    </NCard>
  </div>
</template>

<style scoped>
.cost-project-create {
  padding: 16px;
}

.mt-4 {
  margin-top: 16px;
}
</style>
