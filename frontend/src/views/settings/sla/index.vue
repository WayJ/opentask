<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue';
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
        支持「状态停留」与「首次响应」两种 metric（UTC 日历分钟）。首次响应：非创建者首条评论即满足；指派不算。stop 为空时进入 resolved/closed/rejected 即满足。进入暂停状态时不计时，离开后按剩余时间续跑。无内置 cron，请外部调度 POST /api/sla/run-due。
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
  </div>
</template>
