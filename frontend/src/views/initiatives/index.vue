<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { type DataTableColumns, NButton, NTag } from 'naive-ui';
import {
  type InitiativeRow,
  type InitiativeStatus,
  fetchCreateInitiative,
  fetchDeleteInitiative,
  fetchInitiatives
} from '@/service/api';
import { formatRelationBadge } from '@/utils/initiativeRelations';
import { $t } from '@/locales';

defineOptions({ name: 'InitiativesPage' });

const router = useRouter();
const loading = ref(false);
const rows = ref<InitiativeRow[]>([]);
const total = ref(0);
const createOpen = ref(false);
const creating = ref(false);
const form = reactive({
  name: '',
  description: '',
  status: 'active' as InitiativeStatus
});

const empty = computed(() => !loading.value && rows.value.length === 0);

const statusType: Record<InitiativeStatus, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
  planned: 'default',
  active: 'info',
  completed: 'success',
  canceled: 'error'
};

const statusLabel: Record<InitiativeStatus, string> = {
  planned: '计划中',
  active: '进行中',
  completed: '已完成',
  canceled: '已取消'
};

const healthType: Record<string, 'success' | 'warning' | 'error' | 'default'> = {
  on_track: 'success',
  at_risk: 'warning',
  off_track: 'error'
};
const healthLabel: Record<string, string> = {
  on_track: '顺利',
  at_risk: '风险',
  off_track: '偏离'
};

function renderHealth(row: InitiativeRow) {
  const overall = row.healthSummary?.overall;
  if (!overall) {
    return h(NTag, { size: 'small', bordered: false }, { default: () => '—' });
  }
  return h(
    NTag,
    { type: healthType[overall] || 'default', size: 'small' },
    { default: () => healthLabel[overall] || overall }
  );
}

const columns: DataTableColumns<InitiativeRow> = [
  {
    title: '名称',
    key: 'name',
    render: row =>
      h(NButton, { text: true, type: 'primary', onClick: () => goDetail(row.id) }, { default: () => row.name })
  },
  {
    title: '状态',
    key: 'status',
    width: 110,
    render: row => h(NTag, { type: statusType[row.status], size: 'small' }, { default: () => statusLabel[row.status] })
  },
  {
    title: '健康',
    key: 'health',
    width: 90,
    render: row => renderHealth(row)
  },
  {
    title: '依赖',
    key: 'relations',
    width: 140,
    render: row => {
      const label = formatRelationBadge(row);
      if (!label) return h('span', { class: 'text-gray-400' }, '—');
      return h(NTag, { size: 'small', bordered: false }, { default: () => label });
    }
  },
  {
    title: '关联项目',
    key: 'projectIds',
    width: 100,
    render: row => String(row.projectIds?.length ?? 0)
  },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    render: row =>
      h('div', { class: 'flex gap-8px' }, [
        h(NButton, { size: 'small', onClick: () => goDetail(row.id) }, { default: () => '详情' }),
        h(
          NButton,
          { size: 'small', type: 'error', secondary: true, onClick: () => onDelete(row) },
          { default: () => '删除' }
        )
      ])
  }
];

function goDetail(id: string) {
  router.push({ name: 'initiatives_detail', query: { id } });
}

async function load() {
  loading.value = true;
  try {
    const { data, error } = await fetchInitiatives({ include: 'relationCounts' });
    if (error || !data) {
      window.$message?.error(error?.message || '加载举措失败');
      return;
    }
    rows.value = data.rows || [];
    total.value = data.total ?? 0;
  } finally {
    loading.value = false;
  }
}

async function onCreate() {
  const name = form.name.trim();
  if (!name) {
    window.$message?.warning('请输入名称');
    return;
  }
  creating.value = true;
  try {
    const { error } = await fetchCreateInitiative({
      name,
      description: form.description.trim() || undefined,
      status: form.status
    });
    if (error) {
      window.$message?.error(error.message || '创建失败');
      return;
    }
    window.$message?.success('已创建');
    createOpen.value = false;
    form.name = '';
    form.description = '';
    form.status = 'active';
    await load();
  } finally {
    creating.value = false;
  }
}

async function onDelete(row: InitiativeRow) {
  const { error } = await fetchDeleteInitiative(row.id);
  if (error) {
    window.$message?.error(error.message || '删除失败');
    return;
  }
  window.$message?.success('已删除');
  await load();
}

onMounted(load);
</script>

<template>
  <div class="h-full flex-col gap-16px overflow-hidden p-16px">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-18px font-600">{{ $t('route.initiatives') }}</h2>
        <p class="mt-4px text-13px text-gray-500">跨项目战略目标（问题 / 项目；不含遗留需求）</p>
      </div>
      <NButton type="primary" @click="createOpen = true">{{ $t('page.shell.createInitiative') }}</NButton>
    </div>

    <NCard :bordered="false" class="flex-1 overflow-hidden" content-style="padding: 0; height: 100%">
      <NEmpty v-if="empty" class="py-48px" :description="$t('page.shell.emptyInitiatives')">
        <template #extra>
          <NButton type="primary" @click="createOpen = true">新建</NButton>
        </template>
      </NEmpty>
      <NDataTable
        v-else
        :loading="loading"
        :columns="columns"
        :data="rows"
        :bordered="false"
        :single-line="false"
        flex-height
        class="h-full"
      />
    </NCard>

    <NModal v-model:show="createOpen" preset="card" :title="$t('page.shell.createInitiative')" class="w-480px">
      <NForm label-placement="left" label-width="80">
        <NFormItem label="名称" required>
          <NInput v-model:value="form.name" maxlength="100" placeholder="例如：Q4 增长" />
        </NFormItem>
        <NFormItem label="描述">
          <NInput v-model:value="form.description" type="textarea" :rows="3" />
        </NFormItem>
        <NFormItem label="状态">
          <NSelect
            v-model:value="form.status"
            :options="[
              { label: '计划中', value: 'planned' },
              { label: '进行中', value: 'active' },
              { label: '已完成', value: 'completed' },
              { label: '已取消', value: 'canceled' }
            ]"
          />
        </NFormItem>
      </NForm>
      <template #footer>
        <div class="flex justify-end gap-8px">
          <NButton @click="createOpen = false">取消</NButton>
          <NButton type="primary" :loading="creating" @click="onCreate">创建</NButton>
        </div>
      </template>
    </NModal>
  </div>
</template>
