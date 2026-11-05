<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  type InitiativeRelationItem,
  type InitiativeRelationType,
  type InitiativeRow,
  type InitiativeStatus,
  fetchAddFavorite,
  fetchAddInitiativeRelation,
  fetchFavorites,
  fetchInitiative,
  fetchInitiativeRelations,
  fetchInitiatives,
  fetchProjectList,
  fetchRemoveFavorite,
  fetchRemoveInitiativeRelation,
  fetchSetInitiativeProjects,
  fetchUpdateInitiative
} from '@/service/api';
import {
  groupRelationItems,
  relationDirectionLabel
} from '@/utils/initiativeRelations';
import EntityDocsPanel from '@/components/entity-docs/EntityDocsPanel.vue';

defineOptions({ name: 'InitiativeDetailPage' });

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const saving = ref(false);
const pinLoading = ref(false);
const pinnedFavoriteId = ref<string | null>(null);
const row = ref<InitiativeRow | null>(null);
const projectOptions = ref<Array<{ label: string; value: string }>>([]);
const relationItems = ref<InitiativeRelationItem[]>([]);
const relationsLoading = ref(false);
const relationSaving = ref(false);
const peerOptions = ref<Array<{ label: string; value: string }>>([]);
const addForm = reactive({
  targetInitiativeId: null as string | null,
  type: 'blocks' as InitiativeRelationType
});

const form = reactive({
  name: '',
  description: '',
  status: 'active' as InitiativeStatus,
  projectIds: [] as string[]
});

const id = computed(() => String(route.query.id || ''));

const grouped = computed(() => groupRelationItems(relationItems.value));

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

const typeOptions = [
  { label: '阻塞 (blocks)', value: 'blocks' },
  { label: '被阻塞 (is_blocked_by)', value: 'is_blocked_by' },
  { label: '相关 (relates_to)', value: 'relates_to' }
];

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

async function loadPeers() {
  try {
    const { data } = await fetchInitiatives();
    const rows = data?.rows || [];
    peerOptions.value = rows
      .filter(r => r.id !== id.value)
      .map(r => ({ label: `${r.name} (${r.status})`, value: r.id }));
  } catch {
    peerOptions.value = [];
  }
}

async function loadRelations() {
  if (!id.value) {
    relationItems.value = [];
    return;
  }
  relationsLoading.value = true;
  try {
    const { data, error } = await fetchInitiativeRelations(id.value);
    if (error) {
      window.$message?.error(error.message || '加载依赖失败');
      relationItems.value = [];
      return;
    }
    relationItems.value = data?.items || [];
  } finally {
    relationsLoading.value = false;
  }
}

async function onAddRelation() {
  if (!id.value || !addForm.targetInitiativeId) {
    window.$message?.warning('请选择目标 Initiative');
    return;
  }
  relationSaving.value = true;
  try {
    const { error } = await fetchAddInitiativeRelation(id.value, {
      targetInitiativeId: addForm.targetInitiativeId,
      type: addForm.type
    });
    if (error) {
      window.$message?.error(error.message || '添加失败');
      return;
    }
    addForm.targetInitiativeId = null;
    window.$message?.success('已添加依赖');
    await loadRelations();
    await load();
  } finally {
    relationSaving.value = false;
  }
}

async function onRemoveRelation(relationId: string) {
  if (!id.value) return;
  relationSaving.value = true;
  try {
    const { error } = await fetchRemoveInitiativeRelation(id.value, relationId);
    if (error) {
      window.$message?.error(error.message || '删除失败');
      return;
    }
    window.$message?.success('已删除');
    await loadRelations();
    await load();
  } finally {
    relationSaving.value = false;
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
  loadPeers();
  loadRelations();
});

onMounted(async () => {
  await loadProjects();
  await load();
  await loadPinState();
  await loadPeers();
  await loadRelations();
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
        <NTag v-if="(row?.blocksCount || 0) > 0" size="small" type="warning">
          阻塞 {{ row?.blocksCount }}
        </NTag>
        <NTag v-if="(row?.blockedByCount || 0) > 0" size="small" type="error">
          被阻 {{ row?.blockedByCount }}
        </NTag>
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

        <NCollapse>
          <NCollapseItem title="依赖" name="relations">
            <NSpin :show="relationsLoading">
              <div class="flex-col gap-12px">
                <div class="flex flex-wrap items-end gap-8px">
                  <div class="min-w-220px">
                    <div class="mb-4px text-12px text-gray-500">目标 Initiative</div>
                    <NSelect
                      v-model:value="addForm.targetInitiativeId"
                      filterable
                      clearable
                      placeholder="选择"
                      :options="peerOptions"
                    />
                  </div>
                  <div class="min-w-200px">
                    <div class="mb-4px text-12px text-gray-500">类型</div>
                    <NSelect v-model:value="addForm.type" :options="typeOptions" />
                  </div>
                  <NButton type="primary" :loading="relationSaving" @click="onAddRelation">添加</NButton>
                </div>

                <div v-if="grouped.blocks.length" class="flex-col gap-4px">
                  <div class="text-13px font-500">阻塞</div>
                  <div
                    v-for="item in grouped.blocks"
                    :key="item.id"
                    class="flex items-center justify-between gap-8px rounded bg-gray-50 px-8px py-6px"
                  >
                    <span>
                      <NTag size="tiny" type="warning">{{ relationDirectionLabel(item.type, item.direction) }}</NTag>
                      {{ item.initiative.name }}
                    </span>
                    <NButton size="tiny" quaternary type="error" @click="onRemoveRelation(item.id)">删除</NButton>
                  </div>
                </div>

                <div v-if="grouped.blockedBy.length" class="flex-col gap-4px">
                  <div class="text-13px font-500">被阻塞</div>
                  <div
                    v-for="item in grouped.blockedBy"
                    :key="item.id"
                    class="flex items-center justify-between gap-8px rounded bg-gray-50 px-8px py-6px"
                  >
                    <span>
                      <NTag size="tiny" type="error">{{ relationDirectionLabel(item.type, item.direction) }}</NTag>
                      {{ item.initiative.name }}
                    </span>
                    <NButton size="tiny" quaternary type="error" @click="onRemoveRelation(item.id)">删除</NButton>
                  </div>
                </div>

                <div v-if="grouped.relatesTo.length" class="flex-col gap-4px">
                  <div class="text-13px font-500">相关</div>
                  <div
                    v-for="item in grouped.relatesTo"
                    :key="item.id"
                    class="flex items-center justify-between gap-8px rounded bg-gray-50 px-8px py-6px"
                  >
                    <span>
                      <NTag size="tiny">{{ relationDirectionLabel(item.type, item.direction) }}</NTag>
                      {{ item.initiative.name }}
                    </span>
                    <NButton size="tiny" quaternary type="error" @click="onRemoveRelation(item.id)">删除</NButton>
                  </div>
                </div>

                <p v-if="!relationItems.length" class="text-12px text-gray-400">暂无依赖关系</p>
              </div>
            </NSpin>
          </NCollapseItem>
        </NCollapse>

        <EntityDocsPanel v-if="id" parent-type="initiative" :parent-id="id" />
      </div>
    </NSpin>
  </div>
</template>
