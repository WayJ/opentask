<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useDebounceFn } from '@vueuse/core';
import { fetchGlobalSearch, type GlobalSearchResult } from '@/service/api/search';
import {
  flattenSearchResults,
  moveActiveIndex,
  type SearchFlatItem,
  type SearchGroupId
} from '@/utils/global-search';
import { $t } from '@/locales';

defineOptions({ name: 'GlobalSearchPage' });

const route = useRoute();
const router = useRouter();

const query = ref(String(route.query.q || ''));
const loading = ref(false);
const error = ref('');
const result = ref<GlobalSearchResult>({ issues: [], projects: [], docs: [], members: [] });
const activeIndex = ref(0);

const flat = computed(() => flattenSearchResults(result.value));

const groupLabel = (g: SearchGroupId) => {
  const map: Record<SearchGroupId, string> = {
    issues: $t('page.search.groupIssues'),
    projects: $t('page.search.groupProjects'),
    docs: $t('page.search.groupDocs'),
    members: $t('page.search.groupMembers')
  };
  return map[g];
};

const grouped = computed(() => {
  const order: SearchGroupId[] = ['issues', 'projects', 'docs', 'members'];
  return order
    .map(g => ({
      id: g,
      label: groupLabel(g),
      items: flat.value.filter(i => i.group === g)
    }))
    .filter(g => g.items.length > 0);
});

async function runSearch(q: string) {
  const trimmed = q.trim();
  error.value = '';
  if (!trimmed) {
    result.value = { issues: [], projects: [], docs: [], members: [] };
    activeIndex.value = 0;
    return;
  }
  loading.value = true;
  try {
    const data = await fetchGlobalSearch(trimmed, 12);
    result.value = data || { issues: [], projects: [], docs: [], members: [] };
    activeIndex.value = flat.value.length ? 0 : -1;
  } catch (e: any) {
    error.value = e?.message || String(e);
    result.value = { issues: [], projects: [], docs: [], members: [] };
    activeIndex.value = -1;
  } finally {
    loading.value = false;
  }
}

const debounced = useDebounceFn((q: string) => {
  router.replace({ path: '/search', query: q.trim() ? { q: q.trim() } : {} });
  runSearch(q);
}, 220);

watch(query, q => debounced(q));

watch(
  () => route.query.q,
  q => {
    const next = String(q || '');
    if (next !== query.value) {
      query.value = next;
      runSearch(next);
    }
  }
);

function openItem(item: SearchFlatItem) {
  router.push(item.href as any);
}

function onKeydown(ev: KeyboardEvent) {
  const tag = (ev.target as HTMLElement | null)?.tagName;
  // allow arrows even from input
  if (ev.key === 'ArrowDown') {
    ev.preventDefault();
    activeIndex.value = moveActiveIndex(activeIndex.value, 1, flat.value.length);
  } else if (ev.key === 'ArrowUp') {
    ev.preventDefault();
    activeIndex.value = moveActiveIndex(activeIndex.value, -1, flat.value.length);
  } else if (ev.key === 'Enter') {
    const item = flat.value[activeIndex.value];
    if (item) {
      ev.preventDefault();
      openItem(item);
    }
  } else if (ev.key === 'Escape' && tag !== 'INPUT') {
    query.value = '';
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown);
  runSearch(query.value);
});
onUnmounted(() => window.removeEventListener('keydown', onKeydown));

function flatIndexOf(item: SearchFlatItem): number {
  return flat.value.findIndex(f => f.id === item.id);
}
</script>

<template>
  <div class="h-full flex-col-stretch gap-16px overflow-hidden p-16px">
    <div class="flex items-center gap-12px">
      <NInput
        v-model:value="query"
        clearable
        size="large"
        :placeholder="$t('page.search.placeholder')"
        class="max-w-720px"
      >
        <template #prefix>
          <icon-uil-search class="text-icon" />
        </template>
      </NInput>
      <NSpin v-if="loading" :size="18" />
    </div>

    <NAlert v-if="error" type="error" :title="error" class="max-w-720px" />

    <div v-if="!query.trim()" class="text-14px text-gray-500">
      {{ $t('page.search.hint') }}
    </div>

    <div v-else-if="!loading && flat.length === 0" class="text-14px text-gray-500">
      {{ $t('page.search.empty') }}
    </div>

    <div class="flex-1 overflow-auto">
      <div v-for="g in grouped" :key="g.id" class="mb-16px max-w-720px">
        <div class="mb-8px text-12px font-medium uppercase tracking-wide text-gray-500">
          {{ g.label }}
        </div>
        <NList bordered clickable hoverable>
          <NListItem
            v-for="item in g.items"
            :key="item.id"
            :class="{ 'bg-[var(--n-color-hover)]': flatIndexOf(item) === activeIndex }"
            @click="openItem(item)"
            @mouseenter="activeIndex = flatIndexOf(item)"
          >
            <div class="flex-col gap-2px">
              <div class="text-14px font-medium">{{ item.title }}</div>
              <div v-if="item.subtitle" class="text-12px text-gray-500 truncate">{{ item.subtitle }}</div>
            </div>
          </NListItem>
        </NList>
      </div>
    </div>
  </div>
</template>
