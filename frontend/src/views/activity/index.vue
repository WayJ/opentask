<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import UserSelect from '@/components/UserSelect.vue';
import { issueApi } from '@/service/api/issue';
import {
  ACTIVITY_ACTION_OPTIONS,
  type ActivityItem,
  buildActivityQuery,
  formatActivityActor,
  formatActivityRow
} from '@/utils/activityFeed';

defineOptions({ name: 'ActivityPage' });

const router = useRouter();
const loading = ref(false);
const loadingMore = ref(false);
const items = ref<ActivityItem[]>([]);
const nextCursor = ref<string | null>(null);
const actionTypes = ref<string[]>([]);
const sincePreset = ref<'24h' | '7d' | null>('7d');
const actorId = ref<string | null>(null);

const empty = computed(() => !loading.value && items.value.length === 0);

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
  } finally {
    loading.value = false;
    loadingMore.value = false;
  }
}

function openIssue(item: ActivityItem) {
  router.push({ name: 'issue_detail', query: { id: item.issueId } });
}

watch([actionTypes, sincePreset, actorId], () => load(true));

onMounted(() => {
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
              <span class="text-12px text-gray-400">{{ item.issueTitle }}</span>
            </template>
          </NThing>
        </NListItem>
      </NList>
      <NEmpty v-else-if="empty" description="暂无活动" />
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
</style>
