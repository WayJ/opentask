<template>
  <div class="rd-groups-list">
    <n-page-header title="研发组管理" @back="handleBack" />
    <n-card class="mt-4">
      <template #header>
        <div class="flex justify-between items-center">
          <span>研发组列表</span>
          <n-button type="primary" @click="handleCreate">创建研发组</n-button>
        </div>
      </template>

      <n-data-table
        :columns="columns"
        :data="groups"
        :loading="loading"
        :pagination="pagination"
      />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NTag, NButtonGroup, useMessage, useDialog } from 'naive-ui'
import { getRdGroups, deleteRdGroup, type RdGroup } from '@/service/api/work-management'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()

const loading = ref(false)
const groups = ref<RdGroup[]>([])
const pagination = ref({ pageSize: 20 })

const columns = [
  { title: '组名', key: 'name' },
  { title: '组长', key: 'leader_id' },
  { title: '成员数', key: 'member_count', render: (row: RdGroup) => row.members?.length || 0 },
  {
    title: '状态',
    key: 'status',
    render: (row: RdGroup) => h(NTag, { type: row.status === 'active' ? 'success' : 'default' }, () => row.status === 'active' ? '活跃' : '停用')
  },
  {
    title: '操作',
    key: 'actions',
    render: (row: RdGroup) => h(NButtonGroup, [
      h(NButton, { size: 'small', onClick: () => handleView(row.id) }, () => '查看'),
      h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row.id) }, () => '删除')
    ])
  }
]

const fetchGroups = async () => {
  loading.value = true
  try {
    const data = await getRdGroups()
    groups.value = data || []
  } catch (error) {
    message.error('加载失败')
  } finally {
    loading.value = false
  }
}

const handleCreate = () => router.push('/work-management/rd-groups/create')

const handleView = (id: string) => router.push(`/work-management/rd-groups/${id}`)

const handleDelete = async (id: string) => {
  dialog.warning({
    title: '确认删除',
    content: '删除研发组将同时删除所有相关数据，此操作不可恢复。确定要删除吗？',
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteRdGroup(id)
        message.success('删除成功')
        await fetchGroups()
      } catch (error) {
        message.error('删除失败')
      }
    }
  })
}

const handleBack = () => router.back()

onMounted(fetchGroups)
</script>

<style scoped>
.rd-groups-list {
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
</style>
