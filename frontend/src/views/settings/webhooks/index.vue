<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue';
import {
  type DataTableColumns,
  NButton,
  NCard,
  NCheckbox,
  NCheckboxGroup,
  NDataTable,
  NInput,
  NInputNumber,
  NModal,
  NRadioButton,
  NRadioGroup,
  NSelect,
  NSpace,
  NSwitch,
  NTag,
  NText
} from 'naive-ui';
import {
  type DeadLetterRow,
  type StatWindow,
  type WebhookAlertSettings,
  type WebhookDelivery,
  type WebhookRow,
  type WebhookStatsPayload,
  DEFAULT_ALERT_SETTINGS,
  DEFAULT_STAT_WINDOW,
  STAT_WINDOWS,
  WEBHOOK_EVENTS,
  WEBHOOK_EVENT_LABELS,
  applyIntegrationPreset,
  clearIntegrationPreset,
  fetchBulkRetryDeadLetter,
  fetchCreateWebhook,
  fetchDeadLetter,
  fetchDeleteWebhook,
  fetchMuteWebhookAlerts,
  fetchRetryWebhookDelivery,
  fetchSetWebhookAlertSettings,
  fetchTestWebhook,
  fetchUnmuteWebhookAlerts,
  fetchUpdateWebhook,
  fetchWebhook,
  fetchWebhookAlertSettings,
  fetchWebhookStats,
  fetchWebhooks,
  filterDeadLetterRows,
  filterDeliveriesByEvent,
  formatSuccessRate,
  isAlertPending,
  isAutoDisabledWebhook,
  isDeliveryReplayable,
  normalizeAlertSettings,
  normalizeStatsPayload
} from '@/service/api/webhooks';

defineOptions({ name: 'SettingsWebhooksPage' });

const loading = ref(false);
const rows = ref<WebhookRow[]>([]);
const creating = ref(false);
const secretModal = ref(false);
const oneTimeSecret = ref('');
const detailOpen = ref(false);
const detailLoading = ref(false);
const detail = ref<WebhookRow | null>(null);
const statusFilter = ref<'all' | 'fail'>('all');
const eventFilter = ref<string>('all');
const form = reactive({
  name: '',
  url: '',
  events: [...WEBHOOK_EVENTS] as string[]
});

/** E54 observability */
const statsWindow = ref<StatWindow>(DEFAULT_STAT_WINDOW);
const statsLoading = ref(false);
const stats = ref<WebhookStatsPayload | null>(null);
const deadOpen = ref(false);
const deadLoading = ref(false);
const deadRows = ref<DeadLetterRow[]>([]);
const deadHookFilter = ref<string>('all');
const deadEventFilter = ref<string>('all');
const deadSelected = ref<string[]>([]);
const bulkRetrying = ref(false);

/** E57 alert settings */
const alertOpen = ref(false);
const alertSaving = ref(false);
const alertForm = reactive({ ...DEFAULT_ALERT_SETTINGS } as WebhookAlertSettings);
const muteUntilInput = ref('');
const alertPendingLabel = computed(() =>
  isAlertPending(normalizeAlertSettings(alertForm)) ? '告警开启中' : '已关闭或静音'
);

async function loadAlertSettings() {
  const { data, error } = await fetchWebhookAlertSettings();
  if (error) {
    window.$message?.error?.(error.message || '告警设置加载失败');
    return;
  }
  const s = normalizeAlertSettings(data?.settings || data?.effective);
  Object.assign(alertForm, s);
  muteUntilInput.value = s.muteUntil || '';
}

async function saveAlertSettings() {
  alertSaving.value = true;
  try {
    const { error } = await fetchSetWebhookAlertSettings({
      settings: {
        enabled: alertForm.enabled,
        windowHours: Number(alertForm.windowHours) || 24,
        deadThreshold: Number(alertForm.deadThreshold) || 10,
        consecutiveDeadThreshold: alertForm.consecutiveDeadThreshold,
        autoDisable: alertForm.autoDisable,
        muteUntil: muteUntilInput.value || null
      }
    });
    if (error) {
      window.$message?.error?.(error.message || '保存失败');
      return;
    }
    window.$message?.success?.('告警设置已保存');
    await loadAlertSettings();
  } finally {
    alertSaving.value = false;
  }
}

