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
  type WebhookDelivery,
  type WebhookRow,
  WEBHOOK_EVENTS,
  WEBHOOK_EVENT_LABELS,
  applyIntegrationPreset,
  clearIntegrationPreset,
  fetchCreateWebhook,
  fetchDeleteWebhook,
  fetchRetryWebhookDelivery,
  fetchTestWebhook,
  fetchUpdateWebhook,
  fetchWebhook,
  fetchWebhooks,
  filterDeliveriesByEvent,
  isDeliveryReplayable
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

onMounted(load);
</script>

<template>
  <div class="p-4">
    <NCard title="出站 Webhooks" :bordered="false">
      <template #header-extra>
        <NText depth="3">订阅 Issue/评论事件，HMAC 签名投递到你的 URL</NText>
      </template>

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
  </div>
</template>

<style scoped>
:deep(.e44-dead-row td) {
  background: rgba(239, 68, 68, 0.08);
}
</style>
