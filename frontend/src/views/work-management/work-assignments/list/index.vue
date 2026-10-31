<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { type DataTableColumns, NButton, NButtonGroup, NDatePicker, NSelect, NSpace, NTag, useMessage } from 'naive-ui';
import { type WorkAssignment, getWorkAssignments } from '@/service/api/work-management';

const router = useRouter();
const message = useMessage();

const loading = ref(false);
const assignments = ref<WorkAssignment[]>([]);
const pagination = ref({ pageSize: 20 });

const filters = ref({
  assignee_id: '',
  week_start: null
});

const fetchAssignments = async () => {
  loading.value = true;
  try {
    const params = {
      assignee_id: filters.value.assignee_id || undefined,
      week_start: filters.value.week_start ? filters.value.week_start.toISOString().split('T')[0] : undefined
    };
    const data = await getWorkAssignments(params);
    assignments.value = data || [];
  } catch {
    message.error('加载失败');
  } finally {
    loading.value = false;
  }
};

const handleFilter = () => {
  fetchAssignments();
};

const handleCreate = () => router.push('/work-management/work-assignments/create');

const handleView = (id: string) => router.push(`/work-management/work-assignments/${id}`);

const handleDelete = (_id: string) => {
  window.$dialog?.warning({
    title: '确认删除',
    content: '确定要删除此工作安排吗？',
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        // 待接入：调用删除 API
        message.success('删除成功');
        fetchAssignments();
      } catch {
        message.error('删除失败');
      }
    }
  });
};

const columns = computed<DataTableColumns<WorkAssignment>>([
  { title: '工作内容', key: 'title' },
  { title: '被分配人', key: 'assignee_id' },
  { title: '截止日期', key: 'deadline' },
  { title: '工时', key: 'estimated_hours' },
  {
    title: '状态',
    key: 'status',
    render: (row: WorkAssignment) => {
      const statusMap: Record<string, { type: 'success' | 'warning' | 'error' | 'default' | 'info'; label: string }> = {
        not_started: { type: 'default', label: '未开始' },
        in_progress: { type: 'info', label: '进行中' },
        completed: { type: 'success', label: '已完成' },
        blocked: { type: 'error', label: '阻塞' }
      };
      const status = statusMap[row.status] || { type: 'default', label: row.status };
      return h(NTag, { type: status.type }, () => status.label);
    }
  },
  {
    title: '质量',
    key: 'quality',
    render: (row: WorkAssignment) => {
      const qualityMap: Record<string, { type: 'success' | 'warning' | 'default'; label: string }> = {
        high: { type: 'success', label: '高质量' },
        low: { type: 'warning', label: '低质量' },
        unknown: { type: 'default', label: '未评估' }
      };
      const quality = qualityMap[row.quality] || { type: 'default', label: row.quality };
      return h(NTag, { type: quality.type }, () => quality.label);
    }
  },
  {
    title: '延期',
    key: 'is_overdue',
    render: (row: WorkAssignment) => {
      if (row.is_overdue) {
        return h(NTag, { type: 'error' }, () => `延期 ${row.overdue_days} 天`);
      }
      return h('span', {}, '-');
    }
  },
  {
    title: '操作',
    key: 'actions',
    render: (row: WorkAssignment) =>
      h(NButtonGroup, [
        h(NButton, { size: 'small', onClick: () => handleView(row.id) }, () => '详情'),
        h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row.id) }, () => '删除')
      ])
  }
]);

const handleBack = () => router.back();

onMounted(fetchAssignments);
</script>

<template>
  <div class="work-assignments-list">
    <NPageHeader title="工作安排" @back="handleBack" />
    <NCard class="mt-4">
      <template #header>
        <div class="flex items-center justify-between">
          <span>工作安排列表</span>
          <NButton type="primary" @click="handleCreate">分配工作</NButton>
        </div>
      </template>

      <!-- 筛选器 -->
      <NSpace class="mb-4">
        <NSelect v-model:value="filters.assignee_id" placeholder="筛选被分配人" clearable style="width: 200px" />
        <NDatePicker
          v-model:value="filters.week_start"
          type="date"
          placeholder="筛选周次"
          clearable
          style="width: 200px"
        />
        <NButton @click="handleFilter">查询</NButton>
      </NSpace>

      <NDataTable :columns="columns" :data="assignments" :loading="loading" :pagination="pagination" />
    </NCard>
  </div>
</template>

<style scoped>
.work-assignments-list {
  padding: 16px;
}

.flex {
  display: flex;
}

.justify-between {
  justify-content: space-between;
}

.items-center {
  align-items: center;
}

.mt-4 {
  margin-top: 16px;
}

.mb-4 {
  margin-bottom: 16px;
}
</style>
