<script setup lang="ts">
import { computed, h, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { type DataTableColumns, NButton, NTag } from 'naive-ui';
import {
  type CustomerRequestRow,
  type CustomerRow,
  fetchCreateCustomerRequest,
  fetchCustomer,
  fetchCustomerRequests,
  fetchUpdateCustomer
} from '@/service/api';

defineOptions({ name: 'CustomerDetailPage' });

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const saving = ref(false);
const customer = ref<CustomerRow | null>(null);
const requests = ref<CustomerRequestRow[]>([]);
const createOpen = ref(false);
const creating = ref(false);
const form = reactive({ name: '', domains: '', externalUrl: '', notes: '' });
const reqForm = reactive({
  title: '',
  body: '',
  priority: null as null | 'low' | 'medium' | 'high' | 'urgent',
  createAndLinkIssue: true
});

const customerId = computed(() => String(route.query.id || ''));

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
    title: '状态',
    key: 'status',
    width: 100,
    render: row => h(NTag, { size: 'small' }, { default: () => statusLabel[row.status] || row.status })
  },
  {
    title: '关联 Issue',
    key: 'issueCount',
    width: 100,
    render: row => String(row.issueCount ?? 0)
  }
];

async function load() {
  if (!customerId.value) return;
  loading.value = true;
  try {
    const [{ data: c, error: ce }, { data: r, error: re }] = await Promise.all([
      fetchCustomer(customerId.value),
      fetchCustomerRequests({ customerId: customerId.value })
    ]);
    if (ce || !c) {
      window.$message?.error(ce?.message || '加载客户失败');
      return;
    }
    customer.value = c;
    form.name = c.name;
    form.domains = (c.domains || []).join(', ');
    form.externalUrl = c.externalUrl || '';
    form.notes = c.notes || '';
    if (re || !r) {
      requests.value = [];
    } else {
      requests.value = r.rows || [];
    }
  } finally {
    loading.value = false;
  }
}

async function onSave() {
  if (!customerId.value) return;
  saving.value = true;
  try {
    const domains = form.domains
      .split(/[,，\s]+/)
      .map(s => s.trim())
      .filter(Boolean);
    const { error } = await fetchUpdateCustomer(customerId.value, {
      name: form.name.trim(),
      domains,
      setDomains: true,
      externalUrl: form.externalUrl.trim() || null,
      clearExternalUrl: !form.externalUrl.trim(),
      notes: form.notes.trim() || null,
      clearNotes: !form.notes.trim()
    });
    if (error) {
      window.$message?.error(error.message || '保存失败');
      return;
    }
    window.$message?.success('已保存');
    await load();
  } finally {
    saving.value = false;
  }
}

async function onCreateRequest() {
  if (!customerId.value || !reqForm.title.trim()) {
    window.$message?.warning('请输入需求标题');
    return;
  }
  creating.value = true;
  try {
    const { error } = await fetchCreateCustomerRequest({
      customerId: customerId.value,
      title: reqForm.title.trim(),
      body: reqForm.body.trim() || undefined,
      priority: reqForm.priority,
      createAndLinkIssue: reqForm.createAndLinkIssue
    });
    if (error) {
      window.$message?.error(error.message || '创建失败');
      return;
    }
    window.$message?.success('已创建需求');
    createOpen.value = false;
    reqForm.title = '';
    reqForm.body = '';
    reqForm.priority = null;
    reqForm.createAndLinkIssue = true;
    await load();
  } finally {
    creating.value = false;
  }
}

watch(customerId, load, { immediate: false });
onMounted(load);
</script>

<template>
  <div class="h-full flex-col gap-16px overflow-auto p-16px">
    <div class="flex items-center gap-12px">
      <NButton quaternary @click="router.push({ name: 'customers' })">← 客户列表</NButton>
      <h2 class="text-18px font-600">{{ customer?.name || '客户详情' }}</h2>
    </div>

    <NSpin :show="loading">
      <NCard title="基本信息" :bordered="false">
        <NForm label-placement="left" label-width="80" class="max-w-640px">
          <NFormItem label="名称">
            <NInput v-model:value="form.name" />
          </NFormItem>
          <NFormItem label="域名">
            <NInput v-model:value="form.domains" placeholder="逗号分隔" />
          </NFormItem>
          <NFormItem label="外链">
            <NInput v-model:value="form.externalUrl" />
          </NFormItem>
          <NFormItem label="备注">
            <NInput v-model:value="form.notes" type="textarea" :rows="3" />
          </NFormItem>
          <NButton type="primary" :loading="saving" @click="onSave">保存</NButton>
        </NForm>
      </NCard>

      <NCard title="客户需求" :bordered="false" class="mt-16px">
        <template #header-extra>
          <NButton type="primary" size="small" @click="createOpen = true">新建需求</NButton>
        </template>
        <NEmpty v-if="!requests.length" description="暂无客户需求。可新建并可选创建关联 Issue。">
          <template #extra>
            <NButton type="primary" @click="createOpen = true">新建需求</NButton>
          </template>
        </NEmpty>
        <NDataTable v-else :columns="columns" :data="requests" :bordered="false" />
      </NCard>
    </NSpin>

    <NModal v-model:show="createOpen" preset="card" title="新建客户需求" class="w-520px">
      <NForm label-placement="left" label-width="110">
        <NFormItem label="标题" required>
          <NInput v-model:value="reqForm.title" />
        </NFormItem>
        <NFormItem label="描述">
          <NInput v-model:value="reqForm.body" type="textarea" :rows="3" />
        </NFormItem>
        <NFormItem label="优先级">
          <NSelect
            v-model:value="reqForm.priority"
            clearable
            :options="[
              { label: '低', value: 'low' },
              { label: '中', value: 'medium' },
              { label: '高', value: 'high' },
              { label: '紧急', value: 'urgent' }
            ]"
          />
        </NFormItem>
        <NFormItem label="创建并关联 Issue">
          <NSwitch v-model:value="reqForm.createAndLinkIssue" />
        </NFormItem>
      </NForm>
      <template #footer>
        <div class="flex justify-end gap-8px">
          <NButton @click="createOpen = false">取消</NButton>
          <NButton type="primary" :loading="creating" @click="onCreateRequest">创建</NButton>
        </div>
      </template>
    </NModal>
  </div>
</template>
