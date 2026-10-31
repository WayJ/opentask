<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import {
  type FormInst,
  type FormRules,
  NButton,
  NDatePicker,
  NInput,
  NInputNumber,
  NSelect,
  NSpace,
  type SelectOption,
  useMessage
} from 'naive-ui';
import { createWorkAssignment, getCostProjects } from '@/service/api/work-management';

const router = useRouter();
const message = useMessage();

const formRef = ref<FormInst | null>(null);
const submitting = ref(false);
const loadingUsers = ref(false);
const loadingProjects = ref(false);

const userOptions = ref<SelectOption[]>([]);
const projectOptions = ref<SelectOption[]>([]);

const formValue = ref({
  title: '',
  assignee_id: '',
  deadline: null as Date | null,
  estimated_hours: 8,
  week_start: new Date(),
  cost_project_id: '',
  description: ''
});

const rules: FormRules = {
  title: {
    required: true,
    message: '请输入工作内容',
    trigger: 'blur'
  },
  assignee_id: {
    required: true,
    type: 'string',
    message: '请选择被分配人',
    trigger: 'change'
  },
  deadline: {
    type: 'date',
    required: true,
    message: '请选择截止日期',
    trigger: 'change'
  },
  estimated_hours: {
    type: 'number',
    required: true,
    message: '请输入预估工时',
    trigger: 'blur'
  },
  week_start: {
    type: 'date',
    required: true,
    message: '请选择所属周次',
    trigger: 'change'
  }
};

const fetchUsers = async () => {
  loadingUsers.value = true;
  try {
    // 待接入：从用户服务获取用户列表
    // 临时使用模拟数据
    userOptions.value = [
      { label: '张三', value: '1' },
      { label: '李四', value: '2' },
      { label: '王五', value: '3' }
    ];
  } catch {
    message.error('加载用户列表失败');
  } finally {
    loadingUsers.value = false;
  }
};

const fetchProjects = async () => {
  loadingProjects.value = true;
  try {
    const data = await getCostProjects({ status: 'active' });
    projectOptions.value = (data || []).map((project: any) => ({
      label: `${project.name} (${project.code})`,
      value: project.id
    }));
  } catch {
    message.error('加载成本项目失败');
  } finally {
    loadingProjects.value = false;
  }
};

const handleSubmit = async () => {
  if (!formRef.value) return;

  try {
    await formRef.value.validate();
    submitting.value = true;

    await createWorkAssignment({
      title: formValue.value.title,
      assignee_id: formValue.value.assignee_id,
      deadline: formValue.value.deadline ? formValue.value.deadline.toISOString().split('T')[0] : '',
      estimated_hours: formValue.value.estimated_hours || 0,
      week_start: formValue.value.week_start ? formValue.value.week_start.toISOString().split('T')[0] : '',
      cost_project_id: formValue.value.cost_project_id || undefined,
      description: formValue.value.description
    });

    message.success('创建成功');
    router.push('/work-management/work-assignments');
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
  fetchUsers();
  fetchProjects();
});
</script>

<template>
  <div class="work-assignment-create">
    <NPageHeader title="创建工作安排" @back="handleBack" />
    <NCard class="mt-4">
      <NForm
        ref="formRef"
        :model="formValue"
        :rules="rules"
        label-placement="left"
        label-width="120px"
        require-mark-placement="right-hanging"
      >
        <NFormItem label="工作内容" path="title">
          <NInput v-model:value="formValue.title" placeholder="请输入工作内容" maxlength="200" show-count />
        </NFormItem>

        <NFormItem label="被分配人" path="assignee_id">
          <NSelect
            v-model:value="formValue.assignee_id"
            :options="userOptions"
            :loading="loadingUsers"
            placeholder="请选择被分配人"
            filterable
            label-field="label"
            value-field="value"
          />
        </NFormItem>

        <NFormItem label="截止日期" path="deadline">
          <NDatePicker v-model:value="formValue.deadline" type="date" placeholder="请选择截止日期" class="w-full" />
        </NFormItem>

        <NFormItem label="预估工时" path="estimated_hours">
          <NInputNumber
            v-model:value="formValue.estimated_hours"
            :min="0.5"
            :max="999"
            :step="0.5"
            placeholder="请输入预估工时"
            class="w-full"
          >
            <template #suffix>小时</template>
          </NInputNumber>
        </NFormItem>

        <NFormItem label="所属周次" path="week_start">
          <NDatePicker v-model:value="formValue.week_start" type="week" placeholder="请选择所属周次" class="w-full" />
        </NFormItem>

        <NFormItem label="成本项目" path="cost_project_id">
          <NSelect
            v-model:value="formValue.cost_project_id"
            :options="projectOptions"
            :loading="loadingProjects"
            placeholder="请选择成本项目"
            filterable
            clearable
            label-field="label"
            value-field="value"
          />
        </NFormItem>

        <NFormItem label="备注" path="description">
          <NInput
            v-model:value="formValue.description"
            type="textarea"
            placeholder="请输入备注信息（可选）"
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
.work-assignment-create {
  padding: 16px;
}

.mt-4 {
  margin-top: 16px;
}

.w-full {
  width: 100%;
}
</style>
