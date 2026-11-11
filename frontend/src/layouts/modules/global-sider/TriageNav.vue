<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAppStore } from '@/store/modules/app';
import SvgIcon from '@/components/custom/svg-icon.vue';
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
        <button type="button" class="triage-nav__btn" :aria-label="$t('page.sider.triage')" @click="go">
          <span class="triage-nav__icon" aria-hidden="true">
            <SvgIcon icon="mdi:inbox-arrow-down" />
          </span>
        </button>
      </template>
      {{ $t('page.sider.triage') }}
    </NTooltip>
    <button v-else type="button" class="triage-nav__row" @click="go">
      <span class="triage-nav__icon" aria-hidden="true">
        <SvgIcon icon="mdi:inbox-arrow-down" />
      </span>
      <span class="triage-nav__label">{{ $t('page.sider.triage') }}</span>
      <span class="triage-nav__hint">{{ $t('page.sider.triageHint') }}</span>
    </button>
  </div>
</template>

<style scoped>
.triage-nav {
  padding: 0;
  margin: 0;
}
.triage-nav.collapsed {
  display: flex;
  justify-content: center;
  padding: 0;
  margin: 0;
}
.triage-nav__btn {
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
.triage-nav__btn:hover,
.triage-nav.active .triage-nav__btn {
  background: var(--vk-accent-soft);
}
.triage-nav__row {
  box-sizing: border-box;
  height: 34px;
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 0 8px;
  border-radius: 6px;
  text-align: left;
  color: inherit;
}
.triage-nav__row:focus-visible,
.triage-nav__btn:focus-visible {
  outline: 2px solid var(--vk-accent);
  outline-offset: 2px;
}
.triage-nav__row:hover,
.triage-nav.active .triage-nav__row {
  background: var(--vk-accent-soft);
}
.triage-nav__icon {
  display: inline-flex;
  font-size: 20px;
  color: currentColor;
  line-height: 0;
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
