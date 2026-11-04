<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  type CustomerRequestRow,
  fetchCustomerRequest,
  fetchLinkRequestIssue,
  fetchUnlinkRequestIssue,
  fetchUpdateCustomerRequest
} from '@/service/api';

defineOptions({ name: 'RequestDetailPage' });

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const saving = ref(false);
const linking = ref(false);
const row = ref<CustomerRequestRow | null>(null);
const linkIssueId = ref('');
const form = reactive({
  title: '',
  body: '',
  status: 'open' as 'open' | 'completed' | 'canceled',
  priority: null as null | 'low' | 'medium' | 'high' | 'urgent'
});

const requestId = computed(() => String(route.query.id || ''));

async function load() {
  if (!requestId.value) return;
  loading.value = true;
  try {
    const { data, error } = await fetchCustomerRequest(requestId.value);
    if (error || !data) {
      window.$message?.error(error?.message || '加载失败');
      return;
    }
    row.value = data;
    form.title = data.title;
    form.body = data.body || '';
    form.status = data.status;
    form.priority = data.priority || null;
  } finally {
    loading.value = false;
  }
}

async function onSave() {
  if (!requestId.value) return;
  saving.value = true;
  try {
    const { error } = await fetchUpdateCustomerRequest(requestId.value, {
      title: form.title.trim(),
      body: form.body,
      clearBody: !form.body.trim(),
      status: form.status,
      priority: form.priority,
      clearPriority: !form.priority
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

async function onLink() {
  const issueId = linkIssueId.value.trim();
  if (!issueId || !requestId.value) return;
  linking.value = true;
  try {
    const { error } = await fetchLinkRequestIssue(requestId.value, issueId);
    if (error) {
      window.$message?.error(error.message || '关联失败');
      return;
    }
    window.$message?.success('已关联');
    linkIssueId.value = '';
    await load();
  } finally {
    linking.value = false;
  }
}

async function onUnlink(issueId: string) {
  if (!requestId.value) return;
  const { error } = await fetchUnlinkRequestIssue(requestId.value, issueId);
  if (error) {
    window.$message?.error(error.message || '解除失败');
    return;
  }
  window.$message?.success('已解除');
  await load();
}

watch(requestId, load);
onMounted(load);
</script>

<template>
  <div class="h-full flex-col gap-16px overflow-auto p-16px">
    <div class="flex items-center gap-12px">
      <NButton quaternary @click="router.push({ name: 'requests' })">← 需求列表</NButton>
      <h2 class="text-18px font-600">{{ row?.title || '需求详情' }}</h2>
    </div>

    <NSpin :show="loading">
      <NCard title="基本信息" :bordered="false">
        <NForm label-placement="left" label-width="80" class="max-w-640px">
          <NFormItem label="客户">
            <NButton
              text
              type="primary"
              @click="router.push({ name: 'customers_detail', query: { id: row?.customerId } })"
            >
              {{ row?.customerName || row?.customerId }}
            </NButton>
          </NFormItem>
          <NFormItem label="标题">
            <NInput v-model:value="form.title" />
          </NFormItem>
          <NFormItem label="描述">
            <NInput v-model:value="form.body" type="textarea" :rows="4" />
          </NFormItem>
          <NFormItem label="状态">
            <NSelect
              v-model:value="form.status"
              :options="[
                { label: '开放', value: 'open' },
                { label: '已完成', value: 'completed' },
                { label: '已取消', value: 'canceled' }
              ]"
            />
          </NFormItem>
          <NFormItem label="优先级">
            <NSelect
              v-model:value="form.priority"
              clearable
              :options="[
                { label: '低', value: 'low' },
                { label: '中', value: 'medium' },
                { label: '高', value: 'high' },
                { label: '紧急', value: 'urgent' }
              ]"
            />
          </NFormItem>
          <NButton type="primary" :loading="saving" @click="onSave">保存</NButton>
        </NForm>
      </NCard>

      <NCard title="关联 Issue" :bordered="false" class="mt-16px">
        <div class="mb-12px flex gap-8px">
          <NInput v-model:value="linkIssueId" placeholder="Issue ID" class="max-w-360px" />
          <NButton type="primary" :loading="linking" @click="onLink">挂载</NButton>
        </div>
        <NEmpty v-if="!(row?.issues || []).length" description="尚未关联 Issue" />
        <NSpace v-else vertical>
          <div v-for="iss in row?.issues || []" :key="iss.id" class="flex items-center gap-8px">
            <NButton text type="primary" @click="router.push({ name: 'issue_detail', query: { id: iss.id } })">
              {{ iss.issueCode }} · {{ iss.title }}
            </NButton>
            <NTag size="small">{{ iss.status }}</NTag>
            <NButton size="tiny" secondary type="error" @click="onUnlink(iss.id)">解挂</NButton>
          </div>
        </NSpace>
      </NCard>
    </NSpin>
  </div>
</template>
