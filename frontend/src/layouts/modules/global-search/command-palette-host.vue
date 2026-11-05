<script lang="ts" setup>
import { watch, watchEffect } from 'vue';
import { useRouter } from 'vue-router';
import { useDebounceFn } from '@vueuse/core';
import { issueApi } from '@/service/api/issue';
import { fetchProjectList } from '@/service/api/project';
import { fetchSavedViews } from '@/service/api/saved-views';
import { fetchCycles } from '@/service/api/cycles';
import { useRouteStore } from '@/store/modules/route';
import { useAppHotkeys } from '@/composables/use-app-hotkeys';
import { useCommandPalette } from '@/composables/use-command-palette';
import { useIssueFocus } from '@/composables/use-issue-focus';
import { useIssueFieldPickers } from '@/composables/use-issue-field-pickers';
import { buildFocusIssueActions, buildNavActions, menusToPaletteItems } from '@/utils/command-palette';
import {
  cyclesToPaletteItems,
  filterByNameQuery,
  issuesToPaletteItems,
  mergeIssuesById,
  projectsToPaletteItems,
  resolveIssueSearchPlan,
  savedViewsToPaletteItems
} from '@/utils/command-palette-entities';
import { $t } from '@/locales';
import SearchModal from './components/search-modal.vue';
import IssueHotkeyPickerHost from './issue-hotkey-picker-host.vue';

defineOptions({ name: 'CommandPaletteHost' });

const router = useRouter();
const routeStore = useRouteStore();
const palette = useCommandPalette();
const focus = useIssueFocus();
const pickers = useIssueFieldPickers();

useAppHotkeys();

const navigate = (to: string | { path: string; query?: Record<string, string> }) => {
  router.push(to);
};

watchEffect(() => {
  palette.setGroupLabels({
    actions: $t('common.commandPalette.groupActions'),
    menus: $t('common.commandPalette.groupMenus'),
    issues: $t('common.commandPalette.groupIssues'),
    projects: $t('common.commandPalette.groupProjects'),
    views: $t('common.commandPalette.groupViews'),
    cycles: $t('common.commandPalette.groupCycles')
  });

  const navActions = buildNavActions(navigate, {
    search: $t('common.commandPalette.navSearch'),
    issues: $t('common.commandPalette.navIssues'),
    createIssue: $t('common.commandPalette.navCreateIssue'),
    createFromTemplate: $t('common.commandPalette.navCreateFromTemplate'),
    projects: $t('common.commandPalette.navProjects'),
    inbox: $t('common.commandPalette.navInbox'),
    triage: $t('common.commandPalette.navTriage'),
    initiatives: $t('common.commandPalette.navInitiatives'),
    cycles: $t('common.commandPalette.navCycles'),
    labels: $t('common.commandPalette.navLabels'),
    issueTemplates: $t('route.workspace_issue-templates')
  });
  const focusActions = buildFocusIssueActions({
    hasFocusedIssue: Boolean(focus.focusedIssueId.value),
    openLabels: () => pickers.openLabels(),
    openEstimate: () => pickers.openEstimate(),
    title: $t('common.commandPalette.actionAddLabel'),
    estimateTitle: '设置估点…'
  });
  const actions = [...navActions, ...focusActions];

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

let searchSeq = 0;

async function runEntitySearch(rawQuery: string) {
  const q = rawQuery.trim();
  searchSeq += 1;
  const seq = searchSeq;
  if (!q) {
    palette.setEntitySources({ issues: [], projects: [], savedViews: [], cycles: [] });
    palette.setEntityLoading(false);
    return;
  }

  palette.setEntityLoading(true);
  const plan = resolveIssueSearchPlan(q);

  try {
    const [issuesRes, byCodeRes, projectsRes, viewsRes, cyclesRes] = await Promise.all([
      issueApi.getIssues({ search: plan.search, page: 1, page_size: 10 }).catch(() => ({ data: null })),
      plan.fetchByCode && plan.code
        ? issueApi.getIssue(plan.code, { byCode: true }).catch(() => ({ data: null }))
        : Promise.resolve({ data: null }),
      fetchProjectList().catch(() => ({ data: null })),
      fetchSavedViews().catch(() => ({ data: null })),
      fetchCycles().catch(() => ({ data: null }))
    ]);

    if (seq !== searchSeq) return;

    const searchedIssues = (issuesRes as { data?: { rows?: Api.Issue.Issue[] } }).data?.rows ?? [];
    const byCodeIssue = (byCodeRes as { data?: Api.Issue.Issue | null }).data;
    const mergedIssues = mergeIssuesById(byCodeIssue ? [byCodeIssue] : [], searchedIssues);

    const projects = filterByNameQuery(
      ((projectsRes as { data?: Api.Project.Project[] }).data ?? []) as Api.Project.Project[],
      q
    ).slice(0, 10);

    const views = filterByNameQuery(
      ((viewsRes as { data?: { rows?: { id: string; name: string; isFavorite: boolean }[] } }).data?.rows ??
        []) as import('@/service/api/saved-views').SavedView[],
      q
    ).slice(0, 10);

    const cycles = filterByNameQuery(
      ((cyclesRes as { data?: { rows?: { id: string; name: string; status: string }[] } }).data?.rows ??
        []) as import('@/service/api/cycles').CycleItem[],
      q
    ).slice(0, 10);

    const applyView = (id: string) => {
      router.push({ path: '/issue/list', query: { view: id } });
    };

    palette.setEntitySources({
      issues: issuesToPaletteItems(mergedIssues, navigate),
      projects: projectsToPaletteItems(projects, navigate),
      savedViews: savedViewsToPaletteItems(views, applyView),
      cycles: cyclesToPaletteItems(cycles, navigate)
    });
  } finally {
    if (seq === searchSeq) palette.setEntityLoading(false);
  }
}

const debouncedEntitySearch = useDebounceFn(runEntitySearch, 300);

watch(
  () => palette.query.value,
  q => {
    if (!q.trim()) {
      searchSeq += 1;
      palette.setEntitySources({ issues: [], projects: [], savedViews: [], cycles: [] });
      palette.setEntityLoading(false);
      return;
    }
    palette.setEntityLoading(true);
    debouncedEntitySearch(q);
  }
);
</script>

<template>
  <SearchModal />
  <IssueHotkeyPickerHost />
</template>
