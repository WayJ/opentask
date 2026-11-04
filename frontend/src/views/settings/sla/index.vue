<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue';
import {
  type DataTableColumns,
  NButton,
  NCard,
  NDataTable,
  NInput,
  NInputNumber,
  NSelect,
  NSpace,
  NSwitch,
  NText
} from 'naive-ui';
import {
  ISSUE_STATUSES,
  type SlaPolicyRow,
  fetchCreateSlaPolicy,
  fetchDeleteSlaPolicy,
  fetchSlaPolicies,
  fetchSlaRunDue,
  fetchUpdateSlaPolicy,
  slaMetricLabel
} from '@/service/api/sla';
import {
  type WorkspaceItem,
  fetchUpdateWorkspace,
  fetchWorkspace,
  fetchWorkspaceList
} from '@/service/api/workspace';
import { localStg } from '@/utils/storage';
import {
  WEEKDAY_KEYS,
  WEEKDAY_LABELS,
  type WeekdayKey,
  emptyWindows,
  normalizeBusinessHours,
  normalizeWindows,
  validateTimezoneClient,
  weekdayPreset0918
} from '@/utils/businessHours';

defineOptions({ name: 'SettingsSlaPage' });

const loading = ref(false);
const rows = ref<SlaPolicyRow[]>([]);
const creating = ref(false);
const running = ref(false);
const form = reactive({
  name: 'Time in progress',
  startStatuses: ['in_progress'] as string[],
  stopStatuses: ['resolved', 'closed'] as string[],
  pauseStatuses: [] as string[],
  targetMinutes: 1440,
  metric: 'time_in_status',
  notifyAssignee: true,
  notifyWatchers: false
});

const statusOptions = ISSUE_STATUSES.map(v => ({ label: v, value: v }));

const workspace = ref<WorkspaceItem | null>(null);
const bhSaving = ref(false);
const bhForm = reactive({
  timezone: 'Asia/Shanghai',
  enabled: false,
  windows: emptyWindows() as Record<WeekdayKey, { start: string; end: string }[]>
});
const timezoneOptions = [
  { label: 'Asia/Shanghai', value: 'Asia/Shanghai' },
  { label: 'UTC', value: 'UTC' },
  { label: 'America/Los_Angeles', value: 'America/Los_Angeles' },
  { label: 'America/New_York', value: 'America/New_York' },
  { label: 'Europe/London', value: 'Europe/London' }
];
const isOwner = computed(() => workspace.value?.role === 'owner');

async function resolveWorkspaceId(): Promise<string | null> {
  const cached = localStg.get('workspaceId');
  if (cached) return String(cached);
  const { data, error } = await fetchWorkspaceList();
  if (error || !data?.length) return null;
  localStg.set('workspaceId', data[0].id);
  return data[0].id;
}

async function loadBusinessHours() {
  const wsId = await resolveWorkspaceId();
  if (!wsId) return;
  const { data, error } = await fetchWorkspace(wsId);
  if (error || !data) return;
  workspace.value = data;
  const bh = normalizeBusinessHours(data.businessHours || null);
  bhForm.timezone = data.timezone || 'Asia/Shanghai';
  bhForm.enabled = bh.enabled;
  bhForm.windows = bh.windows;
}

function applyWeekdayPreset() {
  bhForm.windows = weekdayPreset0918();
}

function setDaySegments(day: WeekdayKey, raw: string) {
  // raw: "09:00-12:00,13:00-18:00" or empty
  const parts = String(raw || '')
    .split(',')
    .map(s => s.trim())
    .filter(Boolean);
  const segs = parts.map(p => {
    const [start, end] = p.split('-').map(x => x.trim());
    return { start: start || '', end: end || '' };
  });
  bhForm.windows[day] = segs;
}

function daySegmentsText(day: WeekdayKey): string {
  return (bhForm.windows[day] || []).map(s => `${s.start}-${s.end}`).join(',');
}