async function muteAlertsNow() {
  const until = muteUntilInput.value.trim();
  if (!until) {
    window.$message?.warning?.('请填写 muteUntil（ISO）');
    return;
  }
  const { error } = await fetchMuteWebhookAlerts(until);
  if (error) {
    window.$message?.error?.(error.message || '静音失败');
    return;
  }
  window.$message?.success?.('已静音');
  await loadAlertSettings();
}

async function unmuteAlertsNow() {
  const { error } = await fetchUnmuteWebhookAlerts();
  if (error) {
    window.$message?.error?.(error.message || '取消静音失败');
    return;
  }
  window.$message?.success?.('已取消静音');
  await loadAlertSettings();
}

async function reenableAutoDisabled(webhookId: string) {
  const { error } = await fetchUpdateWebhook(webhookId, { enabled: true });
  if (error) {
    window.$message?.error?.(error.message || '启用失败');
    return;
  }
  window.$message?.success?.('已重新启用');
  await load();
  if (deadOpen.value) await loadDeadLetter();
}

const windowOptions = STAT_WINDOWS.map(w => ({ label: w, value: w }));

const hookFilterOptions = computed(() => [
  { label: '全部钩子', value: 'all' },
  ...rows.value.map(r => ({
    label: r.name || r.url,
    value: r.id
  }))
]);

const filteredDeadRows = computed(() =>
  filterDeadLetterRows(deadRows.value, deadHookFilter.value, deadEventFilter.value)
);

const successRateLabel = computed(() => formatSuccessRate(stats.value?.totals.successRate));
const deadCountLabel = computed(() => String(stats.value?.totals.dead ?? 0));


const eventOptions = WEBHOOK_EVENTS.map(e => ({ label: WEBHOOK_EVENT_LABELS[e] || e, value: e }));

const eventFilterOptions = [
  { label: '全部事件', value: 'all' },
  ...WEBHOOK_EVENTS.map(e => ({ label: WEBHOOK_EVENT_LABELS[e] || e, value: e }))
];

function useIntegrationPreset() {
  form.events = applyIntegrationPreset(form.events);
}

function clearPreset() {
  form.events = clearIntegrationPreset(form.events);
}

const filteredDeliveries = computed(() => {
  let list = detail.value?.deliveries || [];
  if (statusFilter.value === 'fail') {
    list = list.filter(d => {
      const st = d.status || (d.success ? 'success' : 'pending_retry');
      return st === 'pending_retry' || st === 'dead' || !d.success;
    });
  }
  return filterDeliveriesByEvent(list, eventFilter.value);
});

const columns: DataTableColumns<WebhookRow> = [
  {
    title: '名称 / URL',
    key: 'url',
    render: row =>
      h('div', [
        h('div', { style: 'font-weight:500' }, row.name || '（未命名）'),
        h(NText, { depth: 3, style: 'font-size:12px;word-break:break-all' }, { default: () => row.url })
      ])
  },
  {
    title: '事件',
    key: 'events',
    render: row =>
      h(
        NSpace,
        { size: 4 },
        {
          default: () =>
            (row.events || []).map(e =>
              h(NTag, { size: 'small', bordered: false }, { default: () => e })
            )
        }
      )
  },
  {
    title: 'Secret',
    key: 'secretHint',
    width: 100,
    render: row => h(NText, { code: true }, { default: () => row.secretHint || '—' })
  },
  {
    title: '启用',
    key: 'enabled',
    width: 140,
    render: row =>
      h(NSpace, { size: 4, align: 'center' }, {
        default: () => [
          h(NSwitch, {
            value: row.enabled,
            size: 'small',
            onUpdateValue: (v: boolean) => toggle(row, v)
          }),
          isAutoDisabledWebhook(row)
            ? h(NTag, { size: 'tiny', type: 'warning', bordered: false }, { default: () => '已自动停用' })
            : null
        ]
      })
  },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    render: row =>
      h(NSpace, { size: 4 }, {
        default: () => [
          h(
            NButton,
            { size: 'tiny', tertiary: true, onClick: () => openDetail(row.id) },
            { default: () => '投递' }
          ),
          h(
            NButton,
            { size: 'tiny', tertiary: true, onClick: () => testHook(row.id) },
            { default: () => 'Test' }
          ),
          h(
            NButton,
            { size: 'tiny', tertiary: true, type: 'error', onClick: () => removeHook(row.id) },
            { default: () => '删除' }
          )
        ]
      })
  }
];

