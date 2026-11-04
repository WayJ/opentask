<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue';
import { type DataTableColumns, NButton, NTag } from 'naive-ui';
import {
  type CapacityHint,
  type CycleItem,
  type WorkspaceItem,
  fetchActivateCycle,
  fetchCapacityHint,
  fetchCompleteCycle,
  fetchCreateCycle,
  fetchCycles,
  fetchDeleteCycle,
  fetchGenerateUpcoming,
  fetchUpdateWorkspace,
  fetchWorkspace,
  fetchWorkspaceList
} from '@/service/api';
import { issueApi } from '@/service/api/issue';
import { localStg } from '@/utils/storage';

defineOptions({ name: 'WorkspaceCyclesPage' });

const DONE = new Set(['resolved', 'closed']);

const loading = ref(false);
const workspace = ref<WorkspaceItem | null>(null);
const rows = ref<CycleItem[]>([]);
const capacity = ref<CapacityHint | null>(null);
const createOpen = ref(false);
const creating = ref(false);
const completeOpen = ref(false);
const completing = ref(false);
const completeTarget = ref<CycleItem | null>(null);
const incompletePreview = ref(0);
const generating = ref(false);

const isOwner = computed(() => workspace.value?.role === 'owner');
const enabled = computed(() => Boolean(workspace.value?.cyclesEnabled));
const hasActive = computed(() => rows.value.some(r => r.status === 'active'));
const hasUpcoming = computed(() => rows.value.some(r => r.status === 'upcoming'));
const activeCycle = computed(() => rows.value.find(r => r.status === 'active') || null);

