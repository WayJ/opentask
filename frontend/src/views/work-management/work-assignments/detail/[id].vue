<template>
  <div class="work-assignment-detail">
    <n-page-header title="工作安排详情" @back="handleBack" />
    <n-card class="mt-4" :loading="loading">
      <template v-if="assignment">
        <!-- 基本信息 -->
        <n-descriptions label-placement="left" :column="2" bordered>
          <n-descriptions-item label="工作内容" :span="2">
            {{ assignment.title }}
          </n-descriptions-item>
          <n-descriptions-item label="被分配人">
            {{ assignment.assignee_name || assignment.assignee_id }}
          </n-descriptions-item>
          <n-descriptions-item label="截止日期">
            {{ assignment.deadline }}
          </n-descriptions-item>
          <n-descriptions-item label="预估工时">
            {{ assignment.estimated_hours }} 小时
          </n-descriptions-item>
          <n-descriptions-item label="所属周次">
            {{ assignment.week_start }}
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
          <n-descriptions-item label="延期状态" :span="2">
            <n-tag v-if="assignment.is_overdue" type="error">
              延期 {{ assignment.overdue_days }} 天
            </n-tag>
            <span v-else>正常</span>
          </n-descriptions-item>
          <n-descriptions-item v-if="assignment.cost_project_id" label="成本项目">
            {{ assignment.cost_project_name || assignment.cost_project_id }}
          </n-descriptions-item>
          <n-descriptions-item v-if="assignment.description" label="备注" :span="2">
            {{ assignment.description }}
          </n-descriptions-item>
        </n-descriptions>

        <!-- 操作按钮 -->
        <n-space class="mt-4">
          <n-button
            v-if="assignment.status !== 'completed'"
            type="primary"
            @click="handleMarkCompleted"
          >
            标记为已完成
          </n-button>
          <n-button @click="handleEdit">编辑</n-button>
          <n-button type="error" @click="handleDelete">删除</n-button>
        </n-space>

        <!-- 附件 -->
        <n-divider />
        <div class="mb-4">
          <div class="flex justify-between items-center mb-2">
            <h3>附件 ({{ attachments.length }})</h3>
            <n-upload
              :custom-request="handleUpload"
              :show-file-list="false"
            >
              <n-button size="small">上传附件</n-button>
            </n-upload>
          </div>
          <n-list v-if="attachments.length > 0">
            <n-list-item v-for="file in attachments" :key="file.id">
              <div class="flex justify-between items-center">
                <div class="flex items-center">
                  <span class="mr-2">📄</span>
                  <span>{{ file.file_name }}</span>
                  <span class="ml-2 text-gray text-sm">
                    ({{ formatFileSize(file.file_size) }})
                  </span>
                </div>
                <n-space>
                  <n-button size="small" @click="handleDownload(file)">
                    下载
                  </n-button>
                  <n-button size="small" type="error" @click="handleDeleteAttachment(file.id)">
                    删除
                  </n-button>
                </n-space>
              </div>
            </n-list-item>
          </n-list>
          <n-empty v-else description="暂无附件" size="small" />
        </div>

        <!-- 反馈历史 -->
        <n-divider />
        <div>
          <h3 class="mb-2">反馈历史 ({{ feedbacks.length }})</h3>
          <n-timeline v-if="feedbacks.length > 0">
            <n-timeline-item
              v-for="feedback in feedbacks"
              :key="feedback.id"
              :title="feedback.feedback_date"
            >
              <div class="feedback-content">
                <div class="mb-2">
                  <n-tag size="small" :type="getStatusType(feedback.status)">
                    {{ getStatusLabel(feedback.status) }}
                  </n-tag>
                </div>
                <div v-if="feedback.content" class="text-gray">
                  {{ feedback.content }}
                </div>
                <div v-if="feedback.is_planned" class="mt-2">
                  <n-tag size="tiny" type="info">计划内</n-tag>
                </div>
              </div>
            </n-timeline-item>
          </n-timeline>
          <n-empty v-else description="暂无反馈" size="small" />
        </div>
      </template>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  NButton, NTag, NDivider, NDescriptions, NDescriptionsItem,
  NList, NListItem, NEmpty, NTimeline, NTimelineItem, NUpload, NSpace,
  useMessage
} from 'naive-ui'
import {
  getWorkAssignment,
  deleteWorkAssignment,
  updateWorkAssignment,
  getWorkFeedback,
  getAttachments,
  uploadAttachment,
  deleteAttachment,
  downloadAttachment,
  type WorkAssignment,
  type WorkFeedback,
  type WorkAssignmentAttachment
} from '@/service/api/work-management'

