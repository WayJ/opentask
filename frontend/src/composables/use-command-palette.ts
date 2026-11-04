import { computed, ref } from 'vue';
import {
  type PaletteGroup,
  type PaletteItem,
  buildPaletteGroups,
  clampActiveIndex,
  flattenGroupItems
} from '@/utils/command-palette';

const isOpen = ref(false);
const query = ref('');
const activeIndex = ref(0);
const actionSource = ref<PaletteItem[]>([]);
const menuSource = ref<PaletteItem[]>([]);
const issueSource = ref<PaletteItem[]>([]);
const projectSource = ref<PaletteItem[]>([]);
const viewSource = ref<PaletteItem[]>([]);
const cycleSource = ref<PaletteItem[]>([]);
const entityLoading = ref(false);
const groupLabels = ref({
  actions: 'Actions',
  menus: 'Menus',
  issues: 'Issues',
  projects: 'Projects',
  views: 'Views',
  cycles: 'Cycles'
});

/** Test-only reset of module singleton state. */
export function resetCommandPaletteForTests() {
  isOpen.value = false;
  query.value = '';
  activeIndex.value = 0;
  actionSource.value = [];
  menuSource.value = [];
  issueSource.value = [];
  projectSource.value = [];
  viewSource.value = [];
  cycleSource.value = [];
  entityLoading.value = false;
  groupLabels.value = {
    actions: 'Actions',
    menus: 'Menus',
    issues: 'Issues',
    projects: 'Projects',
    views: 'Views',
    cycles: 'Cycles'
  };
}

/** Shared command palette state (singleton across BaseLayout host + header button). */
export function useCommandPalette() {
  const groups = computed<PaletteGroup[]>(() =>
    buildPaletteGroups({
      actions: actionSource.value,
      menus: menuSource.value,
      query: query.value,
      groupLabels: groupLabels.value,
      issues: issueSource.value,
      projects: projectSource.value,
      savedViews: viewSource.value,
      cycles: cycleSource.value
    })
  );

  const flatItems = computed(() => flattenGroupItems(groups.value));
  const activeItem = computed(() => flatItems.value[activeIndex.value] ?? null);

  function open() {
    isOpen.value = true;
  }

  function close() {
    isOpen.value = false;
    query.value = '';
    activeIndex.value = 0;
    issueSource.value = [];
    projectSource.value = [];
    viewSource.value = [];
    cycleSource.value = [];
    entityLoading.value = false;
  }

  function toggle() {
    if (isOpen.value) close();
    else open();
  }

  function setQuery(q: string) {
    query.value = q;
    activeIndex.value = 0;
  }

  function setSources(opts: { actions: PaletteItem[]; menus: PaletteItem[] }) {
    actionSource.value = opts.actions;
    menuSource.value = opts.menus;
    const len = flattenGroupItems(
      buildPaletteGroups({
        actions: opts.actions,
        menus: opts.menus,
        query: query.value,
        groupLabels: groupLabels.value,
        issues: issueSource.value,
        projects: projectSource.value,
        savedViews: viewSource.value,
        cycles: cycleSource.value
      })
    ).length;
    activeIndex.value = clampActiveIndex(activeIndex.value, len);
  }

  function setEntitySources(opts: {
    issues: PaletteItem[];
    projects: PaletteItem[];
    savedViews: PaletteItem[];
    cycles?: PaletteItem[];
  }) {
    issueSource.value = opts.issues;
    projectSource.value = opts.projects;
    viewSource.value = opts.savedViews;
    cycleSource.value = opts.cycles ?? [];
    activeIndex.value = clampActiveIndex(activeIndex.value, flatItems.value.length);
  }

  function setEntityLoading(loading: boolean) {
    entityLoading.value = loading;
  }

  function setGroupLabels(labels: {
    actions: string;
    menus: string;
    issues?: string;
    projects?: string;
    views?: string;
    cycles?: string;
  }) {
    groupLabels.value = {
      actions: labels.actions,
      menus: labels.menus,
      issues: labels.issues ?? groupLabels.value.issues,
      projects: labels.projects ?? groupLabels.value.projects,
      views: labels.views ?? groupLabels.value.views,
      cycles: labels.cycles ?? groupLabels.value.cycles
    };
  }

  function moveDown() {
    const len = flatItems.value.length;
    if (!len) return;
    activeIndex.value = (activeIndex.value + 1) % len;
  }

  function moveUp() {
    const len = flatItems.value.length;
    if (!len) return;
    activeIndex.value = (activeIndex.value - 1 + len) % len;
  }

  async function run(item: PaletteItem) {
    close();
    await item.run();
  }

  async function runActive() {
    const item = activeItem.value;
    if (!item) return;
    await run(item);
  }

  return {
    isOpen,
    query,
    activeIndex,
    groups,
    flatItems,
    activeItem,
    entityLoading,
    open,
    close,
    toggle,
    setQuery,
    setSources,
    setEntitySources,
    setEntityLoading,
    setGroupLabels,
    moveUp,
    moveDown,
    run,
    runActive
  };
}
