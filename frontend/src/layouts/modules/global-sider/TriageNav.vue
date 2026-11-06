<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { NTooltip } from 'naive-ui';
import { useAppStore } from '@/store/modules/app';
import { $t } from '@/locales';

defineOptions({ name: 'TriageNav' });

const router = useRouter();
const route = useRoute();
const appStore = useAppStore();
const collapsed = computed(() => appStore.siderCollapse);
const active = computed(() => route.name === 'triage' || route.path.startsWith('/triage'));

function go() {
  router.push({ name: 'triage' });
}
</script>

<template>
  <div class="triage-nav" :class="{ collapsed, active }">
    <NTooltip v-if="collapsed" placement="right">
      <template #trigger>
        <button type="button" class="triage-nav__btn" @click="go">📥</button>
      </template>
      {{ $t('page.sider.triage') }}
    </NTooltip>
    <button v-else type="button" class="triage-nav__row" @click="go">
      <span class="triage-nav__icon">📥</span>
      <span class="triage-nav__label">{{ $t('page.sider.triage') }}</span>
      <span class="triage-nav__hint">{{ $t('page.sider.triageHint') }}</span>
    </button>
  </div>
</template>

<style scoped>
.triage-nav {
  padding: 4px 8px 8px;
}
.triage-nav.collapsed {
  display: flex;
  justify-content: center;
  padding: 4px 0 8px;
}
.triage-nav__btn {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  padding: 6px;
  border-radius: 6px;
}
.triage-nav__btn:hover,
.triage-nav.active .triage-nav__btn {
  background: var(--vk-accent-soft);
}
.triage-nav__row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 6px;
  text-align: left;
  color: inherit;
}
.triage-nav__row:hover,
.triage-nav.active .triage-nav__row {
  background: var(--vk-accent-soft);
}
.triage-nav__icon {
  font-size: 14px;
}
.triage-nav__label {
  font-size: 13px;
  font-weight: 500;
}
.triage-nav__hint {
  margin-left: auto;
  font-size: 11px;
  color: var(--vk-muted);
}
</style>
