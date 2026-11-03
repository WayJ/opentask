<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { type InboxNotification, fetchInboxList, fetchMarkAllInboxRead, fetchMarkInboxRead } from '@/service/api';

defineOptions({ name: 'InboxPage' });

const router = useRouter();
const loading = ref(false);
const unreadOnly = ref(false);
const rows = ref<InboxNotification[]>([]);
const unreadCount = ref(0);
const total = ref(0);

const typeLabel: Record<string, string> = {
  assigned: '指派',
  commented: '评论',
  mentioned: '提及'
};

const empty = computed(() => !loading.value && rows.value.length === 0);

async function load() {
  loading.value = true;
  try {
    const { data, error } = await fetchInboxList({ unreadOnly: unreadOnly.value, page: 1, pageSize: 50 });
    if (error || !data) {
      window.$message?.error(error?.message || '加载 Inbox 失败');
      return;
    }
    rows.value = data.rows || [];
    unreadCount.value = data.unreadCount ?? 0;
    total.value = data.total ?? 0;
  } finally {
    loading.value = false;
  }
}

async function onClickRow(row: InboxNotification) {
  if (!row.readAt) {
    await fetchMarkInboxRead(row.id);
  }
  if (row.resourceType === 'issue' && row.resourceId) {
    router.push({ name: 'issue_detail', query: { id: row.resourceId } });
  }
}

async function markAll() {
  const { error } = await fetchMarkAllInboxRead();
  if (error) {
    window.$message?.error(error.message || '操作失败');
    return;
  }
  window.$message?.success('已全部标记已读');
  await load();
}

onMounted(load);
</script>

<template>
  <div class="h-full flex-col gap-16px overflow-hidden p-16px">
    <div class="flex-y-center justify-between">
      <div class="flex-y-center gap-12px">
        <h2 class="text-18px font-medium">Inbox</h2>
        <NTag v-if="unreadCount > 0" type="info" size="small" round>{{ unreadCount }} 未读</NTag>
      </div>
      <div class="flex-y-center gap-8px">
        <NCheckbox v-model:checked="unreadOnly" @update:checked="load">仅未读</NCheckbox>
        <NButton size="small" @click="load">刷新</NButton>
        <NButton size="small" type="primary" secondary :disabled="unreadCount === 0" @click="markAll">全部已读</NButton>
      </div>
    </div>

    <NSpin :show="loading" class="min-h-0 flex-1">
      <NEmpty v-if="empty" description="暂无通知" class="py-48px" />
      <NList v-else hoverable clickable>
        <NListItem v-for="row in rows" :key="row.id" class="cursor-pointer" @click="onClickRow(row)">
          <div class="w-full flex-y-center justify-between gap-12px">
            <div class="min-w-0 flex-1">
              <div class="flex-y-center gap-8px">
                <NBadge :dot="!row.readAt" type="info">
                  <NTag size="tiny" :bordered="false">{{ typeLabel[row.type] || row.type }}</NTag>
                </NBadge>
                <span class="truncate font-medium" :class="{ 'opacity-60': !!row.readAt }">{{ row.title }}</span>
              </div>
              <div v-if="row.body" class="mt-4px truncate text-13px text-gray-500 dark:text-gray-400">
                {{ row.body }}
              </div>
            </div>
            <span class="shrink-0 text-12px opacity-50">{{ row.createdAt }}</span>
          </div>
        </NListItem>
      </NList>
    </NSpin>
  </div>
</template>
