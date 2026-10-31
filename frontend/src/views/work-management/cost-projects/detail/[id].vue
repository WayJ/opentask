<template>
  <div class="cost-project-detail">
    <n-page-header title="成本项目详情" @back="handleBack" />
    <n-card class="mt-4" :loading="loading">
      <template v-if="project">
        <!-- 基本信息 -->
        <n-descriptions label-placement="left" :column="2" bordered>
          <n-descriptions-item label="项目名称" :span="2">
            {{ project.name }}
          </n-descriptions-item>
          <n-descriptions-item label="项目编号">
            {{ project.code }}
          </n-descriptions-item>
          <n-descriptions-item label="项目经理">
            {{ project.manager_name || project.manager_id }}
          </n-descriptions-item>
          <n-descriptions-item label="状态">
            <n-tag :type="getStatusType(project.status)">
              {{ getStatusLabel(project.status) }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="创建时间">
            {{ formatDate(project.created_at) }}
          </n-descriptions-item>
          <n-descriptions-item v-if="project.description" label="项目描述" :span="2">
            {{ project.description }}
          </n-descriptions-item>
        </n-descriptions>

        <!-- 统计信息 -->
        <n-divider />
        <n-grid :cols="4" :x-gap="16">
          <n-grid-item>
            <n-card>
              <n-statistic label="总预估工时" :value="stats.total_estimated_hours" suffix="h" />
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card>
              <n-statistic label="已完成工时" :value="stats.completed_hours" suffix="h" />
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card>
              <n-statistic label="完成率" :value="(stats.completion_rate * 100).toFixed(1)" suffix="%" />
            </n-card>
          </n-grid-item>
          <n-grid-item>
            <n-card>
              <n-statistic label="高质量率" :value="(stats.high_quality_rate * 100).toFixed(1)" suffix="%" />
            </n-card>
          </n-grid-item>
        </n-grid>

        <!-- 操作按钮 -->
        <n-space class="mt-4">
          <n-button type="primary" @click="handleExport">
            导出报告
          </n-button>
          <n-button @click="handleEdit">编辑</n-button>
          <n-button type="error" @click="handleDelete">删除</n-button>
        </n-space>

        <!-- 工作安排列表 -->
        <n-divider />
        <div>
          <h3 class="mb-2">工作安排 ({{ assignments.length }})</h3>
          <n-data-table
            :columns="assignmentColumns"
            :data="assignments"
            :loading="loadingAssignments"
            :pagination="pagination"
          />
        </div>
      </template>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  NButton, NTag, NButtonGroup, NDivider, NDescriptions, NDescriptionsItem,
  NDataTable, NStatistic, NGrid, NGridItem, NCard, NSpace, useMessage,
  type DataTableColumns
} from 'naive-ui'
import {
  getCostProject,
  deleteCostProject,
  getWorkAssignments,
  exportCostProject,
  type CostProject,
  type WorkAssignment
} from '@/service/api/work-management'

const router = useRouter()
const route = useRoute()
const message = useMessage()

const loading = ref(false)
const loadingAssignments = ref(false)
const project = ref<CostProject | null>(null)
const assignments = ref<WorkAssignment[]>([])

const pagination = ref({ pageSize: 20 })

const stats = ref({
  total_estimated_hours: 0,
  completed_hours: 0,
  completion_rate: 0,
  high_quality_rate: 0
})

const getStatusType = (status: string) => {
  const map: Record<string, 'success' | 'info' | 'default'> = {
    active: 'success',
    completed: 'info',
    archived: 'default'
  }
  return map[status] || 'default'
}

const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    active: '活跃',
    completed: '已完成',
    archived: '已归档'
  }
  return map[status] || status
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

const assignmentColumns: DataTableColumns<WorkAssignment> = [
  { title: '工作内容', key: 'title' },
  { title: '被分配人', key: 'assignee_id' },
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
    render: (row: WorkAssignment) => h(NButton, {
      size: 'small',
      onClick: () => router.push(`/work-management/work-assignments/${row.id}`)
    }, () => '详情')
  }
]

const fetchProject = async (id: string) => {
  loading.value = true
  try {
    const data = await getCostProject(id)
    project.value = data
    stats.value = {
      total_estimated_hours: data.total_estimated_hours || 0,
      completed_hours: data.completed_hours || 0,
      completion_rate: data.completion_rate || 0,
      high_quality_rate: data.high_quality_rate || 0
    }
  } catch (error) {
    message.error('加载失败')
  } finally {
    loading.value = false
  }
}

const fetchAssignments = async (projectId: string) => {
  loadingAssignments.value = true
  try {
    const data = await getWorkAssignments({ cost_project_id: projectId })
    assignments.value = data || []
  } catch (error) {
    message.error('加载工作安排失败')
  } finally {
    loadingAssignments.value = false
  }
}

const handleExport = async () => {
  if (!project.value) return

  try {
    const blob = await exportCostProject(project.value.id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${project.value.name}_报告.xlsx`
    a.click()
    URL.revokeObjectURL(url)
    message.success('导出成功')
  } catch (error) {
    message.error('导出失败')
  }
}

const handleEdit = () => {
  // TODO: 跳转到编辑页面
  message.info('编辑功能待实现')
}

const handleDelete = async () => {
  if (!project.value) return

  const dialog = window.confirm('确定要删除此成本项目吗？')
  if (!dialog) return

  try {
    await deleteCostProject(project.value.id)
    message.success('删除成功')
    router.push('/work-management/cost-projects')
  } catch (error) {
    message.error('删除失败')
  }
}

const handleBack = () => router.back()

onMounted(async () => {
  const id = route.params.id as string
  await fetchProject(id)
  await fetchAssignments(id)
})
</script>

<style scoped>
.cost-project-detail {
  padding: 16px;
}

.mt-4 {
  margin-top: 16px;
}

.mb-2 {
  margin-bottom: 8px;
}
</style>
