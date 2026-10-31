<template>
  <div class="cost-project-create">
    <n-page-header title="创建成本项目" @back="handleBack" />
    <n-card class="mt-4">
      <n-form
        ref="formRef"
        :model="formValue"
        :rules="rules"
        label-placement="left"
        label-width="120px"
        require-mark-placement="right-hanging"
      >
        <n-form-item label="项目名称" path="name">
          <n-input
            v-model:value="formValue.name"
            placeholder="请输入项目名称"
            maxlength="100"
            show-count
          />
        </n-form-item>

        <n-form-item label="项目编号" path="code">
          <n-input
            v-model:value="formValue.code"
            placeholder="请输入项目编号"
            maxlength="50"
          />
        </n-form-item>

        <n-form-item label="项目经理" path="manager_id">
          <n-select
            v-model:value="formValue.manager_id"
            :options="managerOptions"
            :loading="loadingManagers"
            placeholder="请选择项目经理"
            filterable
            label-field="label"
            value-field="value"
          />
        </n-form-item>

        <n-form-item label="状态" path="status">
          <n-select
            v-model:value="formValue.status"
            :options="statusOptions"
            placeholder="请选择状态"
          />
        </n-form-item>

        <n-form-item label="项目描述" path="description">
          <n-input
            v-model:value="formValue.description"
            type="textarea"
            placeholder="请输入项目描述（可选）"
            :autosize="{ minRows: 3, maxRows: 6 }"
          />
        </n-form-item>

        <n-form-item :show-label="false">
          <n-space>
            <n-button type="primary" @click="handleSubmit" :loading="submitting">
              创建
            </n-button>
            <n-button @click="handleBack">取消</n-button>
          </n-space>
        </n-form-item>
      </n-form>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  NButton, NSelect, NInput, NSpace,
  useMessage, type FormInst, type FormRules, type SelectOption
} from 'naive-ui'
import {
  createCostProject,
  getUsers
} from '@/service/api/work-management'

const router = useRouter()
const message = useMessage()

const formRef = ref<FormInst | null>(null)
const submitting = ref(false)
const loadingManagers = ref(false)

const managerOptions = ref<SelectOption[]>([])

const formValue = ref({
  name: '',
  code: '',
  manager_id: '',
  status: 'active',
  description: ''
})

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
}

const statusOptions = [
  { label: '活跃', value: 'active' },
  { label: '已完成', value: 'completed' },
  { label: '已归档', value: 'archived' }
]

const fetchManagers = async () => {
  loadingManagers.value = true
  try {
    // TODO: 从用户服务获取用户列表，过滤项目经理角色
    managerOptions.value = [
      { label: '张三', value: '1' },
      { label: '李四', value: '2' },
      { label: '王五', value: '3' }
    ]
  } catch (error) {
    message.error('加载用户列表失败')
  } finally {
    loadingManagers.value = false
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    submitting.value = true

    await createCostProject({
      name: formValue.value.name,
      code: formValue.value.code,
      manager_id: formValue.value.manager_id,
      status: formValue.value.status as any,
      description: formValue.value.description
    })

    message.success('创建成功')
    router.push('/work-management/cost-projects')
  } catch (error: any) {
    if (error?.errorFields) {
      message.error('请检查表单填写')
    } else {
      message.error('创建失败')
    }
  } finally {
    submitting.value = false
  }
}

const handleBack = () => router.back()

onMounted(() => {
  fetchManagers()
})
</script>

<style scoped>
.cost-project-create {
  padding: 16px;
}

.mt-4 {
  margin-top: 16px;
}
</style>
