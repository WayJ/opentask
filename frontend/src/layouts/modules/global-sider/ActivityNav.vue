<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { issueApi } from '@/service/api/issue';
import { useAppStore } from '@/store/modules/app';
import { formatUnreadBadge } from '@/utils/activityFeed';
import { $t } from '@/locales';

defineOptions({ name: 'ActivityNav' });

const route = useRoute();
const router = useRouter();
const appStore = useAppStore();
const collapsed = computed(() => appStore.siderCollapse);
const active = computed(() => route.name === 'activity' || route.path.startsWith('/activity'));

const unread = ref(0);
const capped = ref(false);
const badge = computed(() => formatUnreadBadge(unread.value, capped.value));

let timer: ReturnType<typeof setInterval> | null = null;

async function refreshUnread() {
  try {
    const { data, error } = await issueApi.fetchActivityUnreadCount({ watching: true });
    if (error || !data) return;
    unread.value = data.count || 0;
    capped.value = !!data.capped;
  } catch {
    /* ignore */
  }
}

function go() {
  router.push({ name: 'activity', query: { watching: '1' } });
}

onMounted(() => {
  refreshUnread();
  timer = setInterval(refreshUnread, 60000);
});

onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<template>
  <div class="activity-nav" :class="{ collapsed, active }">
    <template v-if="collapsed">
      <NTooltip placement="right">
        <template #trigger>
          <button type="button" class="activity-nav__btn" @click="go">
            🔔
            <span v-if="badge" class="activity-nav__dot">{{ badge }}</span>
          </button>
        </template>
        {{ $t('page.sider.activity') }}{{ badge ? `（${badge}）` : '' }}
      </NTooltip>
    </template>
    <button v-else type="button" class="activity-nav__row" @click="go">
      <span class="activity-nav__icon">🔔</span>
      <span class="activity-nav__label">{{ $t('page.sider.activity') }}</span>
      <span v-if="badge" class="activity-nav__badge">{{ badge }}</span>
      <span v-else class="activity-nav__hint">{{ $t('page.sider.activityHint') }}</span>
    </button>
  </div>
</template>

<style scoped>
.activity-nav {
  padding: 4px 8px 0;
}
.activity-nav.collapsed {
  display: flex;
  justify-content: center;
  padding: 4px 0 0;
}
.activity-nav__btn {
  position: relative;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: transparent;
  cursor: pointer;
}
.activity-nav__btn:hover,
.activity-nav.active .activity-nav__btn {
  background: var(--vk-accent-soft);
}
.activity-nav__dot {
  position: absolute;
  top: 2px;
  right: 0;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 999px;
  background: #e5484d;
  color: #fff;
  font-size: 10px;
  line-height: 16px;
}
.activity-nav__row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: inherit;
}
.activity-nav__row:hover,
.activity-nav.active .activity-nav__row {
  background: var(--vk-accent-soft);
}
.activity-nav__icon {
  font-size: 14px;
}
.activity-nav__label {
  font-size: 13px;
  font-weight: 500;
}
.activity-nav__hint {
  margin-left: auto;
  font-size: 11px;
  color: var(--vk-muted);
}
.activity-nav__badge {
  margin-left: auto;
  min-width: 18px;
  padding: 0 6px;
  height: 18px;
  border-radius: 999px;
  background: #e5484d;
  color: #fff;
  font-size: 11px;
  line-height: 18px;
  text-align: center;
}
</style>
