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
const groupLabels = ref({ actions: 'Actions', menus: 'Menus' });

/** Test-only reset of module singleton state. */
export function resetCommandPaletteForTests() {
  isOpen.value = false;
  query.value = '';
  activeIndex.value = 0;
  actionSource.value = [];
  menuSource.value = [];
  groupLabels.value = { actions: 'Actions', menus: 'Menus' };
}

/** Shared command palette state (singleton across BaseLayout host + header button). */
export function useCommandPalette() {
  const groups = computed<PaletteGroup[]>(() =>
    buildPaletteGroups({
      actions: actionSource.value,
      menus: menuSource.value,
      query: query.value,
      groupLabels: groupLabels.value
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
        groupLabels: groupLabels.value
      })
    ).length;
    activeIndex.value = clampActiveIndex(activeIndex.value, len);
  }

  function setGroupLabels(labels: { actions: string; menus: string }) {
    groupLabels.value = labels;
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
    open,
    close,
    toggle,
    setQuery,
    setSources,
    setGroupLabels,
    moveUp,
    moveDown,
    run,
    runActive
  };
}
