<template>
  <div class="my-weekly-work">
    <n-page-header title="我的周工作" @back="handleBack" />

    <n-card class="mt-4">
      <template #header>
        <div class="flex justify-between items-center">
          <span>周视图</span>
          <n-date-picker v-model:value="selectedWeek" type="week" @update:value="handleWeekChange" />
        </div>
      </template>

      <!-- 统计卡片 -->
      <n-grid :cols="4" :x-gap="16" class="mb-4">
        <n-grid-item>
          <n-statistic label="本周工时" :value="summary.total_estimated_hours" suffix="h" />
        </n-grid-item>
        <n-grid-item>
          <n-statistic label="已完成" :value="summary.completed_count" />
        </n-grid-item>
        <n-grid-item>
          <n-statistic label="进行中" :value="summary.pending_count" />
        </n-grid-item>
        <n-grid-item>
          <n-statistic label="已延期" :value="summary.overdue_count" />
        </n-grid-item>
      </n-grid>

      <!-- 遗留未完成工作 -->
      <div v-if="overdue.length > 0" class="mb-4">
        <n-alert title="遗留未完成工作" type="warning" class="mb-2">
          以下工作未在上周完成，请尽快处理
        </n-alert>
        <n-data-table
          :columns="overdueColumns"
          :data="overdue"
          :row-key="(row: any) => row.id"
          :pagination="false"
        />
      </div>

      <!-- 本周工作 -->
      <div>
        <h3 class="mb-2">本周工作安排</h3>
        <n-data-table
          :columns="weekColumns"
          :data="currentWeek"
          :loading="loading"
          :row-key="(row: any) => row.id"
          :pagination="false"
        >
          <template #empty>
            <n-empty description="本周暂无工作安排" />
          </template>
        </n-data-table>
      </div>
    </n-card>

    <!-- 计划外工作抽屉 -->
    <n-drawer v-model:show="showUnplanned" :width="800" placement="right">
      <template #header>
        <div class="flex justify-between items-center w-full">
          <span>计划外工作</span>
          <n-button size="small" @click="showUnplanned = false">关闭</n-button>
        </div>
      </template>
      <div class="unplanned-content">
        <n-tabs type="line" animated>
          <n-tab-pane name="resolved" tab="已解决 Issue">
            <n-list>
              <n-list-item v-for="item in unplanned.resolved_issues" :key="item.id">
                <n-thing>{{ item.title }}</n-thing>
              </n-list-item>
            </n-list>
          </n-tab-pane>
          <n-tab-pane name="created" tab="创建的 Issue">
            <n-list>
              <n-list-item v-for="item in unplanned.created_issues" :key="item.id">
                <n-thing>{{ item.title }}</n-thing>
              </n-list-item>
            </n-list>
          </n-tab-pane>
          <n-tab-pane name="completed" tab="已完成需求">
            <n-list>
              <n-list-item v-for="item in unplanned.completed_reqs" :key="item.id">
                <n-thing>{{ item.title }}</n-thing>
              </n-list-item>
            </n-list>
          </n-tab-pane>
          <n-tab-pane name="created-req" tab="创建的需求">
            <n-list>
              <n-list-item v-for="item in unplanned.created_reqs" :key="item.id">
                <n-thing>{{ item.title }}</n-thing>
              </n-list-item>
            </n-list>
          </n-tab-pane>
        </n-tabs>
      </div>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import {
  NButton, NTag, NButtonGroup, NDatePicker, NStatistic, NGrid, NGridItem,
  NAlert, NDataTable, NEmpty, NDrawer, NTabs, NTabPane, NList, NListItem,
  NThing, useMessage, type DataTableColumns
} from 'naive-ui'
import { getMyWeeklyWork, getMyUnplannedWork, type WorkAssignment, type MyWeeklyWorkResponse } from '@/service/api/work-management'

const router = useRouter()
const message = useMessage()

const loading = ref(false)
const selectedWeek = ref<Date>(new Date())
const showUnplanned = ref(false)

const currentWeek = ref<WorkAssignment[]>([])
const overdue = ref<WorkAssignment[]>([])
const unplanned = ref({
  resolved_issues: [],
  created_issues: [],
  completed_reqs: [],
  created_reqs: []
})

const summary = computed(() => ({
  total_estimated_hours: currentWeek.value.reduce((sum, item) => sum + (item.estimated_hours || 0), 0),
  completed_count: currentWeek.value.filter(item => item.status === 'completed').length,
  pending_count: currentWeek.value.filter(item => item.status !== 'completed').length,
  overdue_count: overdue.value.length
}))

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
      }
      const status = statusMap[row.status] || { type: 'default', label: row.status }
      return h(NTag, { type: status.type }, () => status.label)
    }
  },
  {
    title: '延期',
    key: 'overdue',
    render: (row: WorkAssignment) => {
      if (row.is_overdue) {
        return h(NTag, { type: 'error' }, () => `延期 ${row.overdue_days} 天`)
      }
      return h('span', {}, '-')
    }
  },
  {
    title: '操作',
    key: 'actions',
    render: (row: WorkAssignment) => h(NButton, {
      size: 'small',
      onClick: () => handleFeedback(row.id)
    }, () => '反馈')
  }
]

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
      }
      const status = statusMap[row.status] || { type: 'default', label: row.status }
      return h(NTag, { type: status.type }, () => status.label)
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
      }
      const quality = qualityMap[row.quality] || { type: 'default', label: row.quality }
      return h(NTag, { type: quality.type }, () => quality.label)
    }
  },
  {
    title: '操作',
    key: 'actions',
    render: (row: WorkAssignment) => h(NButtonGroup, [
      h(NButton, {
        size: 'small',
        onClick: () => handleFeedback(row.id)
      }, () => '反馈'),
      h(NButton, {
        size: 'small',
        onClick: () => handleViewDetail(row.id)
      }, () => '详情')
    ])
  }
]

const formatWeekStart = (date: Date) => {
  const d = new Date(date)
  const day = d.getDay()
  const diff = d.getDate() - day + (day === 0 ? -6 : 1)
  const monday = new Date(d.setDate(diff))
  return monday.toISOString().split('T')[0]
}

const fetchData = async () => {
  loading.value = true
  try {
    const weekStart = formatWeekStart(selectedWeek.value)
    const data = await getMyWeeklyWork(weekStart)
    currentWeek.value = data.current_week || []
    overdue.value = data.overdue || []
  } catch (error) {
    message.error('加载失败')
  } finally {
    loading.value = false
  }
}

const fetchUnplanned = async () => {
  try {
    const weekStart = formatWeekStart(selectedWeek.value)
    const data = await getMyUnplannedWork(weekStart)
    unplanned.value = data || {
      resolved_issues: [],
      created_issues: [],
      completed_reqs: [],
      created_reqs: []
    }
  } catch (error) {
    message.error('加载计划外工作失败')
  }
}

const handleWeekChange = () => {
  fetchData()
  fetchUnplanned()
}

const handleFeedback = (id: string) => {
  router.push(`/work-management/my-work/feedback/${id}`)
}

const handleViewDetail = (id: string) => {
  router.push(`/work-management/work-assignments/${id}`)
}

const handleBack = () => router.back()

onMounted(() => {
  fetchData()
  fetchUnplanned()
})
</script>

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