const settingsForm = reactive({
  cycleDurationDays: 14,
  cycleRolloverPolicy: 'into_next' as 'into_next' | 'leave_unassigned',
  cycleCapacityLookback: 3,
  issueKey: 'OT',
  gitStatusHooksEnabled: false
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

const capacityText = computed(() => {
  if (!capacity.value) return '';
  const unit = capacity.value.unit || (capacity.value.basis === 'members' ? 'members' : 'issues');
  const unitLabel =
    unit === 'points' ? '点' : unit === 'members' ? '（成员数）' : '个 Issue';
  let text = '';
  if (capacity.value.basis === 'history') {
    text = `建议容量约 ${capacity.value.suggestedCapacity} ${unitLabel}（近 ${capacity.value.lookbackN} 个已完成 Cycle 均值；默认按故事点，无点时回退 Issue 数）`;
  } else {
    text = `建议容量约 ${capacity.value.suggestedCapacity} ${unitLabel}（尚无完成历史，按成员数回退）`;
  }
  const load = capacity.value.currentLoad;
  if (load) {
    text += `；当前 Cycle 负载 ${load.points} 点 / ${load.issueCount} Issue`;
    if (load.hours) text += ` / ${load.hours}h`;
  }
  return text;
});

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

async function loadCapacity() {
  const { data, error } = await fetchCapacityHint(activeCycle.value ? { cycle_id: activeCycle.value.id } : undefined);
  if (error || !data) {
    capacity.value = null;
    return;
  }
  capacity.value = data;
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
    settingsForm.issueKey = (wsRes.data.issueKey || 'OT').toUpperCase();
    settingsForm.gitStatusHooksEnabled = Boolean(wsRes.data.gitStatusHooksEnabled);

    if (cyRes.error) {
      window.$message?.error(cyRes.error.message || '加载 Cycles 失败');
      rows.value = [];
      capacity.value = null;
      return;
    }
    rows.value = cyRes.data?.rows || [];
    if (wsRes.data.cyclesEnabled) {
      await loadCapacity();
    } else {
      capacity.value = null;
    }
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
  if (value) await loadCapacity();
  else capacity.value = null;
}

async function onToggleGitHooks(value: boolean) {
  if (!workspace.value || !isOwner.value) return;
  const { data, error } = await fetchUpdateWorkspace(workspace.value.id, {
    gitStatusHooksEnabled: value
  });
  if (error || !data) {
    window.$message?.error(error?.message || '更新 Git 钩子失败');
    return;
  }
  workspace.value = data;
  settingsForm.gitStatusHooksEnabled = Boolean(data.gitStatusHooksEnabled);
  window.$message?.success(value ? '已开启：从 PR 自动更新 Issue 状态' : '已关闭 PR 状态钩子');
}

async function saveSettings() {
  if (!workspace.value || !isOwner.value) return;
  const { data, error } = await fetchUpdateWorkspace(workspace.value.id, {
    cycleDurationDays: settingsForm.cycleDurationDays,
    cycleRolloverPolicy: settingsForm.cycleRolloverPolicy,
    cycleCapacityLookback: settingsForm.cycleCapacityLookback,
    issueKey: settingsForm.issueKey
  });
  if (error || !data) {
    window.$message?.error(error?.message || '保存失败');
    return;
  }
  workspace.value = data;
  window.$message?.success('设置已保存');
  await loadCapacity();
}

function onIssueKeyInput(v: string) {
  settingsForm.issueKey = (v || '').toUpperCase();
}

async function saveIssueKeyOnly() {
  if (!workspace.value || !isOwner.value) return;
  const { data, error } = await fetchUpdateWorkspace(workspace.value.id, {
    issueKey: settingsForm.issueKey
  });
  if (error || !data) {
    window.$message?.error(error?.message || '保存失败');
    return;
  }
  workspace.value = data;
  settingsForm.issueKey = (data.issueKey || settingsForm.issueKey).toUpperCase();
  window.$message?.success('Issue Key 已保存');
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

async function openComplete(row: CycleItem) {
  completeTarget.value = row;
  incompletePreview.value = 0;
  completeOpen.value = true;
  try {
    const { data, error } = await issueApi.getIssues({
      cycle_id: row.id,
      page: 1,
      page_size: 200
    } as any);
    if (!error && data?.rows) {
      incompletePreview.value = data.rows.filter((i: any) => !DONE.has(String(i.status))).length;
    }
  } catch {
    incompletePreview.value = 0;
  }
}

async function submitComplete() {
  if (!completeTarget.value) return;
  completing.value = true;
  try {
    const { data, error } = await fetchCompleteCycle(completeTarget.value.id);
    if (error || !data) {
      window.$message?.error(error?.message || '结束失败');
      return;
    }
    const rolled = data.rolledCount ?? 0;
    window.$message?.success(
      settingsForm.cycleRolloverPolicy === 'into_next'
        ? `Cycle 已结束，已滚动 ${rolled} 个未完成 Issue`
        : `Cycle 已结束，已取消 ${rolled} 个未完成归属`
    );
    completeOpen.value = false;
    completeTarget.value = null;
    await load();
  } finally {
    completing.value = false;
  }
}

async function onGenerateUpcoming() {
  generating.value = true;
  try {
    const { error } = await fetchGenerateUpcoming();
    if (error) {
      window.$message?.error(error.message || '生成失败');
      return;
    }
    window.$message?.success('已生成下一 Cycle');
    await load();
  } finally {
    generating.value = false;
  }
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
    width: 220,
    render: row =>
      h('div', { class: 'flex-y-center gap-8px' }, [
        row.status === 'upcoming' && !hasActive.value
          ? h(
              NButton,
              { size: 'tiny', type: 'primary', secondary: true, onClick: () => onActivate(row) },
              { default: () => '激活' }
            )
          : null,
        row.status === 'active'
          ? h(
              NButton,
              { size: 'tiny', type: 'warning', secondary: true, onClick: () => openComplete(row) },
              { default: () => '结束' }
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
  <div class="h-full flex-col gap-12px overflow-auto p-12px">
    <div class="flex-y-center justify-between">
      <div>
        <h2 class="text-18px font-medium">Cycles</h2>
        <p class="text-13px text-gray-500">工作区冲刺节奏（Linear Cycles）</p>
      </div>
      <NButton size="small" @click="load">刷新</NButton>
    </div>

    <NSpin :show="loading">
      <template v-if="workspace && !enabled">
        <NCard title="Issue 单号前缀" size="small" class="mb-16px">
          <div class="flex-y-center flex-wrap gap-12px">
            <div class="flex-y-center gap-8px">
              <span class="text-13px">Issue Key</span>
              <NInput
                v-model:value="settingsForm.issueKey"
                :disabled="!isOwner"
                maxlength="6"
                placeholder="OT"
                style="width: 120px; text-transform: uppercase"
                @update:value="onIssueKeyInput"
              />
            </div>
            <NButton type="primary" secondary :disabled="!isOwner" @click="saveIssueKeyOnly">保存</NButton>
            <p class="text-12px text-gray-400">2–6 位大写字母或数字；更改后下一单从 1 重新编号（旧单号保留）</p>
          </div>
        </NCard>

        <NCard title="Git / PR" size="small" class="mb-16px">
          <div class="flex-y-center gap-12px flex-wrap">
            <span>从 PR 自动更新 Issue 状态</span>
            <NSwitch
              :value="settingsForm.gitStatusHooksEnabled"
              :disabled="!isOwner"
              @update:value="onToggleGitHooks"
            />
            <p class="text-12px text-gray-400 w-full">
              默认关闭。开启后：PR open → in_progress（仅自 open）；merged → resolved；未合并 close 不改 Issue。
            </p>
          </div>
        </NCard>
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
            <div class="flex-y-center gap-12px flex-wrap">
              <span>从 PR 自动更新 Issue 状态</span>
              <NSwitch
                :value="settingsForm.gitStatusHooksEnabled"
                :disabled="!isOwner"
                @update:value="onToggleGitHooks"
              />
              <span class="text-12px text-gray-400">默认关；open→in_progress，merged→resolved</span>
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
              <div class="flex-y-center gap-8px">
                <span class="text-13px">Issue Key</span>
                <NInput
                  v-model:value="settingsForm.issueKey"
                  :disabled="!isOwner"
                  maxlength="6"
                  placeholder="OT"
                  style="width: 120px; text-transform: uppercase"
                  @update:value="onIssueKeyInput"
                />
              </div>
              <NButton type="primary" secondary :disabled="!isOwner" @click="saveSettings">保存设置</NButton>
            </div>
          </div>
        </NCard>

        <NCard v-if="capacity" title="容量提示" size="small" class="mb-16px">
          <p class="text-14px">{{ capacityText }}</p>
          <p v-if="activeCycle" class="mt-4px text-12px text-gray-500">当前 Active：{{ activeCycle.name }}</p>
        </NCard>

        <NCard size="small">
          <template #header>
            <div class="flex-y-center justify-between gap-8px">
              <span>Cycle 列表</span>
              <div class="flex-y-center gap-8px">
                <NButton
                  v-if="!hasUpcoming"
                  size="small"
                  secondary
                  type="info"
                  :loading="generating"
                  @click="onGenerateUpcoming"
                >
                  生成下一 Cycle
                </NButton>
                <NButton type="primary" size="small" @click="openCreate">创建 Cycle</NButton>
              </div>
            </div>
          </template>

          <NEmpty v-if="!rows.length" description="还没有 Cycle">
            <template #extra>
              <div class="flex-y-center gap-8px">
                <NButton type="info" secondary :loading="generating" @click="onGenerateUpcoming">
                  一键生成 Upcoming
                </NButton>
                <NButton type="primary" @click="openCreate">手动创建</NButton>
              </div>
            </template>
          </NEmpty>
          <template v-else>
            <NAlert v-if="!hasUpcoming" type="info" class="mb-12px" title="没有 Upcoming Cycle">
              可一键按默认天数生成下一冲刺，或手动创建。
              <template #action>
                <NButton size="small" type="primary" :loading="generating" @click="onGenerateUpcoming">
                  生成下一 Cycle
                </NButton>
              </template>
            </NAlert>
            <NDataTable :columns="columns" :data="rows" :bordered="false" size="small" />
          </template>
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

    <NModal v-model:show="completeOpen" preset="card" title="结束 Cycle" style="width: 480px">
      <div class="flex-col gap-12px">
        <p>
          确认结束
          <strong>{{ completeTarget?.name }}</strong>
          ？
        </p>
        <NAlert type="warning" :bordered="false">
          预计将处理
          <strong>{{ incompletePreview }}</strong>
          个未完成 Issue（策略：
          {{
            settingsForm.cycleRolloverPolicy === 'into_next' ? '滚入下一 Cycle（必要时自动生成）' : '取消 Cycle 归属'
          }}）。已完成（resolved/closed）将留在原 Cycle。
        </NAlert>
        <div class="flex justify-end gap-8px">
          <NButton @click="completeOpen = false">取消</NButton>
          <NButton type="warning" :loading="completing" @click="submitComplete">确认结束</NButton>
        </div>
      </div>
    </NModal>
  </div>
</template>