const router = useRouter()
const route = useRoute()
const message = useMessage()

const loading = ref(false)
const assignment = ref<WorkAssignment | null>(null)
const feedbacks = ref<WorkFeedback[]>([])
const attachments = ref<WorkAssignmentAttachment[]>([])

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

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const fetchAssignment = async (id: string) => {
  loading.value = true
  try {
    const data = await getWorkAssignment(id)
    assignment.value = data
  } catch (error) {
    message.error('加载失败')
  } finally {
    loading.value = false
  }
}

const fetchFeedbacks = async (assignmentId: string) => {
  try {
    const data = await getWorkFeedback({ assignment_id: assignmentId })
    feedbacks.value = data || []
  } catch (error) {
    console.error('加载反馈失败', error)
  }
}

const fetchAttachments = async (assignmentId: string) => {
  try {
    const data = await getAttachments(assignmentId)
    attachments.value = data || []
  } catch (error) {
    console.error('加载附件失败', error)
  }
}

const handleMarkCompleted = async () => {
  if (!assignment.value) return

  try {
    await updateWorkAssignment(assignment.value.id, {
      status: 'completed'
    })
    message.success('标记成功')
    await fetchAssignment(assignment.value.id)
  } catch (error) {
    message.error('标记失败')
  }
}

const handleEdit = () => {
  // TODO: 跳转到编辑页面
  message.info('编辑功能待实现')
}

const handleDelete = async () => {
  if (!assignment.value) return

  const dialog = window.confirm('确定要删除此工作安排吗？')
  if (!dialog) return

  try {
    await deleteWorkAssignment(assignment.value.id)
    message.success('删除成功')
    router.push('/work-management/work-assignments')
  } catch (error) {
    message.error('删除失败')
  }
}

const handleUpload = async ({ file, onProgress, onFinish, onError }: any) => {
  if (!assignment.value) return

  try {
    await uploadAttachment(assignment.value.id, file.file)
    message.success('上传成功')
    await fetchAttachments(assignment.value.id)
    onFinish()
  } catch (error) {
    message.error('上传失败')
    onError()
  }
}

const handleDownload = async (file: WorkAssignmentAttachment) => {
  try {
    const blob = await downloadAttachment(file.assignment_id, file.id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = file.file_name
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    message.error('下载失败')
  }
}

const handleDeleteAttachment = async (attachmentId: string) => {
  if (!assignment.value) return

  try {
    await deleteAttachment(assignment.value.id, attachmentId)
    message.success('删除成功')
    await fetchAttachments(assignment.value.id)
  } catch (error) {
    message.error('删除失败')
  }
}

const handleBack = () => router.back()

onMounted(async () => {
  const id = route.params.id as string
  await fetchAssignment(id)
  if (assignment.value) {
    await fetchFeedbacks(assignment.value.id)
    await fetchAttachments(assignment.value.id)
  }
})
</script>

<style scoped>
.work-assignment-detail {
  padding: 16px;
}

.mt-4 {
  margin-top: 16px;
}

.mb-2 {
  margin-bottom: 8px;
}

.mb-4 {
  margin-bottom: 16px;
}

.ml-2 {
  margin-left: 8px;
}

.mr-2 {
  margin-right: 8px;
}

.text-gray {
  color: #999;
}

.text-sm {
  font-size: 12px;
}

.feedback-content {
  padding: 8px 0;
}
</style>
