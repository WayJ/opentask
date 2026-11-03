<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { fetchInboxList } from '@/service/api';

defineOptions({ name: 'InboxBell' });

const router = useRouter();
const unread = ref(0);

async function refresh() {
  const { data, error } = await fetchInboxList({ unreadOnly: true, page: 1, pageSize: 1 });
  if (!error && data) {
    unread.value = data.unreadCount ?? 0;
  }
}

function goInbox() {
  router.push({ name: 'inbox' });
}

onMounted(refresh);
</script>

<template>
  <ButtonIcon tooltip-content="Inbox" @click="goInbox">
    <NBadge :value="unread" :max="99" :show-zero="false" processing>
      <SvgIcon icon="mdi:bell-outline" class="text-icon-large" />
    </NBadge>
  </ButtonIcon>
</template>
