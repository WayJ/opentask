<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { fetchInboxList } from '@/service/api';
import { useAuthStore } from '@/store/modules/auth';
import { subscribeWorkspaceRealtime } from '@/composables/use-workspace-realtime';

defineOptions({ name: 'InboxBell' });

const router = useRouter();
const authStore = useAuthStore();
const unread = ref(0);
let unsub: (() => void) | null = null;

async function refresh() {
  const { data, error } = await fetchInboxList({ unreadOnly: true, page: 1, pageSize: 1 });
  if (!error && data) {
    unread.value = data.unreadCount ?? 0;
  }
}

function goInbox() {
  router.push({ name: 'inbox' });
}

onMounted(() => {
  refresh();
  unsub = subscribeWorkspaceRealtime(ev => {
    if (ev.type !== 'inbox.created') return;
    const me = String(authStore.userInfo.userId || '');
    const recipient = String(ev.payload?.recipient_user_id || '');
    if (me && recipient && recipient !== me) return;
    refresh();
  });
});

onUnmounted(() => {
  unsub?.();
  unsub = null;
});
</script>

<template>
  <ButtonIcon tooltip-content="Inbox" @click="goInbox">
    <NBadge :value="unread" :max="99" :show-zero="false" processing>
      <SvgIcon icon="mdi:bell-outline" class="text-icon-large" />
    </NBadge>
  </ButtonIcon>
</template>
