<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { type DataTableColumns, NButton, NTag } from 'naive-ui';
import { type CustomerRequestRow, type CustomerRequestStatus, fetchCustomerRequests } from '@/service/api';

defineOptions({ name: 'RequestsPage' });

const router = useRouter();
const loading = ref(false);
const rows = ref<CustomerRequestRow[]>([]);
const statusFilter = ref<CustomerRequestStatus | null>(null);

const empty = computed(() => !loading.value && rows.value.length === 0);

const statusLabel: Record<string, string> = {
  open: '开放',
  completed: '已完成',
  canceled: '已取消'
};

const columns: DataTableColumns<CustomerRequestRow> = [
  {
    title: '标题',
    key: 'title',
    render: row =>
      h(
        NButton,
        { text: true, type: 'primary', onClick: () => router.push({ name: 'requests_detail', query: { id: row.id } }) },
        { default: () => row.title }
      )
  },
  {
    title: '客户',
    key: 'customerName',
    width: 160,
    render: row =>
      h(
        NButton,
        {
          text: true,
          onClick: () => router.push({ name: 'customers_detail', query: { id: row.customerId } })
        },
        { default: () => row.customerName || row.customerId.slice(0, 8) }
      )
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: row => h(NTag, { size: 'small' }, { default: () => statusLabel[row.status] || row.status })
  },
  {
    title: 'Issue',
    key: 'issueCount',
    width: 80,
    render: row => String(row.issueCount ?? 0)
  }
];

async function load() {
  loading.value = true;
  try {
    const { data, error } = await fetchCustomerRequests({
      status: statusFilter.value || undefined
    });
    if (error || !data) {
      window.$message?.error(error?.message || '加载需求失败');
      return;
    }
    rows.value = data.rows || [];
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="h-full flex-col gap-16px overflow-hidden p-16px">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-18px font-600">客户需求</h2>
        <p class="mt-4px text-13px text-gray-500">跨客户的需求列表；可关联 Issue</p>
      </div>
      <div class="flex items-center gap-8px">
        <NSelect
          v-model:value="statusFilter"
          clearable
          placeholder="状态"
          class="w-140px"
          :options="[
            { label: '开放', value: 'open' },
            { label: '已完成', value: 'completed' },
            { label: '已取消', value: 'canceled' }
          ]"
          @update:value="load"
        />
        <NButton quaternary @click="router.push({ name: 'customers' })">客户</NButton>
      </div>
    </div>

    <NCard :bordered="false" class="flex-1 overflow-hidden" content-style="padding: 0; height: 100%">
      <NEmpty v-if="empty" class="py-48px" description="暂无客户需求。请先在客户详情中创建。">
        <template #extra>
          <NButton type="primary" @click="router.push({ name: 'customers' })">去客户列表</NButton>
        </template>
      </NEmpty>
      <NDataTable
        v-else
        :loading="loading"
        :columns="columns"
        :data="rows"
        :bordered="false"
        flex-height
        class="h-full"
      />
    </NCard>
  </div>
</template>
