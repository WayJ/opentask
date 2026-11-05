<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAppStore } from '@/store/modules/app';

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
          <button type="button" class="customers-nav__btn" @click="go">👥</button>
        </template>
        客户
      </NTooltip>
    </template>
    <button v-else type="button" class="customers-nav__row" @click="go">
      <span class="customers-nav__icon">👥</span>
      <span class="customers-nav__label">客户</span>
      <span class="customers-nav__hint">需求</span>
    </button>
  </div>
</template>

<style scoped>
.customers-nav {
  padding: 4px 8px 0;
}
.customers-nav.collapsed {
  display: flex;
  justify-content: center;
  padding: 4px 0 0;
}
.customers-nav__btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: transparent;
  cursor: pointer;
}
.customers-nav__btn:hover,
.customers-nav.active .customers-nav__btn {
  background: rgba(94, 106, 210, 0.12);
}
.customers-nav__row {
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
.customers-nav__row:hover,
.customers-nav.active .customers-nav__row {
  background: rgba(94, 106, 210, 0.12);
}
.customers-nav__icon {
  font-size: 14px;
}
.customers-nav__label {
  font-size: 13px;
  font-weight: 500;
}
.customers-nav__hint {
  margin-left: auto;
  font-size: 11px;
  opacity: 0.55;
}
</style>
