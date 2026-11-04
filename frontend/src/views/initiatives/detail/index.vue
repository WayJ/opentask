<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  type InitiativeRow,
  type InitiativeStatus,
  fetchAddFavorite,
  fetchFavorites,
  fetchInitiative,
  fetchProjectList,
  fetchRemoveFavorite,
  fetchSetInitiativeProjects,
  fetchUpdateInitiative
} from '@/service/api';

defineOptions({ name: 'InitiativeDetailPage' });

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const saving = ref(false);
const pinLoading = ref(false);
const pinnedFavoriteId = ref<string | null>(null);
const row = ref<InitiativeRow | null>(null);
const projectOptions = ref<Array<{ label: string; value: string }>>([]);

const form = reactive({
  name: '',
  description: '',
  status: 'active' as InitiativeStatus,
  projectIds: [] as string[]
});

const id = computed(() => String(route.query.id || ''));

const healthType: Record<string, 'success' | 'warning' | 'error' | 'default'> = {
  on_track: 'success',
  at_risk: 'warning',
  off_track: 'error'
};
const healthLabel: Record<string, string> = {
  on_track: '顺利',
  at_risk: '风险',
  off_track: '偏离'
};

async function loadProjects() {
  try {
    const response = await fetchProjectList();
    const list = response.data || [];
    projectOptions.value = list.map((p: { id: string; name: string }) => ({
      label: p.name,
      value: p.id
    }));
  } catch {
    projectOptions.value = [];
  }
}

async function loadPinState() {
  if (!id.value) {
    pinnedFavoriteId.value = null;
    return;
  }
  try {
    const response = await fetchFavorites();
    const rows = response.data?.rows || [];
    const hit = rows.find(r => r.targetType === 'initiative' && r.targetId === id.value);
    pinnedFavoriteId.value = hit?.id ?? null;
  } catch {
    pinnedFavoriteId.value = null;
  }
}

async function toggleSidebarPin() {
  if (!id.value) return;
  pinLoading.value = true;
  try {
    if (pinnedFavoriteId.value) {
      await fetchRemoveFavorite(pinnedFavoriteId.value);
      pinnedFavoriteId.value = null;
      window.$message?.success('已从侧栏移除');
    } else {
      const response = await fetchAddFavorite({ target_type: 'initiative', target_id: id.value });
      pinnedFavoriteId.value = response.data?.id ?? null;
      window.$message?.success('已收藏到侧栏');
    }
    window.dispatchEvent(new CustomEvent('opentask:favorites-changed'));
  } catch {
    window.$message?.error('更新侧栏收藏失败');
  } finally {
    pinLoading.value = false;
  }
}

async function load() {
  if (!id.value) {
    window.$message?.warning('缺少 Initiative id');
    router.replace({ name: 'initiatives' });
    return;
  }
  loading.value = true;
  try {
    const { data, error } = await fetchInitiative(id.value);
    if (error || !data) {
      window.$message?.error(error?.message || '加载失败');
      return;
    }
    row.value = data;
    form.name = data.name;
    form.description = data.description || '';
    form.status = data.status;
    form.projectIds = [...(data.projectIds || [])];
  } finally {
    loading.value = false;
  }
}

async function onSave() {
  if (!id.value) return;
  const name = form.name.trim();
  if (!name) {
    window.$message?.warning('请输入名称');
    return;
  }
  saving.value = true;
  try {
    const { error: e1 } = await fetchUpdateInitiative(id.value, {
      name,
      description: form.description,
      status: form.status
    });
    if (e1) {
      window.$message?.error(e1.message || '保存失败');
      return;
    }
    const { data, error: e2 } = await fetchSetInitiativeProjects(id.value, form.projectIds);
    if (e2) {
      window.$message?.error(e2.message || '更新关联项目失败');
      return;
    }
    if (data) {
      row.value = data;
      form.projectIds = [...(data.projectIds || [])];
    }
    window.$message?.success('已保存');
  } finally {
    saving.value = false;
  }
}

watch(id, () => {
  load();
  loadPinState();
});

onMounted(async () => {
  await loadProjects();
  await load();
  await loadPinState();
});
</script>

<template>
  <div class="h-full flex-col gap-16px overflow-auto p-16px">
    <div class="flex items-center justify-between gap-12px">
      <div class="flex items-center gap-12px">
        <NButton quaternary @click="router.push({ name: 'initiatives' })">← 返回列表</NButton>
        <h2 class="text-18px font-600">Initiative 详情</h2>
        <NTag
          v-if="row?.healthSummary?.overall"
          :type="healthType[row.healthSummary.overall] || 'default'"
          size="small"
        >
          {{ healthLabel[row.healthSummary.overall] || row.healthSummary.overall }}
        </NTag>
        <NTag v-else size="small" :bordered="false">健康未汇总</NTag>
      </div>
      <NButton :loading="pinLoading" secondary @click="toggleSidebarPin">
        {{ pinnedFavoriteId ? '取消侧栏钉' : '钉到侧栏' }}
      </NButton>
    </div>

    <NSpin :show="loading">
      <div v-if="row" class="flex-col gap-16px">
        <NCard :bordered="false" title="健康汇总">
          <div class="flex flex-wrap gap-12px text-13px">
            <span>项目数：{{ row.healthSummary?.projectCount ?? 0 }}</span>
            <span>顺利：{{ row.healthSummary?.counts?.onTrack ?? 0 }}</span>
            <span>风险：{{ row.healthSummary?.counts?.atRisk ?? 0 }}</span>
            <span>偏离：{{ row.healthSummary?.counts?.offTrack ?? 0 }}</span>
            <span>未知：{{ row.healthSummary?.counts?.unknown ?? 0 }}</span>
          </div>
          <ul v-if="row.projects?.length" class="mt-12px flex-col gap-6px">
            <li v-for="p in row.projects" :key="p.id" class="flex items-center gap-8px">
              <span>{{ p.name || p.id.slice(0, 8) }}</span>
              <NTag v-if="p.healthStatus" size="tiny" :type="healthType[p.healthStatus] || 'default'">
                {{ healthLabel[p.healthStatus] || p.healthStatus }}
              </NTag>
              <NTag v-else size="tiny" :bordered="false">未知</NTag>
            </li>
          </ul>
          <p v-else class="mt-8px text-12px text-gray-400">尚未关联 Project（不走遗留需求轴）</p>
        </NCard>

        <NCard :bordered="false" title="基本信息">
          <NForm label-placement="left" label-width="100" class="max-w-640px">
            <NFormItem label="名称" required>
              <NInput v-model:value="form.name" maxlength="100" />
            </NFormItem>
            <NFormItem label="描述">
              <NInput v-model:value="form.description" type="textarea" :rows="4" />
            </NFormItem>
            <NFormItem label="状态">
              <NSelect
                v-model:value="form.status"
                :options="[
                  { label: '计划中', value: 'planned' },
                  { label: '进行中', value: 'active' },
                  { label: '已完成', value: 'completed' },
                  { label: '已取消', value: 'canceled' }
                ]"
              />
            </NFormItem>
            <NFormItem label="关联项目">
              <NSelect
                v-model:value="form.projectIds"
                multiple
                filterable
                clearable
                placeholder="选择同工作区 Project"
                :options="projectOptions"
              />
            </NFormItem>
            <NFormItem>
              <NButton type="primary" :loading="saving" @click="onSave">保存</NButton>
            </NFormItem>
          </NForm>
        </NCard>
      </div>
    </NSpin>
  </div>
</template>
