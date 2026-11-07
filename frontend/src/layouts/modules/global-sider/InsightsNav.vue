<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAppStore } from '@/store/modules/app';
import { $t } from '@/locales';

defineOptions({ name: 'InsightsNav' });

const route = useRoute();
const router = useRouter();
const appStore = useAppStore();
const collapsed = computed(() => appStore.siderCollapse);
const active = computed(() => route.name === 'insights' || route.path.startsWith('/insights'));

function go() {
  router.push({ name: 'insights' });
}
</script>

<template>
  <div class="insights-nav" :class="{ collapsed, active }">
    <template v-if="collapsed">
      <NTooltip placement="right">
        <template #trigger>
          <button type="button" class="insights-nav__btn" @click="go">📈</button>
        </template>
        {{ $t('page.sider.insights') }}
      </NTooltip>
    </template>
    <button v-else type="button" class="insights-nav__row" @click="go">
      <span class="insights-nav__icon">📈</span>
      <span class="insights-nav__label">{{ $t('page.sider.insights') }}</span>
      <span class="insights-nav__hint">{{ $t('page.sider.insightsHint') }}</span>
    </button>
  </div>
</template>

<style scoped>
.insights-nav {
  padding: 4px 8px 0;
}
.insights-nav.collapsed {
  display: flex;
  justify-content: center;
  padding: 4px 0 0;
}
.insights-nav__btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: transparent;
  cursor: pointer;
}
.insights-nav__btn:hover,
.insights-nav.active .insights-nav__btn {
  background: var(--vk-accent-soft);
}
.insights-nav__row {
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
.insights-nav__row:hover,
.insights-nav.active .insights-nav__row {
  background: var(--vk-accent-soft);
}
.insights-nav__icon {
  font-size: 14px;
}
.insights-nav__label {
  font-size: 13px;
  font-weight: 500;
}
.insights-nav__hint {
  margin-left: auto;
  font-size: 11px;
  color: var(--vk-muted);
}
</style>
