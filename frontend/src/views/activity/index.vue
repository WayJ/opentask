<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import UserSelect from '@/components/UserSelect.vue';
import { issueApi } from '@/service/api/issue';
import {
  ACTIVITY_ACTION_OPTIONS,
  ACTIVITY_QUICK_EMOJIS,
  type ActivityItem,
  buildActivityQuery,
  emptyActivityDescription,
  formatActivityActor,
  formatActivityRow,
  toggleReactionSummary
} from '@/utils/activityFeed';

defineOptions({ name: 'ActivityPage' });

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const loadingMore = ref(false);
const items = ref<ActivityItem[]>([]);
const nextCursor = ref<string | null>(null);
const actionTypes = ref<string[]>([]);
const sincePreset = ref<'24h' | '7d' | null>('7d');
const actorId = ref<string | null>(null);
const watchingOnly = ref(false);

const empty = computed(() => !loading.value && items.value.length === 0);
const emptyDesc = computed(() => emptyActivityDescription(watchingOnly.value));

function relTime(iso?: string | null): string {
  if (!iso) return '';
  const date = new Date(iso);
  const diff = Date.now() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes}分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}小时前`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}天前`;
  return date.toLocaleDateString('zh-CN');
}

function syncWatchingFromQuery() {
  const q = route.query.watching;
  const on = q === '1' || q === 'true' || q === 'True';
  watchingOnly.value = on;
}

async function markRead(): Promise<void> {
  try {
    await issueApi.markActivityRead({ watching: watchingOnly.value });
  } catch {
    /* ignore mark-read errors on open */
  }
}

async function load(reset = true) {
  if (reset) {
    loading.value = true;
    nextCursor.value = null;
    items.value = [];
  } else {
    loadingMore.value = true;
  }
  try {
    const params = buildActivityQuery({
      sincePreset: sincePreset.value,
      actionTypes: actionTypes.value,
      actorId: actorId.value,
      watching: watchingOnly.value || null,
      cursor: reset ? null : nextCursor.value,
      limit: 50
    });
    const { data, error } = await issueApi.fetchWorkspaceActivity(params as any);
    if (error || !data) {
      window.$message?.error((error as any)?.message || '加载活动失败');
      return;
    }
    const page = (data.items || []) as ActivityItem[];
    items.value = reset ? page : items.value.concat(page);
    nextCursor.value = data.nextCursor ?? null;
    if (reset) {
      await markRead();
    }
  } finally {
    loading.value = false;
    loadingMore.value = false;
  }
}

function openIssue(item: ActivityItem) {
  router.push({ name: 'issue_detail', query: { id: item.issueId } });
}

async function toggleChip(item: ActivityItem, emoji: string, ev: Event) {
  ev.stopPropagation();
  const cur = item.reactions?.summary?.find(s => s.emoji === emoji);
  const myReacted = !!cur?.myReacted;
  const nextReacted = !myReacted;
  const prev = item.reactions ? { ...item.reactions, summary: [...(item.reactions.summary || [])] } : null;
  item.reactions = toggleReactionSummary(item.reactions, emoji, nextReacted);

  try {
    const isComment = item.reactions?.scope === 'comment' && item.reactions.commentId;
    if (isComment) {
      if (nextReacted) {
        await issueApi.addCommentReaction(item.issueId, item.reactions!.commentId!, emoji);
      } else {
        await issueApi.removeCommentReaction(item.issueId, item.reactions!.commentId!, emoji);
      }
    } else if (nextReacted) {
      await issueApi.addReaction(item.issueId, emoji);
    } else {
      await issueApi.removeReaction(item.issueId, emoji);
    }
  } catch (e: any) {
    item.reactions = prev as any;
    window.$message?.error(e?.message || '反应失败');
  }
}

watch([actionTypes, sincePreset, actorId, watchingOnly], () => load(true));

watch(
  () => route.query.watching,
  () => {
    syncWatchingFromQuery();
  }
);

onMounted(() => {
  syncWatchingFromQuery();
  load(true);
});
</script>

<template>
  <div class="activity-page p-16px">
    <div class="mb-12px flex flex-wrap items-center gap-12px">
      <h2 class="m-0 text-18px font-600">活动</h2>
      <NSelect
        v-model:value="actionTypes"
        class="w-280px"
        multiple
        clearable
        placeholder="动作类型"
        :options="ACTIVITY_ACTION_OPTIONS"
        size="small"
      />
      <NRadioGroup v-model:value="sincePreset" size="small">
        <NRadioButton :value="null">全部</NRadioButton>
        <NRadioButton value="24h">24h</NRadioButton>
        <NRadioButton value="7d">7天</NRadioButton>
      </NRadioGroup>
      <div class="w-200px">
        <UserSelect v-model="actorId" size="small" placeholder="执行者" />
      </div>
      <div class="flex items-center gap-6px text-13px">
        <NSwitch v-model:value="watchingOnly" size="small" />
        <span>仅关注</span>
      </div>
    </div>

    <NSpin :show="loading">
      <NList v-if="items.length" hoverable clickable>
        <NListItem v-for="item in items" :key="item.id" @click="openIssue(item)">
          <NThing>
            <template #header>
              <div class="flex flex-wrap items-center gap-8px">
                <NTag size="small" round type="info">{{ item.issueCode || item.issueId.slice(0, 8) }}</NTag>
                <span class="text-gray-600">{{ formatActivityActor(item) }}</span>
                <span>{{ formatActivityRow(item) }}</span>
              </div>
            </template>
            <template #header-extra>
              <span class="text-12px text-gray-400">{{ relTime(item.createdAt) }}</span>
            </template>
            <template #description>
              <div class="flex flex-wrap items-center gap-8px">
                <span class="text-12px text-gray-400">{{ item.issueTitle }}</span>
                <div class="activity-rx" @click.stop>
                  <button
                    v-for="chip in item.reactions?.summary || []"
                    :key="chip.emoji"
                    type="button"
                    class="activity-rx__chip"
                    :class="{ on: chip.myReacted }"
                    @click="toggleChip(item, chip.emoji, $event)"
                  >
                    <span>{{ chip.emoji }}</span>
                    <span>{{ chip.count }}</span>
                  </button>
                  <NDropdown
                    trigger="click"
                    :options="ACTIVITY_QUICK_EMOJIS.map(e => ({ label: e, key: e }))"
                    @select="(key: string) => toggleChip(item, key, new Event('click'))"
                  >
                    <button type="button" class="activity-rx__add" title="添加反应">+</button>
                  </NDropdown>
                </div>
              </div>
            </template>
          </NThing>
        </NListItem>
      </NList>
      <NEmpty v-else-if="empty" :description="emptyDesc" />
    </NSpin>

    <div v-if="nextCursor" class="mt-16px flex justify-center">
      <NButton :loading="loadingMore" @click="load(false)">加载更多</NButton>
    </div>
  </div>
</template>

<style scoped>
.activity-page {
  max-width: 960px;
  margin: 0 auto;
}
.activity-rx {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: 4px;
}
.activity-rx__chip,
.activity-rx__add {
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #f7f7fb;
  border-radius: 999px;
  padding: 0 6px;
  height: 22px;
  font-size: 12px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.activity-rx__chip.on {
  background: rgba(94, 106, 210, 0.16);
  border-color: rgba(94, 106, 210, 0.4);
}
.activity-rx__add {
  opacity: 0.7;
}
</style>