const deliveryColumns: DataTableColumns<WebhookDelivery> = [
  {
    title: '事件',
    key: 'eventType',
    ellipsis: { tooltip: true }
  },
  {
    title: '状态',
    key: 'status',
    width: 140,
    render: row => {
      const st = row.status || (row.success ? 'success' : 'pending_retry');
      const type = st === 'dead' ? 'error' : st === 'pending_retry' ? 'warning' : 'success';
      return h(
        NTag,
        {
          size: 'small',
          type,
          bordered: false,
          style: st === 'dead' ? 'font-weight:600' : undefined
        },
        { default: () => st }
      );
    }
  },
  {
    title: 'HTTP',
    key: 'statusCode',
    width: 70,
    render: row => row.statusCode ?? '—'
  },
  {
    title: '次',
    key: 'attempt',
    width: 50
  },
  {
    title: '时间',
    key: 'createdAt',
    width: 170,
    render: row => (row.createdAt || '').replace('T', ' ').slice(0, 19) || '—'
  },
  {
    title: '操作',
    key: 'actions',
    width: 90,
    render: row => {
      if (!detail.value || !isDeliveryReplayable(row)) return '—';
      return h(
        NButton,
        {
          size: 'tiny',
          type: 'primary',
          tertiary: true,
          onClick: () => retryDelivery(detail.value!.id, row.id)
        },
        { default: () => '重试' }
      );
    }
  }
];

async function loadStats() {
  statsLoading.value = true;
  try {
    const { data, error } = await fetchWebhookStats(statsWindow.value);
    if (error) {
      window.$message?.error?.(error.message || '指标加载失败');
      stats.value = null;
      return;
    }
    stats.value = normalizeStatsPayload(data);
  } finally {
    statsLoading.value = false;
  }
}

async function load() {
  loading.value = true;
  try {
    const { data, error } = await fetchWebhooks();
    if (error) {
      window.$message?.error?.(error.message || '加载失败');
      return;
    }
    rows.value = data?.rows || [];
  } finally {
    loading.value = false;
  }
  await loadStats();
  await loadAlertSettings();
}

async function onWindowChange(w: StatWindow) {
  statsWindow.value = w;
  await loadStats();
}

async function openDeadLetter() {
  deadOpen.value = true;
  deadHookFilter.value = 'all';
  deadEventFilter.value = 'all';
  deadSelected.value = [];
  await loadDeadLetter();
}

async function loadDeadLetter() {
  deadLoading.value = true;
  try {
    const { data, error } = await fetchDeadLetter({ limit: 100 });
    if (error) {
      window.$message?.error?.(error.message || '死信箱加载失败');
      deadRows.value = [];
      return;
    }
    deadRows.value = (data?.rows || []) as DeadLetterRow[];
  } finally {
    deadLoading.value = false;
  }
}

async function retryDeadOne(row: DeadLetterRow) {
  const { data, error } = await fetchRetryWebhookDelivery(row.webhookId, row.id);
  if (error) {
    window.$message?.error?.(error.message || '重试失败');
    return;
  }
  if (data?.success) {
    window.$message?.success?.('重试成功');
  } else {
    window.$message?.warning?.(data?.error || '重试未成功');
  }
  await loadDeadLetter();
  await loadStats();
}

async function bulkRetrySelected() {
  const ids = [...deadSelected.value];
  if (!ids.length) {
    window.$message?.warning?.('请先勾选死信');
    return;
  }
  bulkRetrying.value = true;
  try {
    const { data, error } = await fetchBulkRetryDeadLetter(ids);
    if (error) {
      window.$message?.error?.(error.message || '批量重试失败');
      return;
    }
    window.$message?.success?.(
      `批量重试：成功 ${data?.succeeded ?? 0} / 失败 ${data?.failed ?? 0}`
    );
    deadSelected.value = [];
    await loadDeadLetter();
    await loadStats();
  } finally {
    bulkRetrying.value = false;
  }
}

