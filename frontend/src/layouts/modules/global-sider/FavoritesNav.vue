<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { NEmpty, NSpin, NText, NTooltip } from 'naive-ui';
import { type FavoriteItem, fetchFavorites } from '@/service/api/favorites';
import { useAppStore } from '@/store/modules/app';
import {
  FAVORITE_TYPE_LABEL,
  type FavoriteTargetType,
  favoriteLabel,
  favoriteNavTarget,
  sortFavoritesByPosition
} from '@/utils/favorites';
import { $t } from '@/locales';

defineOptions({ name: 'FavoritesNav' });

const router = useRouter();
const appStore = useAppStore();
const collapsed = computed(() => appStore.siderCollapse);

const loading = ref(false);
const rows = ref<FavoriteItem[]>([]);

const ordered = computed(() => sortFavoritesByPosition(rows.value));

async function load() {
  loading.value = true;
  try {
    const res = await fetchFavorites();
    rows.value = res.data?.rows || [];
  } catch {
    rows.value = [];
  } finally {
    loading.value = false;
  }
}

function iconFor(type: string): string {
  if (type === 'project') return '📁';
  if (type === 'saved_view') return '🔖';
  if (type === 'initiative') return '🚩';
  if (type === 'issue') return '🎫';
  return '★';
}

function onClick(fav: FavoriteItem) {
  router.push(favoriteNavTarget(fav));
}

function typeHint(type: string): string {
  const keyByType: Record<string, App.I18n.I18nKey> = {
    project: 'page.shell.favoriteProject',
    saved_view: 'page.shell.favoriteView',
    issue: 'page.shell.favoriteIssue',
    initiative: 'page.shell.favoriteInitiative'
  };
  const key = keyByType[type];
  return key ? $t(key) : FAVORITE_TYPE_LABEL[type as FavoriteTargetType] || type;
}

onMounted(load);

// Refresh when sider expands (cheap; also allows other pages to bump via custom event)
watch(collapsed, (v, old) => {
  if (old === true && v === false) load();
});

if (typeof window !== 'undefined') {
  window.addEventListener('opentask:favorites-changed', () => {
    load();
  });
}

defineExpose({ reload: load });
</script>

<template>
  <div class="favorites-nav" :class="{ collapsed }">
    <div v-if="!collapsed" class="favorites-nav__title">
      <NText depth="3" style="font-size: 12px">{{ $t('page.shell.favorites.title') }}</NText>
    </div>
    <NSpin :show="loading" size="small">
      <NEmpty
        v-if="!loading && ordered.length === 0"
        :description="collapsed ? '' : $t('page.shell.favorites.empty')"
        size="small"
        class="favorites-nav__empty"
      />
      <ul v-else class="favorites-nav__list">
        <li v-for="fav in ordered" :key="fav.id">
          <NTooltip :disabled="!collapsed" placement="right">
            <template #trigger>
              <button type="button" class="favorites-nav__item" @click="onClick(fav)">
                <span class="favorites-nav__icon" aria-hidden="true">{{ iconFor(fav.targetType) }}</span>
                <span v-if="!collapsed" class="favorites-nav__label">
                  <span class="favorites-nav__name">{{ favoriteLabel(fav) }}</span>
                  <span class="favorites-nav__type">{{ typeHint(fav.targetType) }}</span>
                </span>
              </button>
            </template>
            {{ favoriteLabel(fav) }} · {{ typeHint(fav.targetType) }}
          </NTooltip>
        </li>
      </ul>
    </NSpin>
  </div>
</template>

<style scoped>
.favorites-nav {
  padding: 8px 10px 4px;
  border-bottom: 1px solid var(--color-hairline);
  max-height: 40%;
  overflow: auto;
}

.favorites-nav.collapsed {
  padding: 8px 4px;
}

.favorites-nav__title {
  padding: 0 4px 6px;
  font-weight: 500;
}

.favorites-nav__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.favorites-nav__item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  border-radius: var(--radius-sm);
  padding: 6px 8px;
  text-align: left;
}

.favorites-nav.collapsed .favorites-nav__item {
  justify-content: center;
  padding: 8px 0;
}

.favorites-nav__item:hover {
  background: var(--color-bg-hover);
}

.favorites-nav__icon {
  flex: none;
  width: 18px;
  text-align: center;
  font-size: 14px;
}

.favorites-nav__label {
  min-width: 0;
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.favorites-nav__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.favorites-nav__type {
  font-size: 11px;
  opacity: 0.65;
}

.favorites-nav__empty {
  padding: 4px 0 8px;
}
</style>
