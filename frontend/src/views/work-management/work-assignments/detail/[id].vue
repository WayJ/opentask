<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  NButton,
  NDescriptions,
  NDescriptionsItem,
  NDivider,
  NEmpty,
  NList,
  NListItem,
  NSpace,
  NTag,
  NTimeline,
  NTimelineItem,
  NUpload,
  useMessage
} from 'naive-ui';
import {
  type WorkAssignment,
  type WorkAssignmentAttachment,
  type WorkFeedback,
  deleteAttachment,
  deleteWorkAssignment,
  downloadAttachment,
  getAttachments,
  getWorkAssignment,
  getWorkFeedback,
  updateWorkAssignment,
  uploadAttachment
} from '@/service/api/work-management';

const router = useRouter();
const route = useRoute();
const message = useMessage();

const loading = ref(false);
const assignment = ref<WorkAssignment | null>(null);
const feedbacks = ref<WorkFeedback[]>([]);
const attachments = ref<WorkAssignmentAttachment[]>([]);

const getStatusType = (status: string) => {
  const map: Record<string, 'success' | 'warning' | 'error' | 'default' | 'info'> = {
    not_started: 'default',
    in_progress: 'info',
    completed: 'success',
    blocked: 'error'
  };
  return map[status] || 'default';
};

const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    not_started: '未开始',
    in_progress: '进行中',
    completed: '已完成',
    blocked: '阻塞'
  };
  return map[status] || status;
};

const getQualityType = (quality: string) => {
  const map: Record<string, 'success' | 'warning' | 'default'> = {
    high: 'success',
    low: 'warning',
    unknown: 'default'
  };
  return map[quality] || 'default';
};

const getQualityLabel = (quality: string) => {
  const map: Record<string, string> = {
    high: '高质量',
    low: '低质量',
    unknown: '未评估'
  };
  return map[quality] || quality;
};

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const fetchAssignment = async (id: string) => {
  loading.value = true;
  try {
    const data = await getWorkAssignment(id);
    assignment.value = data;
  } catch {
    message.error('加载失败');
  } finally {
    loading.value = false;
  }
};

const fetchFeedbacks = async (assignmentId: string) => {
  try {
    const data = await getWorkFeedback({ assignment_id: assignmentId });
    feedbacks.value = data || [];
  } catch (error) {
    console.error('加载反馈失败', error);
  }
};

const fetchAttachments = async (assignmentId: string) => {
  try {
    const data = await getAttachments(assignmentId);
    attachments.value = data || [];
  } catch (error) {
    console.error('加载附件失败', error);
  }
};

const handleMarkCompleted = async () => {
  if (!assignment.value) return;

  try {
    await updateWorkAssignment(assignment.value.id, {
      status: 'completed'
    });
    message.success('标记成功');
    await fetchAssignment(assignment.value.id);
  } catch {
    message.error('标记失败');
  }
};

const handleEdit = () => {
  // 待实现：跳转到编辑页面
  message.info('编辑功能待实现');
};

const handleDelete = () => {
  if (!assignment.value) return;
  const assignmentId = assignment.value.id;

  window.$dialog?.warning({
    title: '确认删除',
    content: '确定要删除此工作安排吗？',
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteWorkAssignment(assignmentId);
        message.success('删除成功');
        router.push('/work-management/work-assignments');
      } catch {
        message.error('删除失败');
      }
    }
  });
};

const handleUpload = async ({ file, onProgress: _onProgress, onFinish, onError }: any) => {
  if (!assignment.value) return;

  try {
    await uploadAttachment(assignment.value.id, file.file);
    message.success('上传成功');
    await fetchAttachments(assignment.value.id);
    onFinish();
  } catch {
    message.error('上传失败');
    onError();
  }
};

const handleDownload = async (file: WorkAssignmentAttachment) => {
  try {
    const blob = await downloadAttachment(file.assignment_id, file.id);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = file.file_name;
    a.click();
    URL.revokeObjectURL(url);
  } catch {
    message.error('下载失败');
  }
};

const handleDeleteAttachment = async (attachmentId: string) => {
  if (!assignment.value) return;

  try {
    await deleteAttachment(assignment.value.id, attachmentId);
    message.success('删除成功');
    await fetchAttachments(assignment.value.id);
  } catch {
    message.error('删除失败');
  }
};

const handleBack = () => router.back();

