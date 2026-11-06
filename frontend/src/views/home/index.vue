<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import {
  countOpenFromStatus,
  fetchCycles,
  fetchInboxList,
  fetchInsightsSummary,
  fetchWorkspaceList,
  sumCompletedLastDays
} from '@/service/api';
import type { WorkspaceItem } from '@/service/api';
import { issueApi } from '@/service/api/issue';
import { localStg } from '@/utils/storage';
import { $t } from '@/locales';

defineOptions({ name: 'HomeWorkspaceSummary' });

const router = useRouter();
const loading = ref(false);
const workspace = ref<WorkspaceItem | null>(null);
const issueTotal = ref(0);
const inboxUnread = ref(0);
const activeCycleName = ref<string | null>(null);

const assignedCount = ref(0);
const createdCount = ref(0);
const watchingCount = ref(0);
const dueSoonCount = ref(0);
const weekCompleted = ref(0);
const insightsOpen = ref(0);

const greeting = computed(() => {
  const h = new Date().getHours();
  if (h < 12) return '早上好';
  if (h < 18) return '下午好';
  return '晚上好';
});

async function countIssues(params: Record<string, unknown>) {
  try {
    const list = await issueApi.getIssues({ page: 1, page_size: 1, ...params } as any);
    const payload: any = (list as any)?.data ?? list;
    return Number(payload?.total ?? 0);
  } catch {
    return 0;
  }
}

async function loadIssueTotal() {
  issueTotal.value = await countIssues({});
}

async function loadMySections() {
  const [a, c, w, d] = await Promise.all([
    countIssues({ assignee_id: 'me' }),
    countIssues({ reporter_id: 'me' }),
    countIssues({ watching: true }),
    countIssues({ due_soon: true })
  ]);
  assignedCount.value = a;
  createdCount.value = c;
  watchingCount.value = w;
  dueSoonCount.value = d;
}

async function loadInboxUnread() {
  try {
    const { data: inbox } = await fetchInboxList({ page: 1, pageSize: 1 });
    inboxUnread.value = Number(inbox?.unreadCount ?? inbox?.total ?? 0);
  } catch {
    inboxUnread.value = 0;
  }
}

async function loadInsightsStrip() {
  try {
    const { data } = await fetchInsightsSummary();
    if (!data) {
      weekCompleted.value = 0;
      insightsOpen.value = 0;
      return;
    }
    weekCompleted.value = sumCompletedLastDays(data.createdVsCompleted, 7);
    insightsOpen.value = countOpenFromStatus(data.statusCounts);
  } catch {
    weekCompleted.value = 0;
    insightsOpen.value = 0;
  }
}

async function loadActiveCycle(ws: WorkspaceItem) {
  try {
    if (!ws.cyclesEnabled) {
      activeCycleName.value = null;
      return;
    }
    const { data: cycles } = await fetchCycles({ status: 'active' });
    activeCycleName.value = cycles?.rows?.[0]?.name || null;
  } catch {
    activeCycleName.value = null;
  }
}

async function load() {
  loading.value = true;
  try {
    const wsId = localStg.get('workspaceId') as string | null;
    const { data: workspaces } = await fetchWorkspaceList();
    const list = workspaces || [];
    workspace.value = list.find(w => w.id === wsId) || list[0] || null;
    if (!workspace.value?.id) return;
    await Promise.all([
      loadIssueTotal(),
      loadInboxUnread(),
      loadActiveCycle(workspace.value),
      loadMySections(),
      loadInsightsStrip()
    ]);
  } finally {
    loading.value = false;
  }
}

function goIssues(scope?: string) {
  if (scope) {
    router.push({ name: 'issue_list', query: { scope } });
  } else {
    router.push({ name: 'issue_list' });
  }
}
function goInbox() {
  router.push({ name: 'inbox' });
}
function goCycles() {
  router.push({ name: 'workspace_cycles' });
}
function goInsights() {
  router.push({ name: 'insights' });
}

onMounted(load);
</script>

