<script setup lang="ts">
import { computed } from 'vue';

defineOptions({
  name: 'RecentActivity'
});

interface Props {
  data?: Api.Dashboard.RecentActivityItem[];
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
});

const statusLabels: Record<string, string> = {
  planning: '规划中',
  generating: '生成中',
  evaluating: '评估中',
  completed: '已完成',
  closed: '已关闭',
  archived: '已归档',
  open: '待处理',
  in_progress: '进行中',
  feedback: '反馈中',
  resolved: '已解决',
  rejected: '已拒绝'
};

const statusColors: Record<string, string> = {
  planning: 'info',
  generating: 'warning',
  evaluating: 'warning',
  completed: 'success',
  closed: 'default',
  archived: 'default',
  open: 'error',
  in_progress: 'warning',
  feedback: 'info',
  resolved: 'success',
  rejected: 'error'
};

function formatTime(dateStr: string): string {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes}分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}小时前`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}天前`;
  return date.toLocaleDateString('zh-CN');
}

const displayData = computed(() => props.data || []);
</script>

<template>
  <NSpin :show="loading">
    <NList v-if="displayData.length > 0" hoverable clickable>
      <NListItem v-for="item in displayData" :key="item.id">
        <NThing>
          <template #header>
            <div class="flex items-center gap-8px">
              <NTag :type="item.type === 'requirement' ? 'info' : 'warning'" size="small" round>
                {{ item.type === 'requirement' ? '需求' : '问题' }}
              </NTag>
              <span class="font-medium">{{ item.code }}</span>
              <span class="text-gray-500">-</span>
              <span>{{ item.title }}</span>
            </div>
          </template>
          <template #header-extra>
            <NTag :type="(statusColors[item.status] as any) || 'default'" size="small">
              {{ statusLabels[item.status] || item.status }}
            </NTag>
          </template>
          <template #description>
            <span class="text-12px text-gray-400">{{ formatTime(item.updated_at) }}</span>
          </template>
        </NThing>
      </NListItem>
    </NList>
    <NEmpty v-else description="暂无动态" />
  </NSpin>
</template>

<style scoped></style>
