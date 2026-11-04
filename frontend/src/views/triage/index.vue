<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import {
  type TriageIssue,
  fetchTriageAccept,
  fetchTriageDecline,
  fetchTriageDuplicate,
  fetchTriageEnqueue,
  fetchTriageList
} from '@/service/api';

defineOptions({ name: 'TriagePage' });

const router = useRouter();
const loading = ref(false);
const rows = ref<TriageIssue[]>([]);
const total = ref(0);
const createTitle = ref('');
const creating = ref(false);
const dupTarget = ref<Record<string, string>>({});

const empty = computed(() => !loading.value && rows.value.length === 0);

async function load() {
  loading.value = true;
  try {
    const { data, error } = await fetchTriageList({ page: 1, pageSize: 50 });
    if (error || !data) {
      window.$message?.error(error?.message || '加载分诊队列失败');
      return;
    }
    rows.value = data.rows || [];
    total.value = data.total ?? 0;
  } finally {
    loading.value = false;
  }
}

async function onAccept(row: TriageIssue) {
  const { error } = await fetchTriageAccept(row.id);
  if (error) {
    window.$message?.error(error.message || '接受失败');
    return;
  }
  window.$message?.success('已接受，进入 backlog');
  await load();
}

async function onDecline(row: TriageIssue) {
  const { error } = await fetchTriageDecline(row.id);
  if (error) {
    window.$message?.error(error.message || '拒绝失败');
    return;
  }
  window.$message?.success('已拒绝');
  await load();
}

async function onDuplicate(row: TriageIssue) {
  const target = (dupTarget.value[row.id] || '').trim();
  if (!target) {
    window.$message?.warning('请填写规范 Issue 的 ID');
    return;
  }
  const { error } = await fetchTriageDuplicate(row.id, target);
  if (error) {
    window.$message?.error(error.message || '标记重复失败');
    return;
  }
  window.$message?.success('已标记为重复');
  await load();
}

async function onCreate() {
  const title = createTitle.value.trim();
  if (!title) {
    window.$message?.warning('请输入标题');
    return;
  }
  creating.value = true;
  try {
    const { error } = await fetchTriageEnqueue({ title, type: 'feedback' });
    if (error) {
      window.$message?.error(error.message || '创建失败');
      return;
    }
    createTitle.value = '';
    window.$message?.success('已加入分诊队列');
    await load();
  } finally {
    creating.value = false;
  }
}

function openIssue(row: TriageIssue) {
  router.push({ name: 'issue_detail', query: { id: row.id } });
}

onMounted(load);
</script>

<template>
  <div class="h-full flex-col gap-16px overflow-hidden p-16px">
    <div class="flex-y-center justify-between gap-12px">
      <div class="min-w-0">
        <div class="flex-y-center gap-12px">
          <h2 class="text-18px font-medium">分诊</h2>
          <NTag v-if="total > 0" type="warning" size="small" round>{{ total }} 待处理</NTag>
        </div>
        <p class="mt-4px text-13px opacity-60">工作区入站队列（非个人通知 Inbox）</p>
      </div>
      <div class="flex-y-center gap-8px">
        <NInput
          v-model:value="createTitle"
          size="small"
          placeholder="快速入队标题"
          class="w-220px"
          @keyup.enter="onCreate"
        />
        <NButton size="small" type="primary" :loading="creating" @click="onCreate">入队</NButton>
        <NButton size="small" @click="load">刷新</NButton>
      </div>
    </div>

    <NSpin :show="loading" class="min-h-0 flex-1">
      <NEmpty v-if="empty" description="暂无待分诊" class="py-48px" />
      <NList v-else hoverable>
        <NListItem v-for="row in rows" :key="row.id">
          <div class="w-full flex-col gap-8px">
            <div class="flex-y-center justify-between gap-12px">
              <div class="min-w-0 flex-1 cursor-pointer" @click="openIssue(row)">
                <div class="flex-y-center gap-8px">
                  <NTag size="tiny" :bordered="false">{{ row.issueCode }}</NTag>
                  <NTag size="tiny" type="info" :bordered="false">{{ row.type }}</NTag>
                  <NTag size="tiny" :bordered="false">{{ row.priority }}</NTag>
                  <span class="truncate font-medium">{{ row.title }}</span>
                </div>
                <div v-if="row.description" class="mt-4px truncate text-13px opacity-50">
                  {{ row.description }}
                </div>
              </div>
              <div class="flex-y-center shrink-0 gap-8px">
                <NButton size="tiny" type="primary" secondary @click="onAccept(row)">接受</NButton>
                <NButton size="tiny" secondary @click="onDecline(row)">拒绝</NButton>
              </div>
            </div>
            <div class="flex-y-center gap-8px">
              <NInput
                v-model:value="dupTarget[row.id]"
                size="tiny"
                placeholder="重复于：目标 Issue ID"
                class="max-w-320px"
              />
              <NButton size="tiny" @click="onDuplicate(row)">标记重复</NButton>
            </div>
          </div>
        </NListItem>
      </NList>
    </NSpin>
  </div>
</template>
