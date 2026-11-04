<script lang="ts" setup>
import { computed } from 'vue';
import { onKeyStroke } from '@vueuse/core';
import { useAppStore } from '@/store/modules/app';
import { useThemeStore } from '@/store/modules/theme';
import { useCommandPalette } from '@/composables/use-command-palette';
import type { PaletteItem } from '@/utils/command-palette';
import { $t } from '@/locales';
import SearchFooter from './search-footer.vue';

defineOptions({ name: 'SearchModal' });

const appStore = useAppStore();
const theme = useThemeStore();
const {
  isOpen,
  query,
  groups,
  flatItems,
  activeItem,
  activeIndex,
  entityLoading,
  open,
  close,
  setQuery,
  moveUp,
  moveDown,
  run,
  runActive
} = useCommandPalette();

const isMobile = computed(() => appStore.isMobile);

const visible = computed({
  get: () => isOpen.value,
  set: (v: boolean) => {
    if (v) open();
    else close();
  }
});

const keyword = computed({
  get: () => query.value,
  set: (v: string) => setQuery(v)
});

const showSearching = computed(() => entityLoading.value && Boolean(query.value.trim()));

function handleClose() {
  close();
}

function handleUp(e: KeyboardEvent) {
  if (!isOpen.value) return;
  e.preventDefault();
  moveUp();
}

function handleDown(e: KeyboardEvent) {
  if (!isOpen.value) return;
  e.preventDefault();
  moveDown();
}

function handleEnter(e: KeyboardEvent) {
  if (!isOpen.value) return;
  e.preventDefault();
  runActive();
}

function handleHover(item: PaletteItem) {
  const idx = flatItems.value.findIndex(i => i.id === item.id);
  if (idx >= 0) activeIndex.value = idx;
}

onKeyStroke('Escape', () => {
  if (isOpen.value) handleClose();
});
onKeyStroke('Enter', handleEnter);
onKeyStroke('ArrowUp', handleUp);
onKeyStroke('ArrowDown', handleDown);
</script>

<template>
  <NModal
    v-model:show="visible"
    :segmented="{ footer: 'soft' }"
    :closable="false"
    preset="card"
    auto-focus
    footer-style="padding: 0; margin: 0"
    class="fixed left-0 right-0"
    :class="[isMobile ? 'size-full top-0px rounded-0' : 'w-630px top-50px']"
  >
    <NInputGroup>
      <NInput v-model:value="keyword" clearable :placeholder="$t('common.commandPalette.placeholder')">
        <template #prefix>
          <icon-uil-search class="text-15px text-#c2c2c2" />
        </template>
      </NInput>
      <NButton v-if="isMobile" type="primary" ghost @click="handleClose">
        {{ $t('common.cancel') }}
      </NButton>
    </NInputGroup>

    <div class="mt-20px">
      <div v-if="showSearching" class="mb-8px px-8px text-12px text-#8b8b8b dark:text-#a0a0a0">
        {{ $t('common.commandPalette.searching') }}
      </div>
      <NEmpty v-if="flatItems.length === 0 && !showSearching" :description="$t('common.noData')" />
      <NScrollbar v-else-if="flatItems.length > 0" style="max-height: 420px">
        <div class="pb-12px">
          <template v-for="group in groups" :key="group.id">
            <div class="mb-4px mt-8px px-8px text-12px text-#8b8b8b dark:text-#a0a0a0">
              {{ group.label }}
            </div>
            <div
              v-for="item in group.items"
              :key="item.id"
              class="mt-8px min-h-56px flex-y-center cursor-pointer justify-between rounded-4px bg-#e5e7eb px-14px py-8px dark:bg-dark"
              :style="{
                background: item.id === activeItem?.id ? theme.themeColor : '',
                color: item.id === activeItem?.id ? '#fff' : ''
              }"
              @click="run(item)"
              @mouseenter="handleHover(item)"
            >
              <div class="ml-5px flex-1 overflow-hidden">
                <div class="truncate">{{ item.title }}</div>
                <div
                  v-if="item.subtitle"
                  class="truncate text-12px opacity-80"
                  :style="{ color: item.id === activeItem?.id ? '#fff' : undefined }"
                >
                  {{ item.subtitle }}
                </div>
              </div>
              <icon-ant-design-enter-outlined class="icon mr-3px p-2px text-20px" />
            </div>
          </template>
        </div>
      </NScrollbar>
    </div>
    <template #footer>
      <SearchFooter v-if="!isMobile" />
    </template>
  </NModal>
</template>

<style lang="scss" scoped></style>
