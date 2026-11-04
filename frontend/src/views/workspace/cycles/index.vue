<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue';
import { type DataTableColumns, NButton, NTag } from 'naive-ui';
import {
  type CycleItem,
  type WorkspaceItem,
  fetchActivateCycle,
  fetchCreateCycle,
  fetchCycles,
  fetchDeleteCycle,
  fetchUpdateWorkspace,
  fetchWorkspace,
  fetchWorkspaceList
} from '@/service/api';
import { localStg } from '@/utils/storage';

defineOptions({ name: 'WorkspaceCyclesPage' });

const loading = ref(false);
const workspace = ref<WorkspaceItem | null>(null);
const rows = ref<CycleItem[]>([]);
const createOpen = ref(false);
const creating = ref(false);

const isOwner = computed(() => workspace.value?.role === 'owner');
const enabled = computed(() => Boolean(workspace.value?.cyclesEnabled));
const hasActive = computed(() => rows.value.some(r => r.status === 'active'));

const settingsForm = reactive({
  cycleDurationDays: 14,
  cycleRolloverPolicy: 'into_next' as 'into_next' | 'leave_unassigned',
  cycleCapacityLookback: 3
});

const createForm = reactive({
  name: '',
  startsAt: null as number | null,
  endsAt: null as number | null
});

const statusType: Record<string, 'default' | 'info' | 'success' | 'warning'> = {
  upcoming: 'default',
  active: 'info',
  completed: 'success'
};

function toIsoDate(ts: number) {
  return new Date(ts).toISOString().slice(0, 19);
}

function formatDt(v?: string | null) {
  if (!v) return '—';
  return String(v).replace('T', ' ').slice(0, 16);
}

async function resolveWorkspaceId(): Promise<string | null> {
  const cached = localStg.get('workspaceId');
  if (cached) return cached;
  const { data, error } = await fetchWorkspaceList();
  if (error || !data?.length) return null;
  localStg.set('workspaceId', data[0].id);
  return data[0].id;
}

async function load() {
  loading.value = true;
  try {
    const wsId = await resolveWorkspaceId();
    if (!wsId) {
      window.$message?.error('未找到工作区');
      return;
    }
    const [wsRes, cyRes] = await Promise.all([fetchWorkspace(wsId), fetchCycles()]);
    if (wsRes.error || !wsRes.data) {
      window.$message?.error(wsRes.error?.message || '加载工作区失败');
      return;
    }
    workspace.value = wsRes.data;
    settingsForm.cycleDurationDays = wsRes.data.cycleDurationDays ?? 14;
    settingsForm.cycleRolloverPolicy =
      (wsRes.data.cycleRolloverPolicy as 'into_next' | 'leave_unassigned') || 'into_next';
    settingsForm.cycleCapacityLookback = wsRes.data.cycleCapacityLookback ?? 3;

    if (cyRes.error) {
      window.$message?.error(cyRes.error.message || '加载 Cycles 失败');
      rows.value = [];
      return;
    }
    rows.value = cyRes.data?.rows || [];
  } finally {
    loading.value = false;
  }
}

async function enableCycles() {
  if (!workspace.value || !isOwner.value) return;
  const { data, error } = await fetchUpdateWorkspace(workspace.value.id, { cyclesEnabled: true });
  if (error || !data) {
    window.$message?.error(error?.message || '启用失败');
    return;
  }
  workspace.value = data;
  window.$message?.success('已启用 Cycles');
  await load();
}

async function onToggleEnabled(value: boolean) {
  if (!workspace.value || !isOwner.value) return;
  const { data, error } = await fetchUpdateWorkspace(workspace.value.id, { cyclesEnabled: value });
  if (error || !data) {
    window.$message?.error(error?.message || '更新失败');
    return;
  }
  workspace.value = data;
  window.$message?.success(value ? '已启用 Cycles' : '已关闭 Cycles');
}

async function saveSettings() {
  if (!workspace.value || !isOwner.value) return;
  const { data, error } = await fetchUpdateWorkspace(workspace.value.id, {
    cycleDurationDays: settingsForm.cycleDurationDays,
    cycleRolloverPolicy: settingsForm.cycleRolloverPolicy,
    cycleCapacityLookback: settingsForm.cycleCapacityLookback
  });
  if (error || !data) {
    window.$message?.error(error?.message || '保存失败');
    return;
  }
  workspace.value = data;
  window.$message?.success('设置已保存');
}

function openCreate() {
  const duration = settingsForm.cycleDurationDays || 14;
  const start = Date.now();
  const end = start + duration * 24 * 60 * 60 * 1000;
  createForm.name = '';
  createForm.startsAt = start;
  createForm.endsAt = end;
  createOpen.value = true;
}

async function submitCreate() {
  if (!createForm.startsAt || !createForm.endsAt) {
    window.$message?.warning('请选择起止时间');
    return;
  }
  creating.value = true;
  try {
    const { error } = await fetchCreateCycle({
      name: createForm.name || undefined,
      starts_at: toIsoDate(createForm.startsAt),
      ends_at: toIsoDate(createForm.endsAt)
    });
    if (error) {
      window.$message?.error(error.message || '创建失败');
      return;
    }
    window.$message?.success('Cycle 已创建');
    createOpen.value = false;
    await load();
  } finally {
    creating.value = false;
  }
}

