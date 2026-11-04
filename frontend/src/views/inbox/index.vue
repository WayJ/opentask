<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import type { DropdownOption } from 'naive-ui';
import {
  type InboxNotification,
  fetchInboxList,
  fetchMarkAllInboxRead,
  fetchMarkInboxRead,
  fetchSnoozeInbox,
  fetchUnsnoozeInbox
} from '@/service/api';
import { useAuthStore } from '@/store/modules/auth';
import { subscribeWorkspaceRealtime } from '@/composables/use-workspace-realtime';

defineOptions({ name: 'InboxPage' });

const router = useRouter();
const authStore = useAuthStore();
let unsubRt: (() => void) | null = null;
const loading = ref(false);
const unreadOnly = ref(false);
const includeSnoozed = ref(false);
const rows = ref<InboxNotification[]>([]);
const unreadCount = ref(0);
const total = ref(0);

const typeLabel: Record<string, string> = {
  assigned: '指派',
  commented: '评论',
  mentioned: '提及',
  project_health: '项目健康',
  status_changed: '状态',
  subscribed_update: '关注更新',
  due_date_changed: '截止日期',
  due_reminder: '到期提醒',
  due_reminder_digest: '到期摘要'
};

const empty = computed(() => !loading.value && rows.value.length === 0);

function startOfLocalDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 9, 0, 0, 0);
}

function snoozePresets(): { key: string; label: string; until: Date }[] {
  const now = new Date();
  const in1h = new Date(now.getTime() + 60 * 60 * 1000);
  const in3h = new Date(now.getTime() + 3 * 60 * 60 * 1000);
  const tomorrow = startOfLocalDay(new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1));
  const day = now.getDay(); // 0 Sun
  let daysUntilMon = 8 - day;
  if (day === 0) daysUntilMon = 1;
  else if (day === 1) daysUntilMon = 7;
  const nextMon = startOfLocalDay(new Date(now.getFullYear(), now.getMonth(), now.getDate() + daysUntilMon));
  return [
    { key: '1h', label: '1 小时后', until: in1h },
    { key: '3h', label: '3 小时后', until: in3h },
    { key: 'tomorrow', label: '明天 9:00', until: tomorrow },
    { key: 'next_mon', label: '下周一 9:00', until: nextMon }
  ];
}

function snoozeOptions(row: InboxNotification): DropdownOption[] {
  const opts: DropdownOption[] = snoozePresets().map(p => ({
    label: p.label,
    key: p.key
  }));
  if (row.snoozedUntil) {
    opts.push({ type: 'divider', key: 'd1' });
    opts.push({ label: '取消延后', key: 'unsnooze' });
  }
  return opts;
}

async function load() {
  loading.value = true;
  try {
    const { data, error } = await fetchInboxList({
      unreadOnly: unreadOnly.value,
      includeSnoozed: includeSnoozed.value,
      page: 1,
      pageSize: 50
    });
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
  } else if (row.resourceType === 'project' && row.resourceId) {
    router.push({ path: '/workflow/project-detail', query: { id: row.resourceId } });
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

async function onSnoozeSelect(key: string | number, row: InboxNotification) {
  const k = String(key);
  if (k === 'unsnooze') {
    const { error } = await fetchUnsnoozeInbox(row.id);
    if (error) {
      window.$message?.error(error.message || '取消延后失败');
      return;
    }
    window.$message?.success('已取消延后');
    await load();
    return;
  }
  const preset = snoozePresets().find(p => p.key === k);
  if (!preset) return;
  const { error } = await fetchSnoozeInbox(row.id, preset.until.toISOString());
  if (error) {
    window.$message?.error(error.message || '延后失败');
    return;
  }
  window.$message?.success(`已延后至 ${preset.label}`);
  await load();
}

onMounted(() => {
  load();
  unsubRt = subscribeWorkspaceRealtime(ev => {
    if (ev.type !== 'inbox.created') return;
    const me = String(authStore.userInfo.userId || '');
    const recipient = String(ev.payload?.recipient_user_id || '');
    if (me && recipient && recipient !== me) return;
    load();
  });
});
onUnmounted(() => {
  unsubRt?.();
  unsubRt = null;
});
</script>

<template>
  <div class="h-full flex-col gap-12px overflow-hidden">
    <div class="flex-y-center justify-between">
      <div class="flex-y-center gap-12px">
        <div>
          <h2 class="text-18px font-medium">Inbox</h2>
          <p class="mt-2px text-12px opacity-60">个人通知收件箱（与「分诊」入站队列分开）</p>
        </div>
        <NTag v-if="unreadCount > 0" type="info" size="small" round>{{ unreadCount }} 未读</NTag>
      </div>
      <div class="flex-y-center gap-8px">
        <NCheckbox v-model:checked="unreadOnly" @update:checked="load">仅未读</NCheckbox>
        <NCheckbox v-model:checked="includeSnoozed" @update:checked="load">显示已延后</NCheckbox>
        <NButton size="small" @click="load">刷新</NButton>
        <NButton size="small" type="primary" secondary :disabled="unreadCount === 0" @click="markAll">全部已读</NButton>
      </div>
    </div>

    <NSpin :show="loading" class="min-h-0 flex-1">
      <NEmpty v-if="empty" description="暂无通知（个人收件箱，与分诊队列无关）" class="py-48px" />
      <NList v-else hoverable clickable>
        <NListItem v-for="row in rows" :key="row.id" class="cursor-pointer" @click="onClickRow(row)">
          <div class="w-full flex-y-center justify-between gap-12px">
            <div class="min-w-0 flex-1">
              <div class="flex-y-center gap-8px">
                <NBadge :dot="!row.readAt" type="info">
                  <NTag size="tiny" :bordered="false">{{ typeLabel[row.type] || row.type }}</NTag>
                </NBadge>
                <span class="truncate font-medium" :class="{ 'opacity-60': !!row.readAt }">{{ row.title }}</span>
                <NTag v-if="row.snoozedUntil" size="tiny" type="warning" :bordered="false">已延后</NTag>
              </div>
              <div v-if="row.body" class="mt-4px truncate text-13px opacity-60">
                {{ row.body }}
              </div>
            </div>
            <div class="flex-y-center shrink-0 gap-8px" @click.stop>
              <NDropdown
                trigger="click"
                :options="snoozeOptions(row)"
                @select="(key: string | number) => onSnoozeSelect(key, row)"
              >
                <NButton size="tiny" quaternary>延后</NButton>
              </NDropdown>
              <span class="text-12px opacity-50">{{ row.createdAt }}</span>
            </div>
          </div>
        </NListItem>
      </NList>
    </NSpin>
  </div>
</template>

<style scoped>
.n-list {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-md);
}
.n-list-item {
  border-color: var(--color-hairline) !important;
}
</style>
