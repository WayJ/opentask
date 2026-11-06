<script setup lang="ts">
import { useRouter } from 'vue-router';
import { createReusableTemplate } from '@vueuse/core';
import type { RouteKey } from '@elegant-router/types';
import { useThemeStore } from '@/store/modules/theme';
import { useRouteStore } from '@/store/modules/route';
import { useRouterPush } from '@/hooks/common/router';

defineOptions({
  name: 'GlobalBreadcrumb'
});

const themeStore = useThemeStore();
const routeStore = useRouteStore();
const router = useRouter();
const { routerPushByKey } = useRouterPush();

interface BreadcrumbContentProps {
  breadcrumb: App.Global.Menu;
}

const [DefineBreadcrumbContent, BreadcrumbContent] = createReusableTemplate<BreadcrumbContentProps>();

function handleClickMenu(key: RouteKey) {
  routerPushByKey(key);
}

function openCrumb(item: App.Global.Breadcrumb) {
  router.push({ name: item.key });
}
</script>

<template>
  <NBreadcrumb v-if="themeStore.header.breadcrumb.visible">
    <!-- define component start: BreadcrumbContent -->
    <DefineBreadcrumbContent v-slot="{ breadcrumb }">
      <div class="i-flex-y-center align-middle">
        <component :is="breadcrumb.icon" v-if="themeStore.header.breadcrumb.showIcon" class="mr-4px text-icon" />
        {{ breadcrumb.label }}
      </div>
    </DefineBreadcrumbContent>
    <!-- define component end: BreadcrumbContent -->

    <NBreadcrumbItem v-for="(item, index) in routeStore.breadcrumbs" :key="item.key">
      <NDropdown v-if="item.options?.length" :options="item.options" @select="handleClickMenu">
        <BreadcrumbContent :breadcrumb="item" />
      </NDropdown>
      <button
        v-else-if="index < routeStore.breadcrumbs.length - 1"
        type="button"
        class="ot-crumb"
        @click="openCrumb(item)"
      >
        <BreadcrumbContent :breadcrumb="item" />
      </button>
      <BreadcrumbContent v-else :breadcrumb="item" />
    </NBreadcrumbItem>
  </NBreadcrumb>
</template>

<style scoped>
.ot-crumb {
  border: 0;
  padding: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
}

.ot-crumb:focus-visible {
  outline: 2px solid var(--vk-accent);
  outline-offset: 2px;
}
</style>