async function onActivate(row: CycleItem) {
  const { error } = await fetchActivateCycle(row.id);
  if (error) {
    window.$message?.error(error.message || '激活失败');
    return;
  }
  window.$message?.success('已激活');
  await load();
}

async function onDelete(row: CycleItem) {
  const { error } = await fetchDeleteCycle(row.id);
  if (error) {
    window.$message?.error(error.message || '删除失败');
    return;
  }
  window.$message?.success('已删除');
  await load();
}

const columns = computed<DataTableColumns<CycleItem>>(() => [
  { title: '名称', key: 'name', ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    width: 110,
    render: row => h(NTag, { type: statusType[row.status] || 'default', size: 'small' }, { default: () => row.status })
  },
  { title: '开始', key: 'startsAt', width: 150, render: row => formatDt(row.startsAt) },
  { title: '结束', key: 'endsAt', width: 150, render: row => formatDt(row.endsAt) },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    render: row =>
      h('div', { class: 'flex-y-center gap-8px' }, [
        row.status === 'upcoming' && !hasActive.value
          ? h(
              NButton,
              { size: 'tiny', type: 'primary', secondary: true, onClick: () => onActivate(row) },
              { default: () => '激活' }
            )
          : null,
        row.status === 'upcoming'
          ? h(
              NButton,
              { size: 'tiny', type: 'error', secondary: true, onClick: () => onDelete(row) },
              { default: () => '删除' }
            )
          : null
      ])
  }
]);

onMounted(load);
</script>

<template>
  <div class="h-full flex-col gap-16px overflow-auto p-16px">
    <div class="flex-y-center justify-between">
      <div>
        <h2 class="text-18px font-medium">Cycles</h2>
        <p class="text-13px text-gray-500">工作区冲刺节奏（Linear Cycles）</p>
      </div>
      <NButton size="small" @click="load">刷新</NButton>
    </div>

    <NSpin :show="loading">
      <template v-if="workspace && !enabled">
        <NCard>
          <NEmpty description="尚未启用 Cycles">
            <template #extra>
              <NButton type="primary" :disabled="!isOwner" @click="enableCycles">启用 Cycles</NButton>
              <p v-if="!isOwner" class="mt-8px text-12px text-gray-400">仅 owner 可启用</p>
            </template>
          </NEmpty>
        </NCard>
      </template>

      <template v-else-if="workspace">
        <NCard title="设置" size="small" class="mb-16px">
          <div class="flex-col gap-12px">
            <div class="flex-y-center gap-12px">
              <span>启用 Cycles</span>
              <NSwitch :value="enabled" :disabled="!isOwner" @update:value="onToggleEnabled" />
            </div>
            <div class="flex-y-center flex-wrap gap-12px">
              <div class="flex-y-center gap-8px">
                <span class="text-13px">默认天数</span>
                <NInputNumber
                  v-model:value="settingsForm.cycleDurationDays"
                  :min="1"
                  :max="365"
                  :disabled="!isOwner"
                  style="width: 120px"
                />
              </div>
              <NSelect
                v-model:value="settingsForm.cycleRolloverPolicy"
                :disabled="!isOwner"
                style="width: 200px"
                :options="[
                  { label: '未完成滚入下一 Cycle', value: 'into_next' },
                  { label: '未完成取消归属', value: 'leave_unassigned' }
                ]"
              />
              <div class="flex-y-center gap-8px">
                <span class="text-13px">容量回看</span>
                <NInputNumber
                  v-model:value="settingsForm.cycleCapacityLookback"
                  :min="1"
                  :max="20"
                  :disabled="!isOwner"
                  style="width: 120px"
                />
              </div>
              <NButton type="primary" secondary :disabled="!isOwner" @click="saveSettings">保存设置</NButton>
            </div>
          </div>
        </NCard>

        <NCard size="small">
          <template #header>
            <div class="flex-y-center justify-between">
              <span>Cycle 列表</span>
              <NButton type="primary" size="small" @click="openCreate">创建 Cycle</NButton>
            </div>
          </template>
          <NDataTable :columns="columns" :data="rows" :bordered="false" size="small" />
        </NCard>
      </template>
    </NSpin>

    <NModal v-model:show="createOpen" preset="card" title="创建 Upcoming Cycle" style="width: 480px">
      <div class="flex-col gap-12px">
        <NInput v-model:value="createForm.name" placeholder="名称（可空，默认 Cycle N）" />
        <NDatePicker v-model:value="createForm.startsAt" type="datetime" class="w-full" />
        <NDatePicker v-model:value="createForm.endsAt" type="datetime" class="w-full" />
        <div class="flex justify-end gap-8px">
          <NButton @click="createOpen = false">取消</NButton>
          <NButton type="primary" :loading="creating" @click="submitCreate">创建</NButton>
        </div>
      </div>
    </NModal>
  </div>
</template>