onMounted(async () => {
  const id = route.params.id as string;
  await fetchAssignment(id);
  if (assignment.value) {
    await fetchFeedbacks(assignment.value.id);
    await fetchAttachments(assignment.value.id);
  }
});
</script>

<template>
  <div class="work-assignment-detail">
    <NPageHeader title="工作安排详情" @back="handleBack" />
    <NCard class="mt-4" :loading="loading">
      <template v-if="assignment">
        <!-- 基本信息 -->
        <NDescriptions label-placement="left" :column="2" bordered>
          <NDescriptionsItem label="工作内容" :span="2">
            {{ assignment.title }}
          </NDescriptionsItem>
          <NDescriptionsItem label="被分配人">
            {{ assignment.assignee_name || assignment.assignee_id }}
          </NDescriptionsItem>
          <NDescriptionsItem label="截止日期">
            {{ assignment.deadline }}
          </NDescriptionsItem>
          <NDescriptionsItem label="预估工时">{{ assignment.estimated_hours }} 小时</NDescriptionsItem>
          <NDescriptionsItem label="所属周次">
            {{ assignment.week_start }}
          </NDescriptionsItem>
          <NDescriptionsItem label="当前状态">
            <NTag :type="getStatusType(assignment.status)">
              {{ getStatusLabel(assignment.status) }}
            </NTag>
          </NDescriptionsItem>
          <NDescriptionsItem label="质量评估">
            <NTag :type="getQualityType(assignment.quality)">
              {{ getQualityLabel(assignment.quality) }}
            </NTag>
          </NDescriptionsItem>
          <NDescriptionsItem label="延期状态" :span="2">
            <NTag v-if="assignment.is_overdue" type="error">延期 {{ assignment.overdue_days }} 天</NTag>
            <span v-else>正常</span>
          </NDescriptionsItem>
          <NDescriptionsItem v-if="assignment.cost_project_id" label="成本项目">
            {{ assignment.cost_project_name || assignment.cost_project_id }}
          </NDescriptionsItem>
          <NDescriptionsItem v-if="assignment.description" label="备注" :span="2">
            {{ assignment.description }}
          </NDescriptionsItem>
        </NDescriptions>

        <!-- 操作按钮 -->
        <NSpace class="mt-4">
          <NButton v-if="assignment.status !== 'completed'" type="primary" @click="handleMarkCompleted">
            标记为已完成
          </NButton>
          <NButton @click="handleEdit">编辑</NButton>
          <NButton type="error" @click="handleDelete">删除</NButton>
        </NSpace>

        <!-- 附件 -->
        <NDivider />
        <div class="mb-4">
          <div class="mb-2 flex items-center justify-between">
            <h3>附件 ({{ attachments.length }})</h3>
            <NUpload :custom-request="handleUpload" :show-file-list="false">
              <NButton size="small">上传附件</NButton>
            </NUpload>
          </div>
          <NList v-if="attachments.length > 0">
            <NListItem v-for="file in attachments" :key="file.id">
              <div class="flex items-center justify-between">
                <div class="flex items-center">
                  <span class="mr-2">📄</span>
                  <span>{{ file.file_name }}</span>
                  <span class="ml-2 text-sm text-gray">({{ formatFileSize(file.file_size) }})</span>
                </div>
                <NSpace>
                  <NButton size="small" @click="handleDownload(file)">下载</NButton>
                  <NButton size="small" type="error" @click="handleDeleteAttachment(file.id)">删除</NButton>
                </NSpace>
              </div>
            </NListItem>
          </NList>
          <NEmpty v-else description="暂无附件" size="small" />
        </div>

        <!-- 反馈历史 -->
        <NDivider />
        <div>
          <h3 class="mb-2">反馈历史 ({{ feedbacks.length }})</h3>
          <NTimeline v-if="feedbacks.length > 0">
            <NTimelineItem v-for="feedback in feedbacks" :key="feedback.id" :title="feedback.feedback_date">
              <div class="feedback-content">
                <div class="mb-2">
                  <NTag size="small" :type="getStatusType(feedback.status)">
                    {{ getStatusLabel(feedback.status) }}
                  </NTag>
                </div>
                <div v-if="feedback.content" class="text-gray">
                  {{ feedback.content }}
                </div>
                <div v-if="feedback.is_planned" class="mt-2">
                  <NTag size="tiny" type="info">计划内</NTag>
                </div>
              </div>
            </NTimelineItem>
          </NTimeline>
          <NEmpty v-else description="暂无反馈" size="small" />
        </div>
      </template>
    </NCard>
  </div>
</template>

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
