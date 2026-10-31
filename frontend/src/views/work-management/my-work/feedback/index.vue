<template>
  <div class="work-feedback">
    <n-page-header title="提交工作反馈" @back="handleBack" />
    <n-card class="mt-4" :loading="loading">
      <n-spin :show="loading">
        <!-- 工作信息 -->
        <div v-if="assignment" class="assignment-info mb-4">
          <n-descriptions label-placement="left" :column="1">
            <n-descriptions-item label="工作内容">
              {{ assignment.title }}
            </n-descriptions-item>
            <n-descriptions-item label="截止日期">
              {{ assignment.deadline }}
            </n-descriptions-item>
            <n-descriptions-item label="预估工时">
              {{ assignment.estimated_hours }} 小时
            </n-descriptions-item>
            <n-descriptions-item label="当前状态">
              <n-tag :type="getStatusType(assignment.status)">
                {{ getStatusLabel(assignment.status) }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="质量评估">
              <n-tag :type="getQualityType(assignment.quality)">
                {{ getQualityLabel(assignment.quality) }}
              </n-tag>
            </n-descriptions-item>
          </n-descriptions>
        </div>

        <!-- 反馈表单 -->
        <n-divider />

        <n-form
          ref="formRef"
          :model="formValue"
          :rules="rules"
          label-placement="left"
          label-width="120px"
          require-mark-placement="right-hanging"
        >
          <n-form-item label="反馈日期" path="feedback_date">
            <n-date-picker v-model:value="formValue.feedback_date" type="date" class="w-full" />
          </n-form-item>

          <n-form-item label="工作状态" path="status">
            <n-select
              v-model:value="formValue.status"
              :options="statusOptions"
              label-field="label"
              value-field="value"
            />
          </n-form-item>

          <n-form-item label="反馈内容" path="content">
            <n-input
              v-model:value="formValue.content"
              type="textarea"
              placeholder="请描述今天的工作进展..."
              :autosize="{ minRows: 4, maxRows: 10 }"
            />
          </n-form-item>

          <n-form-item label="附件">
            <n-upload
              :custom-request="handleUpload"
              :show-file-list="true"
              :max="10"
            >
              <n-button>上传附件</n-button>
              <template #tip>
                支持上传图片、PDF、Office 文档，单个文件最大 50MB
              </template>
            </n-upload>
          </n-form-item>

          <n-form-item :show-label="false">
            <n-button type="primary" @click="handleSubmit" :loading="submitting">
              提交反馈
            </n-button>
            <n-button class="ml-2" @click="handleBack">取消</n-button>
          </n-form-item>
        </n-form>
      </n-spin>
    </n-card>

    <!-- 历史反馈 -->
    <n-card class="mt-4" title="历史反馈">
      <n-timeline>
        <n-timeline-item
          v-for="feedback in history"
          :key="feedback.id"
          :title="feedback.feedback_date"
        >
          <div class="feedback-content">
            <div class="mb-2">
              <n-tag size="small" :type="getStatusType(feedback.status)">
                {{ getStatusLabel(feedback.status) }}
              </n-tag>
              <span class="ml-2 text-gray">{{ feedback.content || '无内容' }}</span>
            </div>
          </div>
        </n-timeline-item>
      </n-timeline>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  NButton, NTag, NDatePicker, NSelect, NInput, NUpload, NDescriptions,
  NDescriptionsItem, NDivider, NTimeline, NTimelineItem, useMessage,
  type FormInst, FormRules, UploadFileInfo
} from 'naive-ui'
import { createWorkFeedback, getWorkFeedback, type WorkAssignment, type WorkFeedback } from '@/service/api/work-management'

const router = useRouter()
const route = useRoute()
const message = useMessage()

const loading = ref(false)
const submitting = ref(false)
const assignment = ref<WorkAssignment | null>(null)
const history = ref<WorkFeedback[]>([])

const formRef = ref<FormInst | null>(null)

const formValue = ref({
  assignment_id: '',
  feedback_date: new Date(),
  content: '',
  status: 'in_progress',
  is_planned: true
})

const rules: FormRules = {
  feedback_date: {
    type: 'date',
    required: true,
    message: '请选择反馈日期',
    trigger: 'change'
  },
  status: {
    required: true,
    type: 'string',
    message: '请选择工作状态',
    trigger: 'change'
  }
}

const statusOptions = [
  { label: '未开始', value: 'not_started' },
  { label: '进行中', value: 'in_progress' },
  { label: '已完成', value: 'completed' },
  { label: '阻塞', value: 'blocked' }
]

const getStatusType = (status: string) => {
  const map: Record<string, 'success' | 'warning' | 'error' | 'default' | 'info'> = {
    not_started: 'default',
    in_progress: 'info',
    completed: 'success',
    blocked: 'error'
  }
  return map[status] || 'default'
}

const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    not_started: '未开始',
    in_progress: '进行中',
    completed: '已完成',
    blocked: '阻塞'
  }
  return map[status] || status
}

const getQualityType = (quality: string) => {
  const map: Record<string, 'success' | 'warning' | 'default'> = {
    high: 'success',
    low: 'warning',
    unknown: 'default'
  }
  return map[quality] || 'default'
}

const getQualityLabel = (quality: string) => {
  const map: Record<string, string> = {
    high: '高质量',
    low: '低质量',
    unknown: '未评估'
  }
  return map[quality] || quality
}

const fetchAssignment = async (id: string) => {
  loading.value = true
  try {
    // TODO: 调用获取工作安排详情 API
    // const data = await getWorkAssignment(id)
    // assignment.value = data
  } catch (error) {
    message.error('加载失败')
  } finally {
    loading.value = false
  }
}

const fetchHistory = async () => {
  try {
    // TODO: 调用获取反馈历史 API
    // const data = await getWorkFeedback()
    // history.value = data || []
  } catch (error) {
    message.error('加载历史失败')
  }
}

const handleUpload = async ({ file, onProgress, onFinish, onError }: any) => {
  // TODO: 实现文件上传
  message.info('文件上传功能待实现')
  onFinish()
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    submitting.value = true

    await createWorkFeedback({
      assignment_id: formValue.value.assignment_id || undefined,
      feedback_date: formValue.value.feedback_date.toISOString().split('T')[0],
      content: formValue.value.content,
      status: formValue.value.status,
      is_planned: formValue.value.is_planned
    })

    message.success('反馈提交成功')
    await fetchHistory()

    // 如果状态更新为已完成，刷新工作安排信息
    if (formValue.value.status === 'completed' && assignment.value) {
      await fetchAssignment(assignment.value.id)
    }
  } catch (error: any) {
    if (error?.errorFields) {
      message.error('请检查表单填写')
    } else {
      message.error('提交失败')
    }
  } finally {
    submitting.value = false
  }
}

const handleBack = () => router.back()

onMounted(() => {
  const id = route.params.id as string
  formValue.value.assignment_id = id
  fetchAssignment(id)
  fetchHistory()
})
</script>

<style scoped>
.work-feedback {
  padding: 16px;
}

.mt-4 {
  margin-top: 16px;
}

.mb-4 {
  margin-bottom: 16px;
}

.ml-2 {
  margin-left: 8px;
}

.assignment-info {
  background-color: var(--n-color);
  padding: 16px;
  border-radius: 4px;
}

.text-gray {
  color: #999;
}

.w-full {
  width: 100%;
}
</style>
