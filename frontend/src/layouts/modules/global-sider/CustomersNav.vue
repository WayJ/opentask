<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAppStore } from '@/store/modules/app';
import SvgIcon from '@/components/custom/svg-icon.vue';
import { $t } from '@/locales';

defineOptions({ name: 'CustomersNav' });

const route = useRoute();
const router = useRouter();
const appStore = useAppStore();
const collapsed = computed(() => appStore.siderCollapse);
const active = computed(
  () =>
    route.name === 'customers' ||
    route.name === 'customers_detail' ||
    route.name === 'requests' ||
    route.name === 'requests_detail' ||
    route.path.startsWith('/customers') ||
    route.path.startsWith('/requests')
);

function go() {
  router.push({ name: 'customers' });
}
</script>

<template>
  <div class="customers-nav" :class="{ collapsed, active }">
    <template v-if="collapsed">
      <NTooltip placement="right">
        <template #trigger>
          <button type="button" class="customers-nav__btn" :aria-label="$t('page.sider.customers')" @click="go">
            <span class="customers-nav__icon" aria-hidden="true">
              <SvgIcon icon="mdi:account-group-outline" />
            </span>
          </button>
        </template>
        {{ $t('page.sider.customers') }}
      </NTooltip>
    </template>
    <button v-else type="button" class="customers-nav__row" @click="go">
      <span class="customers-nav__icon" aria-hidden="true">
        <SvgIcon icon="mdi:account-group-outline" />
      </span>
      <span class="customers-nav__label">{{ $t('page.sider.customers') }}</span>
      <span class="customers-nav__hint">{{ $t('page.sider.customersHint') }}</span>
    </button>
  </div>
</template>

<style scoped>
.customers-nav {
  padding: 0;
  margin: 0;
}
.customers-nav.collapsed {
  display: flex;
  justify-content: center;
  padding: 0;
  margin: 0;
}
.customers-nav__btn {
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
.customers-nav__btn:hover,
.customers-nav.active .customers-nav__btn {
  background: var(--vk-accent-soft);
}
.customers-nav__row {
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
.customers-nav__row:focus-visible,
.customers-nav__btn:focus-visible {
  outline: 2px solid var(--vk-accent);
  outline-offset: 2px;
}
.customers-nav__row:hover,
.customers-nav.active .customers-nav__row {
  background: var(--vk-accent-soft);
}
.customers-nav__icon {
  display: inline-flex;
  font-size: 20px;
  color: currentColor;
  line-height: 0;
}
.customers-nav__label {
  font-size: 13px;
  font-weight: 500;
}
.customers-nav__hint {
  margin-left: auto;
  font-size: 11px;
  color: var(--vk-muted);
}
</style>
