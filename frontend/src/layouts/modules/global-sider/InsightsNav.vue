<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAppStore } from '@/store/modules/app';
import SvgIcon from '@/components/custom/svg-icon.vue';
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
          <button type="button" class="insights-nav__btn" :aria-label="$t('page.sider.insights')" @click="go">
            <span class="insights-nav__icon" aria-hidden="true">
              <SvgIcon icon="mdi:chart-box-outline" />
            </span>
          </button>
        </template>
        {{ $t('page.sider.insights') }}
      </NTooltip>
    </template>
    <button v-else type="button" class="insights-nav__row" @click="go">
      <span class="insights-nav__icon" aria-hidden="true">
        <SvgIcon icon="mdi:chart-box-outline" />
      </span>
      <span class="insights-nav__label">{{ $t('page.sider.insights') }}</span>
      <span class="insights-nav__hint">{{ $t('page.sider.insightsHint') }}</span>
    </button>
  </div>
</template>

<style scoped>
.insights-nav {
  padding: 0;
  margin: 0;
}
.insights-nav.collapsed {
  display: flex;
  justify-content: center;
  padding: 0;
  margin: 0;
}
.insights-nav__btn {
  box-sizing: border-box;
  width: 36px;
  height: 36px;
  padding: 0;
  margin: 0;
  border-radius: 6px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: inherit;
}
.insights-nav__btn:hover,
.insights-nav.active .insights-nav__btn {
  background: var(--vk-accent-soft);
}
.insights-nav__row {
  box-sizing: border-box;
  height: 34px;
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  padding: 0 8px;
  border-radius: 6px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: inherit;
}
.insights-nav__row:focus-visible,
.insights-nav__btn:focus-visible {
  outline: 2px solid var(--vk-accent);
  outline-offset: 2px;
}
.insights-nav__row:hover,
.insights-nav.active .insights-nav__row {
  background: var(--vk-accent-soft);
}
.insights-nav__icon {
  display: inline-flex;
  font-size: 20px;
  color: currentColor;
  line-height: 0;
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
