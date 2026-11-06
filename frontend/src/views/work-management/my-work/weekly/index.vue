<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import {
  type DataTableColumns,
  NAlert,
  NButton,
  NButtonGroup,
  NDataTable,
  NDatePicker,
  NDrawer,
  NEmpty,
  NGrid,
  NGridItem,
  NList,
  NListItem,
  NStatistic,
  NTabPane,
  NTabs,
  NTag,
  NThing,
  useMessage
} from 'naive-ui';
import { type WorkAssignment, getMyUnplannedWork, getMyWeeklyWork } from '@/service/api/work-management';

const router = useRouter();
const message = useMessage();

const loading = ref(false);
const selectedWeek = ref<Date>(new Date());
const showUnplanned = ref(false);

const currentWeek = ref<WorkAssignment[]>([]);
const overdue = ref<WorkAssignment[]>([]);
const unplanned = ref({
  resolved_issues: [],
  created_issues: [],
  completed_reqs: [],
  created_reqs: []
});

const summary = computed(() => ({
  total_estimated_hours: currentWeek.value.reduce((sum, item) => sum + (item.estimated_hours || 0), 0),
  completed_count: currentWeek.value.filter(item => item.status === 'completed').length,
  pending_count: currentWeek.value.filter(item => item.status !== 'completed').length,
  overdue_count: overdue.value.length
}));

const formatWeekStart = (date: Date) => {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  const monday = new Date(d.setDate(diff));
  return monday.toISOString().split('T')[0];
};

const fetchData = async () => {
  loading.value = true;
  try {
    const weekStart = formatWeekStart(selectedWeek.value);
    const data = await getMyWeeklyWork(weekStart);
    currentWeek.value = data.current_week || [];
    overdue.value = data.overdue || [];
  } catch {
    message.error('加载失败');
  } finally {
    loading.value = false;
  }
};

const fetchUnplanned = async () => {
  try {
    const weekStart = formatWeekStart(selectedWeek.value);
    const data = await getMyUnplannedWork(weekStart);
    unplanned.value = data || {
      resolved_issues: [],
      created_issues: [],
      completed_reqs: [],
      created_reqs: []
    };
  } catch {
    message.error('加载计划外工作失败');
  }
};

const handleWeekChange = () => {
  fetchData();
  fetchUnplanned();
};

const handleFeedback = (id: string) => {
  router.push(`/work-management/my-work/feedback/${id}`);
};

const handleViewDetail = (id: string) => {
  router.push(`/work-management/work-assignments/${id}`);
};

const overdueColumns: DataTableColumns<WorkAssignment> = [
  { title: '工作内容', key: 'title' },
  { title: '截止日期', key: 'deadline' },
  { title: '工时', key: 'estimated_hours' },
  {
    title: '状态',
    key: 'status',
    render: (row: WorkAssignment) => {
      const statusMap: Record<string, { type: 'success' | 'warning' | 'error' | 'default'; label: string }> = {
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
    title: '延期',
    key: 'overdue',
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
      h(
        NButton,
        {
          size: 'small',
          onClick: () => handleFeedback(row.id)
        },
        () => '反馈'
      )
  }
];

const weekColumns: DataTableColumns<WorkAssignment> = [
  { title: '工作内容', key: 'title' },
  { title: '截止日期', key: 'deadline' },
  { title: '工时', key: 'estimated_hours' },
  {
    title: '状态',
    key: 'status',
    render: (row: WorkAssignment) => {
      const statusMap: Record<string, { type: 'success' | 'warning' | 'error' | 'default'; label: string }> = {
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
    title: '操作',
    key: 'actions',
    render: (row: WorkAssignment) =>
      h(NButtonGroup, [
        h(
          NButton,
          {
            size: 'small',
            onClick: () => handleFeedback(row.id)
          },
          () => '反馈'
        ),
        h(
          NButton,
          {
            size: 'small',
            onClick: () => handleViewDetail(row.id)
          },
          () => '详情'
        )
      ])
  }
];

const handleBack = () => router.back();

onMounted(() => {
  fetchData();
  fetchUnplanned();
});
</script>

<template>
  <div class="my-weekly-work">
    <NPageHeader title="我的周工作" @back="handleBack" />

    <NCard class="mt-4">
      <template #header>
        <div class="flex items-center justify-between">
          <span>周视图</span>
          <NDatePicker v-model:value="selectedWeek" type="week" @update:value="handleWeekChange" />
        </div>
      </template>

      <!-- 统计卡片 -->
      <NGrid :cols="4" :x-gap="16" class="mb-4">
        <NGridItem>
          <NStatistic label="本周工时" :value="summary.total_estimated_hours" suffix="h" />
        </NGridItem>
        <NGridItem>
          <NStatistic label="已完成" :value="summary.completed_count" />
        </NGridItem>
        <NGridItem>
          <NStatistic label="进行中" :value="summary.pending_count" />
        </NGridItem>
        <NGridItem>
          <NStatistic label="已延期" :value="summary.overdue_count" />
        </NGridItem>
      </NGrid>

      <!-- 遗留未完成工作 -->
      <div v-if="overdue.length > 0" class="mb-4">
        <NAlert title="遗留未完成工作" type="warning" class="mb-2">以下工作未在上周完成，请尽快处理</NAlert>
        <NDataTable :columns="overdueColumns" :data="overdue" :row-key="(row: any) => row.id" :pagination="false" />
      </div>

      <!-- 本周工作 -->
      <div>
        <h3 class="mb-2">本周工作安排</h3>
        <NDataTable
          :columns="weekColumns"
          :data="currentWeek"
          :loading="loading"
          :row-key="(row: any) => row.id"
          :pagination="false"
        >
          <template #empty>
            <NEmpty description="本周暂无工作安排" />
          </template>
        </NDataTable>
      </div>
    </NCard>

    <!-- 计划外工作抽屉 -->
    <NDrawer v-model:show="showUnplanned" :width="800" placement="right">
      <template #header>
        <div class="w-full flex items-center justify-between">
          <span>计划外工作</span>
          <NButton size="small" @click="showUnplanned = false">关闭</NButton>
        </div>
      </template>
      <div class="unplanned-content">
        <NTabs type="line" animated>
          <NTabPane name="resolved" tab="已解决问题">
            <NList>
              <NListItem v-for="item in unplanned.resolved_issues" :key="item.id">
                <NThing>{{ item.title }}</NThing>
              </NListItem>
            </NList>
          </NTabPane>
          <NTabPane name="created" tab="创建的问题">
            <NList>
              <NListItem v-for="item in unplanned.created_issues" :key="item.id">
                <NThing>{{ item.title }}</NThing>
              </NListItem>
            </NList>
          </NTabPane>
          <NTabPane name="completed" tab="已完成需求">
            <NList>
              <NListItem v-for="item in unplanned.completed_reqs" :key="item.id">
                <NThing>{{ item.title }}</NThing>
              </NListItem>
            </NList>
          </NTabPane>
          <NTabPane name="created-req" tab="创建的需求">
            <NList>
              <NListItem v-for="item in unplanned.created_reqs" :key="item.id">
                <NThing>{{ item.title }}</NThing>
              </NListItem>
            </NList>
          </NTabPane>
        </NTabs>
      </div>
    </NDrawer>
  </div>
</template>

<style scoped>
.my-weekly-work {
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

.w-full {
  width: 100%;
}

.unplanned-content {
  padding: 16px;
}
</style>
