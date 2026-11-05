<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { type DataTableColumns, NButton, NTag } from 'naive-ui';
import { type CustomerRow, fetchCreateCustomer, fetchCustomers, fetchDeleteCustomer } from '@/service/api';

defineOptions({ name: 'CustomersPage' });

const router = useRouter();
const loading = ref(false);
const rows = ref<CustomerRow[]>([]);
const createOpen = ref(false);
const creating = ref(false);
const form = reactive({
  name: '',
  domains: '',
  externalUrl: '',
  notes: ''
});

const empty = computed(() => !loading.value && rows.value.length === 0);

const columns: DataTableColumns<CustomerRow> = [
  {
    title: '客户',
    key: 'name',
    render: row =>
      h(NButton, { text: true, type: 'primary', onClick: () => goDetail(row.id) }, { default: () => row.name })
  },
  {
    title: '域名',
    key: 'domains',
    render: row =>
      h(
        'div',
        { class: 'flex flex-wrap gap-4px' },
        (row.domains || []).map(d => h(NTag, { size: 'small', bordered: false }, { default: () => d }))
      )
  },
  {
    title: '需求数',
    key: 'requestCount',
    width: 90,
    render: row => String(row.requestCount ?? 0)
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
  router.push({ name: 'customers_detail', query: { id } });
}

async function load() {
  loading.value = true;
  try {
    const { data, error } = await fetchCustomers();
    if (error || !data) {
      window.$message?.error(error?.message || '加载客户失败');
      return;
    }
    rows.value = data.rows || [];
  } finally {
    loading.value = false;
  }
}

async function onCreate() {
  const name = form.name.trim();
  if (!name) {
    window.$message?.warning('请输入客户名称');
    return;
  }
  creating.value = true;
  try {
    const domains = form.domains
      .split(/[,，\s]+/)
      .map(s => s.trim())
      .filter(Boolean);
    const { error } = await fetchCreateCustomer({
      name,
      domains: domains.length ? domains : undefined,
      externalUrl: form.externalUrl.trim() || undefined,
      notes: form.notes.trim() || undefined
    });
    if (error) {
      window.$message?.error(error.message || '创建失败');
      return;
    }
    window.$message?.success('已创建客户');
    createOpen.value = false;
    form.name = '';
    form.domains = '';
    form.externalUrl = '';
    form.notes = '';
    await load();
  } finally {
    creating.value = false;
  }
}

async function onDelete(row: CustomerRow) {
  const { error } = await fetchDeleteCustomer(row.id);
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
        <h2 class="text-18px font-600">客户</h2>
        <p class="mt-4px text-13px text-gray-500">工作区客户账户；可关联客户需求与 Issue</p>
      </div>
      <div class="flex gap-8px">
        <NButton quaternary @click="$router.push({ name: 'requests' })">全部需求</NButton>
        <NButton type="primary" @click="createOpen = true">新建客户</NButton>
      </div>
    </div>

    <NCard :bordered="false" class="flex-1 overflow-hidden" content-style="padding: 0; height: 100%">
      <NEmpty v-if="empty" class="py-48px" description="暂无客户。创建客户后可录入客户需求并关联 Issue。">
        <template #extra>
          <NButton type="primary" @click="createOpen = true">新建客户</NButton>
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

    <NModal v-model:show="createOpen" preset="card" title="新建客户" class="w-480px">
      <NForm label-placement="left" label-width="80">
        <NFormItem label="名称" required>
          <NInput v-model:value="form.name" maxlength="200" placeholder="例如：Acme Corp" />
        </NFormItem>
        <NFormItem label="域名">
          <NInput v-model:value="form.domains" placeholder="逗号分隔，如 acme.com" />
        </NFormItem>
        <NFormItem label="外链">
          <NInput v-model:value="form.externalUrl" placeholder="https://" />
        </NFormItem>
        <NFormItem label="备注">
          <NInput v-model:value="form.notes" type="textarea" :rows="3" />
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
