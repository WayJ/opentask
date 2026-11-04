<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAppStore } from '@/store/modules/app';

defineOptions({ name: 'ActivityNav' });

const route = useRoute();
const router = useRouter();
const appStore = useAppStore();
const collapsed = computed(() => appStore.siderCollapse);
const active = computed(() => route.name === 'activity' || route.path.startsWith('/activity'));

function go() {
  router.push({ name: 'activity' });
}
</script>

<template>
  <div class="activity-nav" :class="{ collapsed, active }">
    <template v-if="collapsed">
      <NTooltip placement="right">
        <template #trigger>
          <button type="button" class="activity-nav__btn" @click="go">📋</button>
        </template>
        活动
      </NTooltip>
    </template>
    <button v-else type="button" class="activity-nav__row" @click="go">
      <span class="activity-nav__icon">📋</span>
      <span class="activity-nav__label">活动</span>
      <span class="activity-nav__hint">Feed</span>
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
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: transparent;
  cursor: pointer;
}
.activity-nav__btn:hover,
.activity-nav.active .activity-nav__btn {
  background: rgba(94, 106, 210, 0.12);
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
  background: rgba(94, 106, 210, 0.12);
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
  opacity: 0.55;
}
</style>
