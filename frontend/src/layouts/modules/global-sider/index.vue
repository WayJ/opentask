<script setup lang="ts">
import { computed } from 'vue';
import { GLOBAL_SIDER_MENU_ID } from '@/constants/app';
import { useAppStore } from '@/store/modules/app';
import { useThemeStore } from '@/store/modules/theme';
import GlobalLogo from '../global-logo/index.vue';
import FavoritesNav from './FavoritesNav.vue';
import TriageNav from './TriageNav.vue';
import CustomersNav from './CustomersNav.vue';
import InsightsNav from './InsightsNav.vue';
import ActivityNav from './ActivityNav.vue';

defineOptions({
  name: 'GlobalSider'
});

const appStore = useAppStore();
const themeStore = useThemeStore();

const isTopHybridSidebarFirst = computed(() => themeStore.layout.mode === 'top-hybrid-sidebar-first');
const isTopHybridHeaderFirst = computed(() => themeStore.layout.mode === 'top-hybrid-header-first');
const darkMenu = computed(
  () =>
    !themeStore.darkMode && !isTopHybridSidebarFirst.value && !isTopHybridHeaderFirst.value && themeStore.sider.inverted
);
const showLogo = computed(() => themeStore.layout.mode === 'vertical');
const menuWrapperClass = computed(() => (showLogo.value ? 'flex-1-hidden' : 'h-full'));
</script>

<template>
  <DarkModeContainer class="size-full flex-col-stretch shadow-sider" :inverted="darkMenu">
    <GlobalLogo
      v-if="showLogo"
      :show-title="!appStore.siderCollapse"
      :style="{ height: themeStore.header.height + 'px' }"
    />
    <div class="global-sider__quick" :class="{ 'is-collapsed': appStore.siderCollapse }">
      <TriageNav />
      <CustomersNav />
      <InsightsNav />
      <ActivityNav />
    </div>
    <FavoritesNav />
    <div :id="GLOBAL_SIDER_MENU_ID" :class="menuWrapperClass"></div>
  </DarkModeContainer>
</template>

<style scoped>
.global-sider__quick {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 6px 8px 0;
  margin: 0;
}
.global-sider__quick.is-collapsed {
  align-items: center;
  padding: 6px 0 0;
}
</style>
