<script setup lang="ts">
import { h, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { NButton, NButtonGroup, NTag, useMessage } from 'naive-ui';
import { type CostProject, deleteCostProject, getCostProjects } from '@/service/api/work-management';

const router = useRouter();
const message = useMessage();

const loading = ref(false);
const projects = ref<CostProject[]>([]);
const pagination = ref({ pageSize: 20 });

const fetchProjects = async () => {
  loading.value = true;
  try {
    const data = await getCostProjects();
    projects.value = data || [];
  } catch {
    message.error('加载失败');
  } finally {
    loading.value = false;
  }
};

const handleCreate = () => router.push('/work-management/cost-projects/create');

const handleView = (id: string) => router.push(`/work-management/cost-projects/${id}`);

const handleDelete = (id: string) => {
  window.$dialog?.warning({
    title: '确认删除',
    content: '确定要删除此成本项目吗？',
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await deleteCostProject(id);
        message.success('删除成功');
        await fetchProjects();
      } catch {
        message.error('删除失败');
      }
    }
  });
};

const columns = [
  { title: '项目名称', key: 'name' },
  { title: '项目编号', key: 'code' },
  { title: '项目经理', key: 'manager_id' },
  {
    title: '状态',
    key: 'status',
    render: (row: CostProject) => {
      const statusMap: Record<string, { type: 'success' | 'warning' | 'error' | 'default'; label: string }> = {
        active: { type: 'success', label: '活跃' },
        completed: { type: 'info', label: '已完成' },
        archived: { type: 'default', label: '已归档' }
      };
      const status = statusMap[row.status] || { type: 'default', label: row.status };
      return h(NTag, { type: status.type }, () => status.label);
    }
  },
  {
    title: '操作',
    key: 'actions',
    render: (row: CostProject) =>
      h(NButtonGroup, [
        h(NButton, { size: 'small', onClick: () => handleView(row.id) }, () => '查看'),
        h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row.id) }, () => '删除')
      ])
  }
];

const handleBack = () => router.back();

onMounted(fetchProjects);
</script>

<template>
  <div class="cost-projects-list">
    <NPageHeader title="成本项目管理" @back="handleBack" />
    <NCard class="mt-4">
      <template #header>
        <div class="flex items-center justify-between">
          <span>成本项目列表</span>
          <NButton type="primary" @click="handleCreate">创建成本项目</NButton>
        </div>
      </template>

      <NDataTable :columns="columns" :data="projects" :loading="loading" :pagination="pagination" />
    </NCard>
  </div>
</template>

<style scoped>
.cost-projects-list {
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