<template>
  <div class="home-summary">
    <NSpin :show="loading">
      <div class="mb-16px">
        <h2 class="m-0 text-20px font-medium">{{ greeting }}</h2>
        <p class="mb-0 mt-4px text-13px opacity-60">
          {{ workspace?.name || '工作区' }}
          <span v-if="workspace?.issueKey" class="ml-8px text-12px opacity-50">
            Issue Key · {{ workspace.issueKey }}
          </span>
        </p>
      </div>

      <NGrid :x-gap="16" :y-gap="16" cols="1 s:2 m:3" responsive="screen">
        <NGi>
          <NCard size="small" hoverable class="cursor-pointer" @click="goIssues()">
            <div class="ot-muted text-12px">{{ $t('page.shell.issueListTitle') }}</div>
            <div class="mt-4px text-28px font-medium">{{ issueTotal }}</div>
            <div class="mt-8px text-12px text-primary">打开列表 →</div>
          </NCard>
        </NGi>
        <NGi>
          <NCard size="small" hoverable class="cursor-pointer" @click="goInbox">
            <div class="text-12px opacity-60">Inbox</div>
            <div class="mt-4px text-28px font-medium">{{ inboxUnread }}</div>
            <div class="mt-8px text-12px text-primary">查看收件箱 →</div>
          </NCard>
        </NGi>
        <NGi>
          <NCard size="small" hoverable class="cursor-pointer" @click="goCycles">
            <div class="text-12px opacity-60">Cycle</div>
            <div class="mt-8px truncate text-18px font-medium">
              {{ activeCycleName || (workspace?.cyclesEnabled ? '无进行中的冲刺' : '未启用冲刺') }}
            </div>
            <div class="mt-8px text-12px text-primary">工作区设置 →</div>
          </NCard>
        </NGi>
      </NGrid>

      <NCard size="small" class="mt-16px" title="我的">
        <NGrid :x-gap="12" :y-gap="12" cols="1 s:2 m:4" responsive="screen">
          <NGi>
            <NCard size="small" hoverable class="my-section cursor-pointer" @click="goIssues('assigned')">
              <div class="text-12px opacity-60">指派给我</div>
              <div class="mt-4px text-22px font-medium">{{ assignedCount }}</div>
            </NCard>
          </NGi>
          <NGi>
            <NCard size="small" hoverable class="my-section cursor-pointer" @click="goIssues('created')">
              <div class="text-12px opacity-60">我创建的</div>
              <div class="mt-4px text-22px font-medium">{{ createdCount }}</div>
            </NCard>
          </NGi>
          <NGi>
            <NCard size="small" hoverable class="my-section cursor-pointer" @click="goIssues('watching')">
              <div class="text-12px opacity-60">我关注的</div>
              <div class="mt-4px text-22px font-medium">{{ watchingCount }}</div>
            </NCard>
          </NGi>
          <NGi>
            <NCard size="small" hoverable class="my-section cursor-pointer" @click="goIssues('due_soon')">
              <div class="text-12px opacity-60">即将到期</div>
              <div class="mt-4px text-22px font-medium">{{ dueSoonCount }}</div>
              <div class="mt-4px text-11px opacity-50">今日起 3 日内</div>
            </NCard>
          </NGi>
        </NGrid>
      </NCard>

      <NCard size="small" class="insights-strip mt-16px cursor-pointer" hoverable @click="goInsights">
        <div class="flex flex-wrap items-center justify-between gap-12px">
          <div>
            <div class="text-13px font-medium">Insights</div>
            <div class="mt-2px text-12px opacity-55">本周完成 / 开放问题</div>
          </div>
          <div class="flex gap-24px">
            <div>
              <div class="text-11px opacity-55">本周完成</div>
              <div class="text-20px font-medium">{{ weekCompleted }}</div>
            </div>
            <div>
              <div class="text-11px opacity-55">开放</div>
              <div class="text-20px font-medium">{{ insightsOpen }}</div>
            </div>
          </div>
          <div class="text-12px text-primary">查看效能 →</div>
        </div>
      </NCard>

      <NCard size="small" class="mt-16px" title="快速入口">
        <NSpace>
          <NButton size="small" type="primary" @click="goIssues()">{{ $t('page.shell.issueListTitle') }}</NButton>
          <NButton size="small" @click="goIssues('assigned')">我的问题</NButton>
          <NButton size="small" @click="goInbox">Inbox</NButton>
          <NButton size="small" @click="router.push({ name: 'triage' })">Triage</NButton>
          <NButton size="small" @click="goCycles">冲刺 / 问题单号</NButton>
        </NSpace>
      </NCard>
    </NSpin>
  </div>
</template>

<style scoped>
.home-summary {
  max-width: 960px;
  padding: 4px;
}
.home-summary :deep(.n-card) {
  border: 1px solid var(--color-hairline);
  background: var(--color-bg-primary);
}
.my-section {
  min-height: 72px;
}
.cursor-pointer {
  cursor: pointer;
}
</style>