async function openDetail(id: string) {
  detailOpen.value = true;
  detailLoading.value = true;
  statusFilter.value = 'all';
  eventFilter.value = 'all';
  try {
    const { data, error } = await fetchWebhook(id);
    if (error) {
      window.$message?.error?.(error.message || '加载失败');
      detail.value = null;
      return;
    }
    detail.value = data || null;
  } finally {
    detailLoading.value = false;
  }
}

async function retryDelivery(webhookId: string, deliveryLogId: string) {
  const { data, error } = await fetchRetryWebhookDelivery(webhookId, deliveryLogId);
  if (error) {
    window.$message?.error?.(error.message || '重试失败');
    return;
  }
  if (data?.success) {
    window.$message?.success?.('重试成功');
  } else {
    window.$message?.warning?.(data?.error || '重试未成功');
  }
  await openDetail(webhookId);
}

async function createHook() {
  if (!form.url.trim()) {
    window.$message?.warning?.('请填写 URL');
    return;
  }
  if (!form.events.length) {
    window.$message?.warning?.('请至少选择一个事件');
    return;
  }
  creating.value = true;
  try {
    const { data, error } = await fetchCreateWebhook({
      url: form.url.trim(),
      events: [...form.events],
      name: form.name.trim() || undefined
    });
    if (error) {
      window.$message?.error?.(error.message || '创建失败');
      return;
    }
    if (data?.secret) {
      oneTimeSecret.value = data.secret;
      secretModal.value = true;
    }
    form.name = '';
    form.url = '';
    form.events = [...WEBHOOK_EVENTS];
    window.$message?.success?.('已创建');
    await load();
  } finally {
    creating.value = false;
  }
}

async function toggle(row: WebhookRow, enabled: boolean) {
  const prev = row.enabled;
  row.enabled = enabled;
  const { error } = await fetchUpdateWebhook(row.id, { enabled });
  if (error) {
    row.enabled = prev;
    window.$message?.error?.(error.message || '更新失败');
  }
}

async function testHook(id: string) {
  const { data, error } = await fetchTestWebhook(id);
  if (error) {
    window.$message?.error?.(error.message || '测试失败');
    return;
  }
  if (data?.success) {
    window.$message?.success?.(`测试成功 (HTTP ${data.statusCode ?? '—'})`);
  } else {
    window.$message?.warning?.(data?.error || '测试未成功');
  }
}

async function removeHook(id: string) {
  const { error } = await fetchDeleteWebhook(id);
  if (error) {
    window.$message?.error?.(error.message || '删除失败');
    return;
  }
  window.$message?.success?.('已删除');
  await load();
}


const deadColumns: DataTableColumns<DeadLetterRow> = [
  {
    type: 'selection'
  },
  {
    title: '钩子',
    key: 'webhookName',
    ellipsis: { tooltip: true },
    render: row => row.webhookName || row.webhookUrl || row.webhookId.slice(0, 8)
  },
  {
    title: '事件',
    key: 'eventType',
    ellipsis: { tooltip: true }
  },
  {
    title: 'HTTP',
    key: 'statusCode',
    width: 70,
    render: row => row.statusCode ?? '—'
  },
  {
    title: '错误',
    key: 'error',
    ellipsis: { tooltip: true },
    render: row => row.error || '—'
  },
  {
    title: '时间',
    key: 'createdAt',
    width: 170,
    render: row => (row.createdAt || '').replace('T', ' ').slice(0, 19) || '—'
  },
  {
    title: '状态',
    key: 'autoDisabled',
    width: 110,
    render: row =>
      row.autoDisabled || row.pausedReason === 'auto_dead_letter_alert'
        ? h(NTag, { size: 'tiny', type: 'warning', bordered: false }, { default: () => '已自动停用' })
        : '—'
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    render: row =>
      h(NSpace, { size: 4 }, {
        default: () => [
          h(
            NButton,
            {
              size: 'tiny',
              type: 'primary',
              tertiary: true,
              onClick: () => retryDeadOne(row)
            },
            { default: () => '重试' }
          ),
          row.autoDisabled || row.pausedReason === 'auto_dead_letter_alert'
            ? h(
                NButton,
                {
                  size: 'tiny',
                  tertiary: true,
                  onClick: () => reenableAutoDisabled(row.webhookId)
                },
                { default: () => '启用' }
              )
            : null
        ]
      })
  }
];

