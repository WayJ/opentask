<script lang="ts" setup>
import { watchEffect } from 'vue';
import { useRouter } from 'vue-router';
import { useRouteStore } from '@/store/modules/route';
import { useAppHotkeys } from '@/composables/use-app-hotkeys';
import { useCommandPalette } from '@/composables/use-command-palette';
import { buildNavActions, menusToPaletteItems } from '@/utils/command-palette';
import { $t } from '@/locales';
import SearchModal from './components/search-modal.vue';

defineOptions({ name: 'CommandPaletteHost' });

const router = useRouter();
const routeStore = useRouteStore();
const palette = useCommandPalette();

useAppHotkeys();

watchEffect(() => {
  palette.setGroupLabels({
    actions: $t('common.commandPalette.groupActions'),
    menus: $t('common.commandPalette.groupMenus')
  });

  const navigate = (path: string) => {
    router.push(path);
  };

  const actions = buildNavActions(navigate, {
    issues: $t('common.commandPalette.navIssues'),
    createIssue: $t('common.commandPalette.navCreateIssue'),
    projects: $t('common.commandPalette.navProjects'),
    inbox: $t('common.commandPalette.navInbox')
  });

  const menus = menusToPaletteItems(
    routeStore.searchMenus.map(m => ({
      routePath: m.routePath,
      label: m.label,
      i18nKey: m.i18nKey
    })),
    m => (m.i18nKey ? $t(m.i18nKey) : m.label),
    navigate
  );

  palette.setSources({ actions, menus });
});
</script>

<template>
  <SearchModal />
</template>
