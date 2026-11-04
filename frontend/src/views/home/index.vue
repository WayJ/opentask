<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import {
  fetchCycles,
  fetchInboxList,
  fetchWorkspaceList,
  type WorkspaceItem
} from '@/service/api';
import { issueApi } from '@/service/api/issue';
import { localStg } from '@/utils/storage';

defineOptions({ name: 'HomeWorkspaceSummary' });

const router = useRouter();
const loading = ref(false);
const workspace = ref<WorkspaceItem | null>(null);
const issueTotal = ref(0);
const inboxUnread = ref(0);
const activeCycleName = ref<string | null>(null);

const greeting = computed(() => {
  const h = new Date().getHours();
  if (h < 12) return '早上好';
  if (h < 18) return '下午好';
  return '晚上好';
});

async function load() {
  loading.value = true;
  try {
    const wsId = localStg.get('workspaceId') as string | null;
    const { data: workspaces } = await fetchWorkspaceList();
    workspace.value =
      (workspaces || []).find(w => w.id === wsId) || (workspaces || [])[0] || null;

    if (!workspace.value?.id) return;

    try {
      const list = await issueApi.getIssues({ current: 1, pageSize: 1 } as any);
      const payload: any = (list as any)?.data ?? list;
      issueTotal.value = Number(payload?.total ?? 0);
    } catch {
      issueTotal.value = 0;
    }

    try {
      const { data: inbox } = await fetchInboxList({ page: 1, pageSize: 1 });
      inboxUnread.value = Number(inbox?.unreadCount ?? inbox?.total ?? 0);
    } catch {
      inboxUnread.value = 0;
    }

    try {
      if (workspace.value?.cyclesEnabled) {
        const { data: cycles } = await fetchCycles({ status: 'active' });
        const rows = cycles?.rows || [];
        activeCycleName.value = rows[0]?.name || null;
      } else {
        activeCycleName.value = null;
      }
    } catch {
      activeCycleName.value = null;
    }
  } finally {
    loading.value = false;
  }
}

function goIssues() {
  router.push({ name: 'issue_list' });
}
function goInbox() {
  router.push({ name: 'inbox' });
}
function goCycles() {
  router.push({ name: 'workspace_cycles' });
}

onMounted(load);
</script>

<template>
  <div class="home-summary p-16px">
    <NSpin :show="loading">
      <div class="mb-16px">
        <h2 class="m-0 text-20px font-medium">{{ greeting }}</h2>
        <p class="mb-0 mt-4px text-13px text-gray-500">
          {{ workspace?.name || '工作区' }}
          <span v-if="workspace?.issueKey" class="ml-8px text-12px text-gray-400">
            Issue Key · {{ workspace.issueKey }}
          </span>
        </p>
      </div>

      <NGrid :x-gap="16" :y-gap="16" cols="1 s:2 m:3" responsive="screen">
        <NGi>
          <NCard size="small" hoverable class="cursor-pointer" @click="goIssues">
            <div class="text-12px text-gray-500">Issues</div>
            <div class="mt-4px text-28px font-medium">{{ issueTotal }}</div>
            <div class="mt-8px text-12px text-primary">打开列表 →</div>
          </NCard>
        </NGi>
        <NGi>
          <NCard size="small" hoverable class="cursor-pointer" @click="goInbox">
            <div class="text-12px text-gray-500">Inbox</div>
            <div class="mt-4px text-28px font-medium">{{ inboxUnread }}</div>
            <div class="mt-8px text-12px text-primary">查看收件箱 →</div>
          </NCard>
        </NGi>
        <NGi>
          <NCard size="small" hoverable class="cursor-pointer" @click="goCycles">
            <div class="text-12px text-gray-500">Cycle</div>
            <div class="mt-8px truncate text-18px font-medium">
              {{ activeCycleName || (workspace?.cyclesEnabled ? '无 Active Cycle' : '未启用 Cycles') }}
            </div>
            <div class="mt-8px text-12px text-primary">工作区设置 →</div>
          </NCard>
        </NGi>
      </NGrid>

      <NCard size="small" class="mt-16px" title="快速入口">
        <NSpace>
          <NButton size="small" type="primary" @click="goIssues">Issue 列表</NButton>
          <NButton size="small" @click="goInbox">Inbox</NButton>
          <NButton size="small" @click="router.push({ name: 'triage' })">Triage</NButton>
          <NButton size="small" @click="goCycles">Cycles / Issue Key</NButton>
        </NSpace>
      </NCard>
    </NSpin>
  </div>
</template>

<style scoped>
.home-summary {
  max-width: 960px;
}
.cursor-pointer {
  cursor: pointer;
}
</style>