onMounted(load);

</script>

<template>
  <div class="p-4">
    <NCard title="出站 Webhooks" :bordered="false">
      <template #header-extra>
        <NSpace align="center">
          <NText depth="3">订阅 Issue/评论事件，HMAC 签名投递到你的 URL</NText>
          <NButton size="small" tertiary type="error" @click="openDeadLetter">死信箱</NButton>
        </NSpace>
      </template>

      <NCard size="small" title="投递指标" class="mb-4" :loading="statsLoading">
        <NSpace align="center" justify="space-between">
          <NSpace align="center">
            <NText depth="3">时间窗</NText>
            <NRadioGroup
              :value="statsWindow"
              size="small"
              @update:value="(v: StatWindow) => onWindowChange(v)"
            >
              <NRadioButton v-for="opt in windowOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </NRadioButton>
            </NRadioGroup>
          </NSpace>
          <NSpace :size="24">
            <div>
              <NText depth="3" style="font-size:12px">成功率</NText>
              <div style="font-size:22px;font-weight:600">{{ successRateLabel }}</div>
            </div>
            <div style="cursor:pointer" @click="openDeadLetter">
              <NText depth="3" style="font-size:12px">死信</NText>
              <div style="font-size:22px;font-weight:600;color:#ef4444">{{ deadCountLabel }}</div>
            </div>
            <div>
              <NText depth="3" style="font-size:12px">成功 / 尝试</NText>
              <div style="font-size:16px;font-weight:500">
                {{ stats?.totals.success ?? 0 }} / {{ stats?.totals.attempts ?? 0 }}
              </div>
            </div>
            <div v-if="stats?.totals.latencyMs">
              <NText depth="3" style="font-size:12px">延迟 p50 / p95</NText>
              <div style="font-size:16px;font-weight:500">
                {{ stats.totals.latencyMs.p50 }}ms / {{ stats.totals.latencyMs.p95 }}ms
              </div>
            </div>
          </NSpace>
        </NSpace>
      </NCard>

      <NCard size="small" class="mb-4">
        <template #header>
          <NSpace align="center" justify="space-between" style="width:100%">
            <span style="font-weight:500;cursor:pointer" @click="alertOpen = !alertOpen">死信告警</span>
            <NText depth="3" style="font-size:12px">{{ alertPendingLabel }}</NText>
          </NSpace>
        </template>
        <div v-show="alertOpen">
          <NSpace vertical>
            <NSpace align="center">
              <NText>总开关（opt-in）</NText>
              <NSwitch v-model:value="alertForm.enabled" size="small" />
              <NText depth="3">关闭时永不告警</NText>
            </NSpace>
            <NSpace align="center">
              <NText>窗口小时</NText>
              <NInputNumber v-model:value="alertForm.windowHours" :min="1" :max="168" size="small" style="width:120px" />
              <NText>死信阈值</NText>
              <NInputNumber v-model:value="alertForm.deadThreshold" :min="1" size="small" style="width:120px" />
            </NSpace>
            <NSpace align="center">
              <NText>连续死信阈值（可选）</NText>
              <NInputNumber
                v-model:value="alertForm.consecutiveDeadThreshold"
                :min="1"
                clearable
                size="small"
                style="width:120px"
                placeholder="关闭"
              />
              <NText>硬顶自动停用</NText>
              <NSwitch v-model:value="alertForm.autoDisable" size="small" />
            </NSpace>
            <NSpace align="center">
              <NText>muteUntil</NText>
              <NInput v-model:value="muteUntilInput" placeholder="ISO 时间，可空" size="small" style="width:280px" />
              <NButton size="small" tertiary @click="muteAlertsNow">静音</NButton>
              <NButton size="small" tertiary @click="unmuteAlertsNow">取消静音</NButton>
            </NSpace>
            <NButton type="primary" size="small" :loading="alertSaving" @click="saveAlertSettings">保存告警设置</NButton>
          </NSpace>
        </div>
      </NCard>

      <NCard size="small" title="新建" class="mb-4">
        <NSpace vertical>
          <NInput v-model:value="form.name" placeholder="名称（可选）" />
          <NInput v-model:value="form.url" placeholder="https://example.com/hooks/opentask" />
          <NSpace>
            <NButton size="small" tertiary @click="useIntegrationPreset">集成常用</NButton>
            <NButton size="small" tertiary @click="clearPreset">清除预设</NButton>
          </NSpace>
          <NCheckboxGroup v-model:value="form.events">
            <NSpace>
              <NCheckbox v-for="opt in eventOptions" :key="opt.value" :value="opt.value" :label="opt.label" />
            </NSpace>
          </NCheckboxGroup>
          <NButton type="primary" :loading="creating" @click="createHook">创建</NButton>
        </NSpace>
      </NCard>

      <NDataTable :columns="columns" :data="rows" :loading="loading" :bordered="false" size="small" />
      <div v-if="!loading && !rows.length" class="py-8 text-center opacity-60">
        尚无 Webhook。创建一个以接收 issue.created 等事件。
      </div>
    </NCard>

    <NModal v-model:show="secretModal" preset="card" title="请保存 Signing Secret" style="width: 520px">
      <NText depth="3">此密钥仅展示一次，用于验证 X-OpenTask-Signature。</NText>
      <pre class="mt-3 overflow-auto rounded bg-gray-100 p-3 text-sm dark:bg-gray-800">{{ oneTimeSecret }}</pre>
      <template #footer>
        <NButton type="primary" @click="secretModal = false">我已保存</NButton>
      </template>
    </NModal>

    <NModal
      v-model:show="detailOpen"
      preset="card"
      :title="detail?.name || detail?.url || '投递记录'"
      style="width: 820px"
    >
      <NSpace vertical>
        <NSpace align="center">
          <NRadioGroup v-model:value="statusFilter" size="small">
            <NRadioButton value="all">全部</NRadioButton>
            <NRadioButton value="fail">失败/死信</NRadioButton>
          </NRadioGroup>
          <NSelect
            v-model:value="eventFilter"
            :options="eventFilterOptions"
            size="small"
            style="width: 220px"
            placeholder="按事件过滤"
          />
        </NSpace>
        <NDataTable
          :columns="deliveryColumns"
          :data="filteredDeliveries"
          :loading="detailLoading"
          :bordered="false"
          size="small"
          :row-class-name="(row: WebhookDelivery) => ((row.status || '') === 'dead' ? 'e44-dead-row' : '')"
        />
      </NSpace>
    </NModal>

    <NModal
      v-model:show="deadOpen"
      preset="card"
      title="死信箱"
      style="width: 920px"
    >
      <NSpace vertical>
        <NSpace align="center">
          <NSelect
            v-model:value="deadHookFilter"
            :options="hookFilterOptions"
            size="small"
            style="width: 220px"
            placeholder="按钩子过滤"
          />
          <NSelect
            v-model:value="deadEventFilter"
            :options="eventFilterOptions"
            size="small"
            style="width: 220px"
            placeholder="按事件过滤"
          />
          <NButton
            size="small"
            type="primary"
            :loading="bulkRetrying"
            :disabled="!deadSelected.length"
            @click="bulkRetrySelected"
          >
            批量重试所选 ({{ deadSelected.length }})
          </NButton>
          <NButton size="small" tertiary :loading="deadLoading" @click="loadDeadLetter">刷新</NButton>
        </NSpace>
        <NDataTable
          v-model:checked-row-keys="deadSelected"
          :columns="deadColumns"
          :data="filteredDeadRows"
          :loading="deadLoading"
          :bordered="false"
          size="small"
          :row-key="(row: DeadLetterRow) => row.id"
          :row-class-name="() => 'e44-dead-row'"
        />
        <div v-if="!deadLoading && !filteredDeadRows.length" class="py-6 text-center opacity-60">
          暂无死信。
        </div>
      </NSpace>
    </NModal>
  </div>
</template>

<style scoped>
:deep(.e44-dead-row td) {
  background: rgba(239, 68, 68, 0.08);
}
</style>
