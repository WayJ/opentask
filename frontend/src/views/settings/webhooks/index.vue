<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue';
import {
  type DataTableColumns,
  NButton,
  NCard,
  NCheckbox,
  NCheckboxGroup,
  NDataTable,
  NInput,
  NModal,
  NSpace,
  NSwitch,
  NTag,
  NText
} from 'naive-ui';
import {
  type WebhookRow,
  WEBHOOK_EVENTS,
  fetchCreateWebhook,
  fetchDeleteWebhook,
  fetchTestWebhook,
  fetchUpdateWebhook,
  fetchWebhooks
} from '@/service/api/webhooks';

defineOptions({ name: 'SettingsWebhooksPage' });

const loading = ref(false);
const rows = ref<WebhookRow[]>([]);
const creating = ref(false);
const secretModal = ref(false);
const oneTimeSecret = ref('');
const form = reactive({
  name: '',
  url: '',
  events: [...WEBHOOK_EVENTS] as string[]
});

const eventOptions = WEBHOOK_EVENTS.map(e => ({ label: e, value: e }));

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
    width: 160,
    render: row =>
      h(NSpace, { size: 4 }, {
        default: () => [
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
  </div>
</template>