async function saveBusinessHours() {
  if (!workspace.value || !isOwner.value) return;
  bhSaving.value = true;
  try {
    let tz: string | null;
    let windows;
    try {
      tz = validateTimezoneClient(bhForm.timezone);
      windows = normalizeWindows(bhForm.windows);
    } catch (e: any) {
      window.$message?.error?.(e?.message || '时段非法');
      return;
    }
    const { data, error } = await fetchUpdateWorkspace(workspace.value.id, {
      timezone: tz,
      businessHours: { enabled: bhForm.enabled, windows }
    });
    if (error || !data) {
      window.$message?.error?.(error?.message || '保存失败');
      return;
    }
    workspace.value = data;
    window.$message?.success?.('营业时段已保存（running/paused deadline 已重算）');
    await loadBusinessHours();
  } finally {
    bhSaving.value = false;
  }
}

const metricOptions = [
  { label: '状态停留 (time_in_status)', value: 'time_in_status' },
  { label: '首次响应 (first_response)', value: 'first_response' }
];

const columns: DataTableColumns<SlaPolicyRow> = [
  {
    title: '名称',
    key: 'name',
    render: row =>
      h('div', [
        h('div', { style: 'font-weight:500' }, row.name),
        h(NText, { depth: 3, style: 'font-size:12px' }, { default: () => `${row.targetMinutes} 分钟 · ${slaMetricLabel(row.metric)}` })
      ])
  },
  {
    title: '启停状态',
    key: 'statuses',
    render: row =>
      h(
        NText,
        { depth: 3, style: 'font-size:12px' },
        {
          default: () =>
            `start: ${(row.startStatuses || []).join(', ') || '—'} → stop: ${(row.stopStatuses || []).join(', ') || '关闭类'} · pause: ${(row.pauseStatuses || []).join(', ') || '—'}`
        }
      )
  },
  {
    title: '启用',
    key: 'enabled',
    width: 90,
    render: row =>
      h(NSwitch, {
        value: row.enabled,
        size: 'small',
        onUpdateValue: (v: boolean) => toggle(row, v)
      })
  },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    render: row =>
      h(
        NButton,
        { size: 'tiny', tertiary: true, type: 'error', onClick: () => removeRow(row.id) },
        { default: () => '删除' }
      )
  }
];

async function load() {
  loading.value = true;
  try {
    const { data, error } = await fetchSlaPolicies();
    if (error) {
      window.$message?.error?.(error.message || '加载失败');
      return;
    }
    rows.value = data?.rows || [];
  } finally {
    loading.value = false;
  }
}

async function create() {
  if (!form.name.trim() || !form.startStatuses.length) {
    window.$message?.warning?.('名称与 startStatuses 必填');
    return;
  }
  creating.value = true;
  try {
    const { error } = await fetchCreateSlaPolicy({
      name: form.name.trim(),
      startStatuses: form.startStatuses,
      stopStatuses: form.stopStatuses,
      pauseStatuses: form.pauseStatuses,
      targetMinutes: form.targetMinutes,
      metric: form.metric,
      notifyAssignee: form.notifyAssignee,
      notifyWatchers: form.notifyWatchers
    });
    if (error) {
      window.$message?.error?.(error.message || '创建失败');
      return;
    }
    window.$message?.success?.('已创建');
    await load();
  } finally {
    creating.value = false;
  }
}

async function toggle(row: SlaPolicyRow, enabled: boolean) {
  const { error } = await fetchUpdateSlaPolicy(row.id, { enabled });
  if (error) {
    window.$message?.error?.(error.message || '更新失败');
    return;
  }
  row.enabled = enabled;
}

async function removeRow(id: string) {
  const { error } = await fetchDeleteSlaPolicy(id);
  if (error) {
    window.$message?.error?.(error.message || '删除失败');
    return;
  }
  window.$message?.success?.('已删除');
  await load();
}

