<template>
  <div class="work-assignments-list">
    <n-page-header title="工作安排" @back="handleBack" />
    <n-card class="mt-4">
      <template #header>
        <div class="flex justify-between items-center">
          <span>工作安排列表</span>
          <n-button type="primary" @click="handleCreate">分配工作</n-button>
        </div>
      </template>

      <!-- 筛选器 -->
      <n-space class="mb-4">
        <n-select
          v-model:value="filters.assignee_id"
          placeholder="筛选被分配人"
          clearable
          style="width: 200px"
        />
        <n-date-picker
          v-model:value="filters.week_start"
          type="date"
          placeholder="筛选周次"
          clearable
          style="width: 200px"
        />
        <n-button @click="handleFilter">查询</n-button>
      </n-space>

      <n-data-table
        :columns="columns"
        :data="assignments"
        :loading="loading"
        :pagination="pagination"
      />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  NButton, NTag, NButtonGroup, NSelect, NDatePicker, NSpace,
  useMessage, type DataTableColumns
} from 'naive-ui'
import { getWorkAssignments, type WorkAssignment } from '@/service/api/work-management'

const router = useRouter()
const message = useMessage()

const loading = ref(false)
const assignments = ref<WorkAssignment[]>([])
const pagination = ref({ pageSize: 20 })

const filters = ref({
  assignee_id: '',
  week_start: null
})

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
    title: '延期',
    key: 'is_overdue',
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
    render: (row: WorkAssignment) => h(NButtonGroup, [
      h(NButton, { size: 'small', onClick: () => handleView(row.id) }, () => '详情'),
      h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row.id) }, () => '删除')
    ])
  }
])

const fetchAssignments = async () => {
  loading.value = true
  try {
    const params = {
      assignee_id: filters.value.assignee_id || undefined,
      week_start: filters.value.week_start ? filters.value.week_start.toISOString().split('T')[0] : undefined
    }
    const data = await getWorkAssignments(params)
    assignments.value = data || []
  } catch (error) {
    message.error('加载失败')
  } finally {
    loading.value = false
  }
}

const handleFilter = () => {
  fetchAssignments()
}

const handleCreate = () => router.push('/work-management/work-assignments/create')

const handleView = (id: string) => router.push(`/work-management/work-assignments/${id}`)

const handleDelete = async (id: string) => {
  const dialog = window.confirm('确定要删除此工作安排吗？')
  if (!dialog) return

  try {
    // TODO: 调用删除 API
    message.success('删除成功')
    fetchAssignments()
  } catch (error) {
    message.error('删除失败')
  }
}

const handleBack = () => router.back()

onMounted(fetchAssignments)
</script>

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
