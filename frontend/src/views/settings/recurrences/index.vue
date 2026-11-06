<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue';
import {
  type DataTableColumns,
  NButton,
  NCard,
  NInput,
  NSelect,
  NSpace,
  NSwitch,
  NText
} from 'naive-ui';
import {
  type RecurrenceRow,
  RECURRENCE_INTERVALS,
  fetchCreateRecurrence,
  fetchDeleteRecurrence,
  fetchRecurrences,
  fetchRunDueRecurrences,
  fetchUpdateRecurrence,
  formatNextRun
} from '@/service/api/recurrences';

defineOptions({ name: 'SettingsRecurrencesPage' });

const loading = ref(false);
const rows = ref<RecurrenceRow[]>([]);
const creating = ref(false);
const running = ref(false);
const form = reactive({
  titleTemplate: 'Periodic {date}',
  interval: 'daily' as string,
  nextRunAt: new Date().toISOString().slice(0, 19),
  description: '',
  priority: 'medium',
  labels: '',
  weekday: '',
  monthday: ''
});

const intervalOptions = RECURRENCE_INTERVALS.map(v => ({ label: v, value: v }));

const columns: DataTableColumns<RecurrenceRow> = [
  {
    title: '标题模板',
    key: 'titleTemplate',
    render: row =>
      h('div', [
        h('div', { style: 'font-weight:500' }, row.titleTemplate),
        h(NText, { depth: 3, style: 'font-size:12px' }, { default: () => row.interval })
      ])
  },
  {
    title: '下次运行 (UTC)',
    key: 'nextRunAt',
    render: row => formatNextRun(row.nextRunAt)
  },
  {
    title: '最近问题',
    key: 'lastIssueId',
    render: row => (row.lastIssueId ? row.lastIssueId.slice(0, 8) + '…' : '—')
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
    const { data, error } = await fetchRecurrences();
    if (error) {
      window.$message?.error?.(error.message || '加载失败');
      return;
    }
    rows.value = data?.rows || [];
  } finally {
    loading.value = false;
  }
}

async function createRow() {
  if (!form.titleTemplate.trim()) {
    window.$message?.warning?.('请填写标题模板');
    return;
  }
  creating.value = true;
  try {
    const labels = form.labels
      .split(',')
      .map(s => s.trim())
      .filter(Boolean);
    const body: Parameters<typeof fetchCreateRecurrence>[0] = {
      titleTemplate: form.titleTemplate.trim(),
      interval: form.interval,
      nextRunAt: form.nextRunAt,
      description: form.description.trim() || undefined,
      priority: form.priority || undefined,
      labels: labels.length ? labels : undefined
    };
    if (form.interval === 'weekly' && form.weekday !== '') {
      body.weekday = Number(form.weekday);
    }
    if (form.interval === 'monthly' && form.monthday !== '') {
      body.monthday = Number(form.monthday);
    }
    const { error } = await fetchCreateRecurrence(body);
    if (error) {
      window.$message?.error?.(error.message || '创建失败');
      return;
    }
    window.$message?.success?.('已创建周期规则');
    await load();
  } finally {
    creating.value = false;
  }
}

async function toggle(row: RecurrenceRow, enabled: boolean) {
  const prev = row.enabled;
  row.enabled = enabled;
  const { error } = await fetchUpdateRecurrence(row.id, { enabled });
  if (error) {
    row.enabled = prev;
    window.$message?.error?.(error.message || '更新失败');
  }
}

async function removeRow(id: string) {
  const { error } = await fetchDeleteRecurrence(id);
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
    const { data, error } = await fetchRunDueRecurrences();
    if (error) {
      window.$message?.error?.(error.message || '执行失败');
      return;
    }
    window.$message?.success?.(`已创建 ${data?.created ?? 0} 张问题`);
    await load();
  } finally {
    running.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="p-4">
    <NCard title="周期建单 (Recurrences)" :bordered="false">
      <template #header-extra>
        <NSpace>
          <NText depth="3">标题日期按工作区时区；next_run_at 存 UTC · 外部调度调 run-due</NText>
          <NButton size="small" :loading="running" @click="runDue">立即 run-due</NButton>
        </NSpace>
      </template>

      <NCard size="small" title="新建" class="mb-4">
        <NSpace vertical>
          <NInput v-model:value="form.titleTemplate" placeholder="标题模板，支持 {date} / {yyyy-mm-dd}" />
          <NSelect v-model:value="form.interval" :options="intervalOptions" />
          <NInput v-model:value="form.nextRunAt" placeholder="nextRunAt ISO（UTC naive）" />
          <NInput v-model:value="form.description" type="textarea" placeholder="描述（可选）" :rows="2" />
          <NInput v-model:value="form.priority" placeholder="priority（low/medium/high…）" />
          <NInput v-model:value="form.labels" placeholder="labels 逗号分隔（tag name）" />
          <NInput
            v-if="form.interval === 'weekly'"
            v-model:value="form.weekday"
            placeholder="weekday 0=周一 … 6=周日（可选）"
          />
          <NInput
            v-if="form.interval === 'monthly'"
            v-model:value="form.monthday"
            placeholder="monthday 1–31（可选）"
          />
          <NButton type="primary" :loading="creating" @click="createRow">创建</NButton>
        </NSpace>
      </NCard>

      <NDataTable :columns="columns" :data="rows" :loading="loading" :bordered="false" size="small" />
      <div v-if="!loading && !rows.length" class="py-8 text-center opacity-60">
        尚无周期规则。创建后由调度器或「立即 run-due」生成问题。
      </div>
    </NCard>
  </div>
</template>