async function runDue() {
  running.value = true;
  try {
    const { data, error } = await fetchSlaRunDue();
    if (error) {
      window.$message?.error?.(error.message || '执行失败');
      return;
    }
    window.$message?.success?.(
      `扫描 ${data?.scanned ?? 0} · 违约 ${data?.breached ?? 0} · 通知 ${data?.notificationsCreated ?? 0}`
    );
  } finally {
    running.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="p-4">
    <NCard title="SLA 策略" :bordered="false">
      <template #header-extra>
        <NSpace>
          <NButton size="small" :loading="running" @click="runDue">立即 run-due</NButton>
          <NButton size="small" @click="load">刷新</NButton>
        </NSpace>
      </template>
      <NText depth="3" style="display:block;margin-bottom:12px;font-size:12px">
        支持「状态停留」与「首次响应」两种 metric。默认墙钟分钟；下方启用营业时后按营业分钟。首次响应：非创建者首条评论即满足；指派不算。stop 为空时进入 resolved/closed/rejected 即满足。进入暂停状态时不计时，离开后按剩余时间续跑。无内置 cron，请外部调度 POST /api/sla/run-due。
      </NText>
      <NDataTable :columns="columns" :data="rows" :loading="loading" size="small" />
    </NCard>

    <NCard title="新建策略" :bordered="false" style="margin-top:16px">
      <NSpace vertical>
        <NInput v-model:value="form.name" placeholder="名称" maxlength="80" />
        <NSelect v-model:value="form.metric" :options="metricOptions" placeholder="metric" />
        <NText depth="3" style="font-size:12px">首次响应：非创建者首条评论算首响；指派负责人不算。</NText>
        <NSelect v-model:value="form.startStatuses" multiple :options="statusOptions" placeholder="startStatuses" />
        <NSelect v-model:value="form.stopStatuses" multiple :options="statusOptions" placeholder="stopStatuses（可空=关闭类）" />
        <NSelect
          v-model:value="form.pauseStatuses"
          multiple
          :options="statusOptions"
          placeholder="暂停计时的状态（可空=不启用暂停；示例 feedback）"
        />
        <NText depth="3" style="font-size:12px">进入这些状态时 SLA 暂停；离开后按剩余时间续跑。优先级：stop &gt; pause &gt; start。</NText>
        <NInputNumber v-model:value="form.targetMinutes" :min="1" :max="10080" placeholder="targetMinutes" />
        <NSpace>
          <span>通知负责人</span>
          <NSwitch v-model:value="form.notifyAssignee" />
          <span>通知关注者</span>
          <NSwitch v-model:value="form.notifyWatchers" />
        </NSpace>
        <NButton type="primary" :loading="creating" @click="create">创建</NButton>
      </NSpace>
    </NCard>

    <NCard title="营业时段（SLA business hours）" :bordered="false" style="margin-top:16px">
      <NText depth="3" style="display:block;margin-bottom:12px;font-size:12px">
        工作区级 IANA 时区 + 周内营业窗口。启用后 SLA deadline / pause 剩余按营业分钟计算；关闭则回退墙钟。配置保存后批量重算 running/paused。每日最多 2 段，格式 09:00-12:00,13:00-18:00。
      </NText>
      <NSpace vertical>
        <NSpace align="center">
          <span>启用营业时</span>
          <NSwitch v-model:value="bhForm.enabled" :disabled="!isOwner" />
          <NSelect
            v-model:value="bhForm.timezone"
            :options="timezoneOptions"
            style="width:220px"
            :disabled="!isOwner"
            filterable
            tag
          />
          <NButton size="small" :disabled="!isOwner" @click="applyWeekdayPreset">工作日 09–18</NButton>
        </NSpace>
        <div v-for="day in WEEKDAY_KEYS" :key="day" style="display:flex;gap:8px;align-items:center">
          <span style="width:48px">{{ WEEKDAY_LABELS[day] }}</span>
          <NInput
            :value="daySegmentsText(day)"
            :disabled="!isOwner"
            placeholder="空=非营业；例 09:00-12:00,13:00-18:00"
            @update:value="(v: string) => setDaySegments(day, v)"
          />
        </div>
        <NButton type="primary" :loading="bhSaving" :disabled="!isOwner" @click="saveBusinessHours">保存营业时段</NButton>
      </NSpace>
    </NCard>
  </div>
</template>
